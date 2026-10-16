"""
db_service.py
MongoDB persistence engine with SQLite fallback/mirroring.
Connects to MongoDB (default: mongodb://localhost:27017/ or MONGO_URI).
Ensures Intelli-Credit stores analyses in MongoDB collections with dual-persistence.
"""

import os
import json
import sqlite3
from datetime import datetime
import pymongo
from bson import ObjectId

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "intelli_credit.db")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "intelli_credit_db")

_mongo_client = None
_mongo_db = None
_mongo_available = False


def get_mongo_db():
    global _mongo_client, _mongo_db, _mongo_available
    if _mongo_db is not None and _mongo_available:
        return _mongo_db
    try:
        _mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        _mongo_client.server_info()  # trigger connection check
        _mongo_db = _mongo_client[MONGO_DB_NAME]
        _mongo_available = True
        return _mongo_db
    except Exception as e:
        _mongo_available = False
        return None


def get_sqlite():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initializes MongoDB collections and SQLite tables."""
    # 1. MongoDB Setup
    mdb = get_mongo_db()
    if mdb is not None:
        try:
            if "analyses" not in mdb.list_collection_names():
                mdb.create_collection("analyses")
            mdb["analyses"].create_index([("created_at", pymongo.DESCENDING)])
            mdb["analyses"].create_index([("company_name", pymongo.ASCENDING)])
        except Exception:
            pass

    # 2. SQLite Setup
    with get_sqlite() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                mongo_id      TEXT,
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


def save_analysis_record(user_id, company, result) -> str:
    """
    Saves credit analysis to MongoDB and SQLite.
    Returns the string ID of the saved record.
    """
    a = result.get("analysis", {})
    fi = result.get("financials", {})
    now_iso = datetime.now().isoformat()

    doc = {
        "user_id": user_id,
        "company_name": company,
        "created_at": now_iso,
        "risk_score": a.get("risk_score"),
        "decision": a.get("decision"),
        "interest_rate": a.get("interest_rate"),
        "loan_amount": a.get("loan_amount"),
        "revenue": fi.get("revenue_display", fi.get("revenue", "0")),
        "profit": fi.get("profit_display", fi.get("profit", "0")),
        "debt": fi.get("debt_display", fi.get("debt", "0")),
        "cam_report": result.get("cam_report"),
        "full_result": result,
        "storage": "MongoDB" if _mongo_available else "SQLite"
    }

    mongo_id_str = None
    mdb = get_mongo_db()
    if mdb is not None:
        try:
            ins = mdb["analyses"].insert_one(doc)
            mongo_id_str = str(ins.inserted_id)
        except Exception:
            pass

    # Always dual-write to SQLite for local reliability
    sqlite_id = None
    try:
        with get_sqlite() as conn:
            cur = conn.execute("""
                INSERT INTO analyses
                  (mongo_id, user_id, company_name, created_at, risk_score, decision, interest_rate,
                   loan_amount, revenue, profit, debt, cam_report, full_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mongo_id_str, user_id, company, now_iso,
                a.get("risk_score"), a.get("decision"), a.get("interest_rate"),
                a.get("loan_amount"),
                fi.get("revenue_display", fi.get("revenue", "0")),
                fi.get("profit_display", fi.get("profit", "0")),
                fi.get("debt_display", fi.get("debt", "0")),
                result.get("cam_report"),
                json.dumps(result)
            ))
            conn.commit()
            sqlite_id = cur.lastrowid
    except Exception:
        pass

    return mongo_id_str or str(sqlite_id)


def fetch_history(limit=20):
    """Fetches recent analyses from MongoDB, falling back to SQLite."""
    mdb = get_mongo_db()
    if mdb is not None:
        try:
            cursor = mdb["analyses"].find(
                {},
                {
                    "_id": 1, "company_name": 1, "created_at": 1,
                    "risk_score": 1, "decision": 1, "loan_amount": 1,
                    "cam_report": 1
                }
            ).sort("created_at", pymongo.DESCENDING).limit(limit)

            rows = []
            for d in cursor:
                rows.append({
                    "id": str(d["_id"]),
                    "company_name": d.get("company_name", "Unknown"),
                    "created_at": d.get("created_at", ""),
                    "risk_score": d.get("risk_score", 0),
                    "decision": d.get("decision", "N/A"),
                    "loan_amount": d.get("loan_amount", "N/A"),
                    "cam_report": d.get("cam_report", ""),
                    "storage": "MongoDB"
                })
            if rows:
                return rows
        except Exception:
            pass

    # SQLite fallback
    try:
        with get_sqlite() as conn:
            cur = conn.execute("""
                SELECT id, company_name, created_at, risk_score, decision, loan_amount, cam_report
                FROM analyses ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []


def fetch_analysis_by_id(record_id):
    """Retrieves full analysis by MongoDB ObjectId or SQLite ID."""
    mdb = get_mongo_db()
    if mdb is not None:
        try:
            if ObjectId.is_valid(record_id):
                doc = mdb["analyses"].find_one({"_id": ObjectId(record_id)})
                if doc and "full_result" in doc:
                    return doc["full_result"]
        except Exception:
            pass

    # SQLite fallback
    try:
        with get_sqlite() as conn:
            row = None
            if str(record_id).isdigit():
                row = conn.execute("SELECT full_result FROM analyses WHERE id=?", (int(record_id),)).fetchone()
            if not row:
                row = conn.execute("SELECT full_result FROM analyses WHERE mongo_id=?", (str(record_id),)).fetchone()
            if row:
                return json.loads(row["full_result"])
    except Exception:
        pass
    return None


def get_system_storage_info():
    """Returns status of MongoDB and SQLite storage engines."""
    mdb = get_mongo_db()
    mongo_ok = mdb is not None
    mongo_count = 0
    if mongo_ok:
        try:
            mongo_count = mdb["analyses"].count_documents({})
        except Exception:
            mongo_count = 0

    sqlite_count = 0
    try:
        with get_sqlite() as conn:
            sqlite_count = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    except Exception:
        pass

    return {
        "primary_database": "MongoDB" if mongo_ok else "SQLite",
        "mongodb_connected": mongo_ok,
        "mongodb_uri": MONGO_URI,
        "mongodb_database": MONGO_DB_NAME,
        "mongodb_records": mongo_count,
        "sqlite_records": sqlite_count,
        "active_backend": "MongoDB (Primary) + SQLite (Replica)" if mongo_ok else "SQLite (Standalone)"
    }
