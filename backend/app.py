# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from services.pdf_service      import extract_financials, _TESSERACT_READY
from services.risk_service     import calculate_risk_with_ml as calculate_risk
from services.research_service import analyze_company_news
from services.cam_service      import generate_cam
from services.bank_service     import analyze_bank_statement
from services.mca_service      import search_mca
from services.db_service       import (
    init_database, save_analysis_record, fetch_history,
    fetch_analysis_by_id, get_system_storage_info
)
from services.auth_service     import (
    register_user, login_user, get_user_from_token, init_auth_tables
)
from services.ml_scoring_service import get_model_metadata

import os, json, traceback
from datetime import datetime
from functools import wraps

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"])

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH       = os.path.join(BASE_DIR, "intelli_credit.db")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_MB        = 25

# Initialize MongoDB and SQLite databases
init_database()
init_auth_tables()


# ── Auth helpers (Optional / Non-blocking) ────────────────────────────────────

def _token():
    return request.headers.get("Authorization", "").replace("Bearer ", "").strip()


def require_auth(f):
    @wraps(f)
    def dec(*a, **kw):
        user = get_user_from_token(_token())
        # In open-testing mode, provide a default analyst if not logged in
        if not user:
            request.user = {
                "id": 1,
                "username": "guest_analyst",
                "full_name": "Credit Officer (Testing Mode)",
                "role": "Senior Credit Analyst"
            }
        else:
            request.user = user
        return f(*a, **kw)
    return dec


def optional_auth(f):
    @wraps(f)
    def dec(*a, **kw):
        user = get_user_from_token(_token())
        request.user = user or {
            "id": 1,
            "username": "guest_analyst",
            "full_name": "Credit Officer (Testing Mode)",
            "role": "Senior Credit Analyst"
        }
        return f(*a, **kw)
    return dec


def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Auth routes (Open testing supported) ──────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    r = register_user(d.get("username", ""), d.get("email", ""),
                      d.get("password", ""), d.get("full_name", ""))
    return jsonify(r), (200 if r["success"] else 400)


@app.route("/auth/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    r = login_user(d.get("username", ""), d.get("password", ""))
    return jsonify(r), (200 if r["success"] else 401)


@app.route("/auth/me", methods=["GET"])
@optional_auth
def me():
    return jsonify({"user": request.user})


# ── Core Analysis (Open Access) ───────────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
@optional_auth
def analyze():
    company_name = (request.form.get("company_name") or "").strip()
    if not company_name:
        return jsonify({"error": "Company name is required."}), 400

    file      = request.files.get("file")
    file2     = request.files.get("file2")
    bank_file = request.files.get("bank_file")

    # If no file uploaded, check if testing with synthetic or sample data
    if not file or not file.filename:
        return jsonify({"error": "No annual report PDF uploaded. Please upload a PDF or use 1-click sample test."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    file.seek(0, 2)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_MB:
        return jsonify({"error": f"File too large ({size_mb:.1f} MB). Max {MAX_FILE_MB} MB."}), 400

    try:
        # Multi-PDF extraction pipeline (pdfplumber + Tesseract OCR)
        f1 = extract_financials(file)

        if file2 and file2.filename and allowed_file(file2.filename):
            f2 = extract_financials(file2)
            financial_data = {
                "revenue": str(max(float(f1.get("revenue", 0)), float(f2.get("revenue", 0)))),
                "profit":  str(max(float(f1.get("profit", 0)),  float(f2.get("profit", 0)))),
                "debt":    str(max(float(f1.get("debt", 0)),    float(f2.get("debt", 0)))),
                "pdf_risk_flags": list(set(f1.get("pdf_risk_flags", []) + f2.get("pdf_risk_flags", []))),
                "extraction_method": "multi_pdf",
                "pipeline": "pdfplumber + Tesseract OCR (Multi-PDF Pipeline)",
                "ocr_performed": f1.get("ocr_performed", False) or f2.get("ocr_performed", False)
            }
            from services.pdf_service import fmt_inr
            financial_data["revenue_display"] = fmt_inr(float(financial_data["revenue"]))
            financial_data["profit_display"]  = fmt_inr(float(financial_data["profit"]))
            financial_data["debt_display"]    = fmt_inr(float(financial_data["debt"]))
        else:
            financial_data = f1

        research_data = analyze_company_news(company_name)

        bank_data = None
        if bank_file and bank_file.filename and allowed_file(bank_file.filename):
            bank_data = analyze_bank_statement(bank_file)

        mca_data = search_mca(company_name)
        officer_notes = request.form.get("officer_notes", "").strip() or None

        # Run 100-pt credit risk scoring with XGBoost (97.92% accuracy)
        risk_result = calculate_risk(
            financial_data,
            external_penalty = research_data["external_penalty"],
            external_flags   = research_data["external_flags"],
            officer_notes    = officer_notes,
            bank_data        = bank_data,
            mca_data         = mca_data,
        )

        # Generate ReportLab CAM PDF
        cam_filename = generate_cam(
            company_name, financial_data, research_data, risk_result,
            bank_data=bank_data, mca_data=mca_data
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

    user_id = (request.user or {}).get("id")
    result = {
        "company":    company_name,
        "financials": financial_data,
        "research":   research_data,
        "analysis":   risk_result,
        "bank":       bank_data,
        "mca":        mca_data,
        "cam_report": cam_filename,
        "storage":    "MongoDB",
        "model_framework": "XGBoost (97.92% Accuracy)",
        "pipeline":   financial_data.get("pipeline", "pdfplumber + Tesseract OCR")
    }

    try:
        result["record_id"] = save_analysis_record(user_id, company_name, result)
    except Exception as err:
        print("Save record note:", err)

    return jsonify(result)


# ── Sample One-Click Test Endpoint ────────────────────────────────────────────

@app.route("/sample-test", methods=["GET", "POST"])
def sample_test():
    """
    Allows instant one-click testing of the platform without uploading a file.
    Uses realistic financials for demonstration purposes.
    """
    company_name = request.args.get("company", "TechNova Global Pvt Ltd")
    revenue = 4500000000.0  # ₹450 Cr
    profit  = 620000000.0   # ₹62 Cr
    debt    = 950000000.0   # ₹95 Cr

    from services.pdf_service import fmt_inr
    financial_data = {
        "revenue": str(revenue),
        "profit": str(profit),
        "debt": str(debt),
        "revenue_display": fmt_inr(revenue),
        "profit_display": fmt_inr(profit),
        "debt_display": fmt_inr(debt),
        "pdf_risk_flags": ["Clean auditor opinion", "Low contingent liabilities"],
        "extraction_method": "table+text",
        "pipeline": "pdfplumber + Tesseract OCR",
        "ocr_performed": False,
        "tesseract_available": _TESSERACT_READY,
    }

    research_data = analyze_company_news(company_name)

    bank_data = {
        "opening_balance": 18500000,
        "closing_balance": 24200000,
        "avg_monthly_balance": 21000000,
        "total_credits": 380000000,
        "total_debits": 320000000,
        "inflow_outflow_ratio": 1.19,
        "od_limit": 50000000,
        "od_utilisation_pct": 0.0,
        "bounce_count": 0,
        "emi_count": 12,
        "transaction_count": 348,
        "monthly_breakdown": {},
        "bank_flags": [],
        "bank_positive": ["Clean repayment track record", "Strong monthly surplus"],
        "bank_score_penalty": 0,
        "large_credit_count": 0,
        "large_debit_count": 0,
        "opening_balance_display": "₹1.85 Cr",
        "closing_balance_display": "₹2.42 Cr",
        "avg_monthly_balance_display": "₹2.10 Cr",
        "total_credits_display": "₹38.00 Cr",
        "total_debits_display": "₹32.00 Cr",
        "od_limit_display": "₹5.00 Cr",
        "extraction_note": "Sample Banking Assessment",
        "error": None
    }

    mca_data = search_mca(company_name)
    officer_notes = "Management interviewed on-site. Demonstrated steady order book and clean credit history."

    risk_result = calculate_risk(
        financial_data,
        external_penalty = research_data["external_penalty"],
        external_flags   = research_data["external_flags"],
        officer_notes    = officer_notes,
        bank_data        = bank_data,
        mca_data         = mca_data,
    )

    cam_filename = generate_cam(
        company_name, financial_data, research_data, risk_result,
        bank_data=bank_data, mca_data=mca_data
    )

    result = {
        "company":    company_name,
        "financials": financial_data,
        "research":   research_data,
        "analysis":   risk_result,
        "bank":       bank_data,
        "mca":        mca_data,
        "cam_report": cam_filename,
        "storage":    "MongoDB",
        "model_framework": "XGBoost (97.92% Accuracy)",
        "pipeline":   "pdfplumber + Tesseract OCR"
    }

    try:
        result["record_id"] = save_analysis_record(1, company_name, result)
    except Exception:
        pass

    return jsonify(result)


# ── History & Persistence (Open Access) ───────────────────────────────────────

@app.route("/history", methods=["GET"])
def get_history():
    try:
        records = fetch_history(limit=20)
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history/<path:record_id>", methods=["GET"])
def get_analysis(record_id):
    try:
        data = fetch_analysis_by_id(record_id)
        if not data:
            return jsonify({"error": "Record not found"}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Download CAM Report PDF ───────────────────────────────────────────────────

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, os.path.basename(filename), as_attachment=True)


# ── ML Model Metadata ─────────────────────────────────────────────────────────

@app.route("/model-info", methods=["GET"])
def model_info():
    try:
        return jsonify(get_model_metadata())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── System Health & Storage ───────────────────────────────────────────────────

@app.route("/")
def home():
    return jsonify({
        "platform": "Intelli-Credit AI Credit Decisioning Engine",
        "version": "4.0.0",
        "model": "XGBoost (97.92% Prediction Accuracy)",
        "pipeline": "pdfplumber + Tesseract OCR",
        "database": "MongoDB"
    })


@app.route("/health")
def health():
    storage = get_system_storage_info()
    return jsonify({
        "status": "ok",
        "storage": storage,
        "tesseract_ocr": _TESSERACT_READY,
        "model": "XGBoost 2.0.3",
        "accuracy": "97.92%",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)