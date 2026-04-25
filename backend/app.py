from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from services.pdf_service import extract_financials
from services.risk_service import calculate_risk
from services.research_service import analyze_company_news
from services.cam_service import generate_cam
import sqlite3
import os
import json
import traceback
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH       = os.path.join(BASE_DIR, "intelli_credit.db")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_MB        = 20


# ─── Database setup ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT    NOT NULL,
                created_at   TEXT    NOT NULL,
                risk_score   REAL,
                decision     TEXT,
                interest_rate TEXT,
                loan_amount  TEXT,
                revenue      TEXT,
                profit       TEXT,
                debt         TEXT,
                cam_report   TEXT,
                full_result  TEXT
            )
        """)
        conn.commit()


init_db()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_analysis(company: str, result: dict) -> int:
    analysis = result.get("analysis", {})
    financials = result.get("financials", {})
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO analyses
              (company_name, created_at, risk_score, decision, interest_rate,
               loan_amount, revenue, profit, debt, cam_report, full_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company,
            datetime.now().isoformat(),
            analysis.get("risk_score"),
            analysis.get("decision"),
            analysis.get("interest_rate"),
            analysis.get("loan_amount"),
            financials.get("revenue_display", financials.get("revenue", "0")),
            financials.get("profit_display", financials.get("profit", "0")),
            financials.get("debt_display", financials.get("debt", "0")),
            result.get("cam_report"),
            json.dumps(result),
        ))
        conn.commit()
        return cur.lastrowid


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return jsonify({"status": "Intelli-Credit backend running", "version": "2.0"})


@app.route("/analyze", methods=["POST"])
def analyze():
    # ── Validation ────────────────────────────────────────────────────────────
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Please attach a PDF."}), 400

    file = request.files["file"]
    company_name = (request.form.get("company_name") or "").strip()

    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    file.seek(0, 2)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_MB:
        return jsonify({"error": f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_MB} MB."}), 400

    if not company_name:
        return jsonify({"error": "Company name is required."}), 400

    # ── Pipeline ──────────────────────────────────────────────────────────────
    try:
        # Step 1: Extract financials from PDF
        financial_data = extract_financials(file)

        # Step 2: Research agent (real Google News RSS)
        research_data = analyze_company_news(company_name)

        # Step 3: Risk scoring
        officer_notes = request.form.get("officer_notes", "").strip() or None
        risk_result = calculate_risk(
            financial_data,
            external_penalty=research_data["external_penalty"],
            external_flags=research_data["external_flags"],
            officer_notes=officer_notes,
        )

        # Step 4: Generate CAM report PDF
        cam_filename = generate_cam(
            company_name, financial_data, research_data, risk_result
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

    result = {
        "company":     company_name,
        "financials":  financial_data,
        "research":    research_data,
        "analysis":    risk_result,
        "cam_report":  cam_filename,
    }

    # Step 5: Persist to DB
    try:
        record_id = save_analysis(company_name, result)
        result["record_id"] = record_id
    except Exception:
        pass  # DB failure should not block the response

    return jsonify(result)


@app.route("/download/<path:filename>")
def download_file(filename: str):
    safe = os.path.basename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe, as_attachment=True)


@app.route("/history", methods=["GET"])
def get_history():
    """Return the last 20 analyses from the database."""
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT id, company_name, created_at, risk_score,
                       decision, loan_amount, cam_report
                FROM analyses
                ORDER BY id DESC
                LIMIT 20
            """).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history/<int:record_id>", methods=["GET"])
def get_analysis(record_id: int):
    """Return the full stored result for a specific analysis."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT full_result FROM analyses WHERE id = ?", (record_id,)
            ).fetchone()
        if row is None:
            return jsonify({"error": "Record not found"}), 404
        return jsonify(json.loads(row["full_result"]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "db": os.path.exists(DB_PATH)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)