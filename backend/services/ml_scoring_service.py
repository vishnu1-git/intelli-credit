"""
ml_scoring_service.py
Real ML credit scoring model using scikit-learn RandomForestClassifier.
Trained on 2000 synthetic company profiles.
Covers: feature engineering, model training, evaluation, joblib persistence.
This is what AI/ML engineers are expected to know.
"""

import os
import json
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline

MODEL_PATH = os.path.join(os.path.dirname(__file__), "credit_model.joblib")
META_PATH  = os.path.join(os.path.dirname(__file__), "credit_model_meta.json")

FEATURE_NAMES = [
    "profit_margin_pct",
    "debt_to_revenue_ratio",
    "log_revenue_cr",
    "gst_mismatch_pct",
    "news_penalty_score",
    "bank_bounce_count",
    "bank_inflow_ratio",
    "has_litigation_flag",
    "has_auditor_qualification",
    "od_utilisation_pct",
]


# ── Synthetic training data ────────────────────────────────────────────────────

def _generate_training_data(n: int = 2000, seed: int = 42) -> tuple:
    """
    Generate realistic synthetic credit profiles.
    Label 0 = approve, 1 = reject.
    Feature relationships mirror real credit underwriting logic.
    """
    rng = np.random.default_rng(seed)

    # Feature distributions (realistic ranges)
    profit_margin      = rng.normal(8, 12, n).clip(-40, 40)
    debt_to_rev        = rng.exponential(0.6, n).clip(0, 5)
    log_rev            = rng.normal(2.5, 1.2, n).clip(0, 6)   # log10(revenue in Cr)
    gst_mismatch       = rng.exponential(6, n).clip(0, 40)
    news_penalty       = rng.choice([0, 0, 0, 5, 10, 20], n,
                                    p=[0.5, 0.2, 0.1, 0.1, 0.06, 0.04])
    bounce_count       = rng.choice([0, 0, 0, 1, 2, 5], n,
                                    p=[0.6, 0.15, 0.1, 0.08, 0.05, 0.02])
    inflow_ratio       = rng.normal(1.1, 0.3, n).clip(0.3, 3.0)
    has_litigation     = rng.choice([0, 1], n, p=[0.75, 0.25])
    has_auditor_qual   = rng.choice([0, 1], n, p=[0.88, 0.12])
    od_utilisation     = rng.uniform(0, 100, n)

    X = np.column_stack([
        profit_margin, debt_to_rev, log_rev, gst_mismatch, news_penalty,
        bounce_count, inflow_ratio, has_litigation, has_auditor_qual, od_utilisation
    ])

    # Label logic (mirrors underwriting rules)
    reject_score = (
        (profit_margin < 0).astype(float) * 30 +
        (debt_to_rev > 1.5).astype(float) * 25 +
        (gst_mismatch > 20).astype(float) * 15 +
        (news_penalty >= 20).astype(float) * 25 +
        (bounce_count >= 3).astype(float) * 20 +
        (inflow_ratio < 0.8).astype(float) * 15 +
        has_litigation * 10 +
        has_auditor_qual * 20 +
        (od_utilisation > 85).astype(float) * 15
    )
    # Add noise
    reject_score += rng.normal(0, 8, n)
    labels = (reject_score > 45).astype(int)

    return X, labels


# ── Model training ─────────────────────────────────────────────────────────────

def train_model() -> dict:
    """Train the credit scoring model and save to disk."""
    X, y = _generate_training_data(2000)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, output_dict=True)
    auc    = roc_auc_score(y_test, y_prob)
    cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc")

    joblib.dump(pipeline, MODEL_PATH)

    meta = {
        "accuracy":        round(report["accuracy"], 4),
        "auc_roc":         round(auc, 4),
        "cv_auc_mean":     round(float(cv_scores.mean()), 4),
        "cv_auc_std":      round(float(cv_scores.std()), 4),
        "precision_0":     round(report["0"]["precision"], 4),
        "recall_0":        round(report["0"]["recall"], 4),
        "precision_1":     round(report["1"]["precision"], 4),
        "recall_1":        round(report["1"]["recall"], 4),
        "feature_names":   FEATURE_NAMES,
        "n_training":      2000,
        "model_type":      "GradientBoostingClassifier",
        "trained_at":      __import__("datetime").datetime.now().isoformat(),
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    return meta


def _load_or_train():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    train_model()
    return joblib.load(MODEL_PATH)


_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_or_train()
    return _MODEL


# ── Feature engineering ────────────────────────────────────────────────────────

def build_features(
    financials: dict,
    gst: dict,
    research: dict,
    bank_data: dict | None,
) -> np.ndarray:
    """Convert raw analysis dicts into the model feature vector."""
    rev  = float(financials.get("revenue", 0) or 0)
    prof = float(financials.get("profit",  0) or 0)
    debt = float(financials.get("debt",    0) or 0)

    profit_margin    = (prof / rev * 100) if rev > 0 else -10
    debt_to_rev      = (debt / rev)       if rev > 0 else 2.0
    log_rev          = float(np.log10(max(rev / 1e7, 0.01)))  # in Crore

    gst_mismatch     = float(gst.get("gst_mismatch_percent", 5))
    news_penalty     = float(research.get("external_penalty", 0))

    pdf_flags        = financials.get("pdf_risk_flags", [])
    has_litigation   = float(
        any("litigation" in f.lower() or "legal" in f.lower() for f in pdf_flags))
    has_auditor_qual = float(
        any("auditor" in f.lower() or "going concern" in f.lower() for f in pdf_flags))

    bounce_count   = 0.0
    inflow_ratio   = 1.1
    od_utilisation = 0.0
    if bank_data and not bank_data.get("error"):
        bounce_count   = float(bank_data.get("bounce_count",   0))
        inflow_ratio   = float(bank_data.get("inflow_outflow_ratio", 1.1))
        od_utilisation = float(bank_data.get("od_utilisation_pct",   0))

    return np.array([[
        profit_margin, debt_to_rev, log_rev, gst_mismatch, news_penalty,
        bounce_count, inflow_ratio, has_litigation, has_auditor_qual, od_utilisation
    ]])


# ── Public API ─────────────────────────────────────────────────────────────────

def ml_credit_score(
    financials: dict,
    gst:        dict,
    research:   dict,
    bank_data:  dict | None = None,
) -> dict:
    """
    Run the ML model and return a rejection probability + grade.
    This score is used as one additional signal in risk_service.
    """
    try:
        model    = _get_model()
        features = build_features(financials, gst, research, bank_data)
        prob_reject = float(model.predict_proba(features)[0][1])
        prediction  = int(model.predict(features)[0])

        if prob_reject < 0.25:
            ml_grade, ml_adj = "ML Grade A — Low Risk",      +5
        elif prob_reject < 0.45:
            ml_grade, ml_adj = "ML Grade B — Moderate Risk",  0
        elif prob_reject < 0.65:
            ml_grade, ml_adj = "ML Grade C — Elevated Risk", -8
        else:
            ml_grade, ml_adj = "ML Grade D — High Risk",    -15

        feature_vals = build_features(financials, gst, research, bank_data)[0].tolist()

        return {
            "ml_reject_probability": round(prob_reject, 4),
            "ml_prediction":         "Reject" if prediction == 1 else "Approve",
            "ml_grade":              ml_grade,
            "ml_score_adjustment":   ml_adj,
            "ml_features":           dict(zip(FEATURE_NAMES, [round(v, 4) for v in feature_vals])),
            "error":                 None,
        }
    except Exception as e:
        return {
            "ml_reject_probability": 0.5,
            "ml_prediction":         "Unknown",
            "ml_grade":              "ML Unavailable",
            "ml_score_adjustment":   0,
            "ml_features":           {},
            "error":                 str(e),
        }


def get_model_metadata() -> dict:
    if os.path.exists(META_PATH):
        with open(META_PATH) as f:
            return json.load(f)
    return train_model()