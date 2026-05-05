from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from services.pdf_service      import extract_financials
from services.risk_service     import calculate_risk_with_ml as calculate_risk
from services.research_service import analyze_company_news
from services.cam_service      import generate_cam
from services.bank_service     import analyze_bank_statement
from services.mca_service      import search_mca
from services.auth_service     import (
    register_user, login_user, get_user_from_token, init_auth_tables
)
import sqlite3, os, json, traceback
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
MAX_FILE_MB        = 10

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER,
                company_name  TEXT    NOT NULL,
                created_at    TEXT    NOT NULL,
                risk_score    REAL,
                decision      TEXT,
                interest_rate TEXT,
                loan_amount   TEXT,
                revenue       TEXT,
                profit        TEXT,
                debt          TEXT,
                cam_report    TEXT,
                full_result   TEXT
            )
        """)
        conn.commit()
    init_auth_tables()

init_db()

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _token():
    return request.headers.get("Authorization", "").replace("Bearer ", "").strip()

def require_auth(f):
    @wraps(f)
    def dec(*a, **kw):
        user = get_user_from_token(_token())
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        request.user = user
        return f(*a, **kw)
    return dec

def optional_auth(f):
    @wraps(f)
    def dec(*a, **kw):
        request.user = get_user_from_token(_token())
        return f(*a, **kw)
    return dec

def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_analysis(user_id, company, result):
    a  = result.get("analysis", {})
    fi = result.get("financials", {})
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO analyses
              (user_id,company_name,created_at,risk_score,decision,interest_rate,
               loan_amount,revenue,profit,debt,cam_report,full_result)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (user_id, company, datetime.now().isoformat(),
              a.get("risk_score"), a.get("decision"), a.get("interest_rate"),
              a.get("loan_amount"),
              fi.get("revenue_display", fi.get("revenue","0")),
              fi.get("profit_display",  fi.get("profit","0")),
              fi.get("debt_display",    fi.get("debt","0")),
              result.get("cam_report"), json.dumps(result)))
        conn.commit()
        return cur.lastrowid

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    r = register_user(d.get("username",""), d.get("email",""),
                      d.get("password",""), d.get("full_name",""))
    return jsonify(r), (200 if r["success"] else 400)

@app.route("/auth/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    r = login_user(d.get("username",""), d.get("password",""))
    return jsonify(r), (200 if r["success"] else 401)

@app.route("/auth/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"user": request.user})

# ── Core analysis ─────────────────────────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
@optional_auth
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No annual report PDF uploaded."}), 400

    file         = request.files["file"]
    company_name = (request.form.get("company_name") or "").strip()
    bank_file    = request.files.get("bank_file")

    # ✅ NEW: optional second PDF support
    file2 = request.files.get("file2")

    if not file.filename:
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are accepted."}), 400
    if not company_name:
        return jsonify({"error": "Company name is required."}), 400

    file.seek(0, 2)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_MB:
        return jsonify({"error": f"File too large ({size_mb:.1f} MB). Max {MAX_FILE_MB} MB."}), 400

    try:
        # ✅ NEW: multi-PDF extraction + merge
        f1 = extract_financials(file)

        if file2 and file2.filename and allowed_file(file2.filename):
            f2 = extract_financials(file2)

            financial_data = {
                "revenue": str(max(float(f1.get("revenue", 0)), float(f2.get("revenue", 0)))),
                "profit":  str(max(float(f1.get("profit", 0)),  float(f2.get("profit", 0)))),
                "debt":    str(max(float(f1.get("debt", 0)),    float(f2.get("debt", 0)))),
                "pdf_risk_flags": list(set(f1.get("pdf_risk_flags", []) + f2.get("pdf_risk_flags", []))),
                "extraction_method": "multi_pdf"
            }

            # display fields
            from services.pdf_service import fmt_inr
            financial_data["revenue_display"] = fmt_inr(float(financial_data["revenue"]))
            financial_data["profit_display"]  = fmt_inr(float(financial_data["profit"]))
            financial_data["debt_display"]    = fmt_inr(float(financial_data["debt"]))
        else:
            financial_data = f1

        research_data  = analyze_company_news(company_name)

        bank_data = None
        if bank_file and bank_file.filename and allowed_file(bank_file.filename):
            bank_data = analyze_bank_statement(bank_file)

        mca_data = search_mca(company_name)

        officer_notes = request.form.get("officer_notes", "").strip() or None

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

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

    user_id = (request.user or {}).get("id")
    result  = {
        "company":    company_name,
        "financials": financial_data,
        "research":   research_data,
        "analysis":   risk_result,
        "bank":       bank_data,
        "mca":        mca_data,
        "cam_report": cam_filename,
    }

    try:
        result["record_id"] = save_analysis(user_id, company_name, result)
    except Exception:
        pass

    return jsonify(result)

# ── History ───────────────────────────────────────────────────────────────────

@app.route("/history", methods=["GET"])
@optional_auth
def get_history():
    try:
        with get_db() as conn:
            if request.user:
                rows = conn.execute(
                    "SELECT id,company_name,created_at,risk_score,decision,"
                    "loan_amount,cam_report FROM analyses "
                    "WHERE user_id=? ORDER BY id DESC LIMIT 20",
                    (request.user["id"],)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,company_name,created_at,risk_score,decision,"
                    "loan_amount,cam_report FROM analyses "
                    "WHERE user_id IS NULL ORDER BY id DESC LIMIT 20").fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history/<int:record_id>", methods=["GET"])
def get_analysis(record_id):
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT full_result FROM analyses WHERE id=?", (record_id,)).fetchone()
        if not row:
            return jsonify({"error": "Record not found"}), 404
        return jsonify(json.loads(row["full_result"]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, os.path.basename(filename), as_attachment=True)

@app.route("/")
def home():
    return jsonify({"status": "Intelli-Credit backend running", "version": "3.1"})

@app.route("/health")
def health():
    return jsonify({"status": "ok", "db": os.path.exists(DB_PATH)})

if __name__ == "__main__":
    app.run(debug=True, port=5000)

# ── ML model info endpoint ────────────────────────────────────────────────────

@app.route("/model-info", methods=["GET"])
def model_info():
    try:
        from services.ml_scoring_service import get_model_metadata
        return jsonify(get_model_metadata())
    except Exception as e:
        return jsonify({"error": str(e)}), 500