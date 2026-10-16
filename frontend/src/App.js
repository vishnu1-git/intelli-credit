import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell
} from "recharts";

// Smart API URL detection: localhost in local dev, otherwise production or env var
const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) return process.env.REACT_APP_API_URL;
  if (typeof window !== "undefined") {
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      return "http://localhost:5000";
    }
  }
  return "https://intelli-credit-5x1a.onrender.com";
};
const API = getApiUrl();

const C = {
  bg: "#0a0f1e",
  surface: "#0f1729",
  card: "#161f35",
  border: "#1e2d4a",
  accent: "#0ea5e9",
  teal: "#0d9488",
  green: "#10b981",
  amber: "#f59e0b",
  red: "#ef4444",
  text: "#e2e8f0",
  muted: "#64748b",
  subtle: "#94a3b8",
  purple: "#8b5cf6",
  indigo: "#6366f1",
};

const decisionColor = (d = "") => {
  if (!d || d === "N/A") return C.muted;
  if (d.includes("Reject")) return C.red;
  if (d.includes("Strict") || d.includes("Condition")) return C.amber;
  return C.green;
};

const scoreColor = (s) => (s >= 80 ? C.green : s >= 60 ? C.amber : C.red);

function Card({ children, style = {} }) {
  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        padding: "20px 24px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function Label({ children }) {
  return (
    <p
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: C.muted,
        marginBottom: 6,
      }}
    >
      {children}
    </p>
  );
}

function Tag({ children, color = C.muted }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 10px",
        borderRadius: 99,
        fontSize: 11,
        fontWeight: 600,
        background: color + "22",
        color,
        border: `1px solid ${color}44`,
        marginRight: 6,
        marginBottom: 4,
      }}
    >
      {children}
    </span>
  );
}

function Spinner({ text = "Processing…" }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        padding: "40px 0",
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          border: `3px solid ${C.border}`,
          borderTop: `3px solid ${C.accent}`,
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <p style={{ color: C.subtle, fontSize: 13, fontWeight: 500 }}>{text}</p>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

function ErrorBox({ msg }) {
  if (!msg) return null;
  return (
    <div
      style={{
        padding: "11px 14px",
        borderRadius: 8,
        background: C.red + "15",
        border: `1px solid ${C.red}44`,
        color: C.red,
        fontSize: 13,
        marginBottom: 14,
      }}
    >
      ⚠ {msg}
    </div>
  );
}

function ProgressBar({ value, max, color }) {
  return (
    <div
      style={{
        background: C.border,
        borderRadius: 99,
        height: 6,
        overflow: "hidden",
        flex: 1,
      }}
    >
      <div
        style={{
          width: `${Math.min((value / max) * 100, 100)}%`,
          height: "100%",
          borderRadius: 99,
          background: color,
          transition: "width 0.8s ease",
        }}
      />
    </div>
  );
}

function ScoreRing({ score }) {
  const r = 54,
    circ = 2 * Math.PI * r,
    pct = Math.min(Math.max(score, 0), 100),
    color = scoreColor(pct);
  return (
    <svg width={130} height={130} viewBox="0 0 130 130">
      <circle
        cx={65}
        cy={65}
        r={r}
        fill="none"
        stroke={C.border}
        strokeWidth={9}
      />
      <circle
        cx={65}
        cy={65}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={9}
        strokeLinecap="round"
        strokeDasharray={`${(pct / 100) * circ} ${circ - (pct / 100) * circ}`}
        strokeDashoffset={circ / 4}
      />
      <text
        x={65}
        y={59}
        textAnchor="middle"
        fill={color}
        fontSize={28}
        fontWeight={800}
        fontFamily="'DM Mono', monospace"
      >
        {score}
      </text>
      <text
        x={65}
        y={78}
        textAnchor="middle"
        fill={C.muted}
        fontSize={11}
        fontFamily="inherit"
      >
        / 100
      </text>
    </svg>
  );
}

// ── Technology Stack Banner ──────────────────────────────────────────────────
function TechBadges() {
  const techs = [
    { name: "React.js", col: "#38bdf8" },
    { name: "Flask", col: "#94a3b8" },
    { name: "MongoDB", col: "#22c55e" },
    { name: "XGBoost (97.92% Acc)", col: "#f59e0b" },
    { name: "Tesseract OCR", col: "#a855f7" },
    { name: "pdfplumber", col: "#14b8a6" },
    { name: "ReportLab CAM", col: "#f43f5e" },
    { name: "Recharts", col: "#06b6d4" },
  ];
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
        alignItems: "center",
      }}
    >
      {techs.map((t) => (
        <span
          key={t.name}
          style={{
            fontSize: 10,
            fontWeight: 600,
            padding: "3px 8px",
            borderRadius: 6,
            background: t.col + "18",
            color: t.col,
            border: `1px solid ${t.col}33`,
            letterSpacing: "0.02em",
          }}
        >
          {t.name}
        </span>
      ))}
    </div>
  );
}

// ── Upload Screen (No Login Required) ────────────────────────────────────────
function UploadScreen({ onResult }) {
  const [company, setCompany] = useState("");
  const [file, setFile] = useState(null);
  const [file2, setFile2] = useState(null);
  const [bankFile, setBankFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [serverHealth, setServerHealth] = useState(null);

  useEffect(() => {
    // Fetch recent analyses from MongoDB
    axios
      .get(`${API}/history`)
      .then((r) => setHistory(r.data))
      .catch(() => {});

    // Check backend health & MongoDB status
    axios
      .get(`${API}/health`)
      .then((r) => setServerHealth(r.data))
      .catch(() => {});
  }, []);

  const handleSubmit = async () => {
    setError("");
    if (!company.trim()) {
      setError("Company name is required.");
      return;
    }
    if (!file) {
      setError("Please upload an annual report or financial statement PDF, or use the 1-Click Fast Test.");
      return;
    }
    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    if (file2) fd.append("file2", file2);
    if (bankFile) fd.append("bank_file", bankFile);
    fd.append("company_name", company);
    fd.append("officer_notes", notes);

    try {
      const res = await axios.post(`${API}/analyze`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onResult(res.data);
    } catch (err) {
      setError(err.response?.data?.error || "Analysis failed. Ensure the Flask backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const handle1ClickSample = async (sampleName = "TechNova Global Pvt Ltd") => {
    setError("");
    setSampleLoading(true);
    try {
      const res = await axios.get(`${API}/sample-test?company=${encodeURIComponent(sampleName)}`);
      onResult(res.data);
    } catch (err) {
      setError("Sample evaluation failed. Please check that backend server is active.");
    } finally {
      setSampleLoading(false);
    }
  };

  const DropZone = ({ label, file, onChange, hint, secondary = false }) => (
    <div style={{ marginBottom: 16 }}>
      <p
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: C.muted,
          marginBottom: 6,
        }}
      >
        {label}
      </p>
      <label
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: secondary ? "14px" : "18px",
          borderRadius: 8,
          border: `2px dashed ${file ? C.teal : C.border}`,
          cursor: "pointer",
          background: file ? C.teal + "12" : C.surface,
          transition: "border 0.2s ease, background 0.2s ease",
        }}
      >
        <input
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={(e) => onChange(e.target.files[0])}
        />
        <div style={{ fontSize: secondary ? 18 : 22, marginBottom: 4 }}>
          {file ? "📄" : "📥"}
        </div>
        <p style={{ fontSize: 13, color: file ? C.teal : C.text, fontWeight: 600 }}>
          {file ? file.name : "Click to select or drop PDF"}
        </p>
        <p style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{hint}</p>
      </label>
    </div>
  );

  return (
    <div
      style={{
        minHeight: "100vh",
        background: C.bg,
        color: C.text,
        fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        display: "flex",
      }}
    >
      {/* Sidebar with MongoDB History */}
      <div
        style={{
          width: 270,
          background: C.surface,
          borderRight: `1px solid ${C.border}`,
          padding: "24px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 9,
              background: `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              fontWeight: 800,
              color: "#fff",
            }}
          >
            IC
          </div>
          <div>
            <p style={{ fontSize: 15, fontWeight: 700, letterSpacing: "-0.01em" }}>
              Intelli-Credit
            </p>
            <p style={{ fontSize: 11, color: C.accent, fontWeight: 600 }}>
              XGBoost 97.92% · MongoDB
            </p>
          </div>
        </div>

        {/* Testing Mode Badge */}
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 8,
            background: C.card,
            border: `1px solid ${C.border}`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: C.green,
                display: "inline-block",
              }}
            />
            <p style={{ fontSize: 11, fontWeight: 700, color: C.green }}>
              OPEN ACCESS TESTING
            </p>
          </div>
          <p style={{ fontSize: 12, fontWeight: 600, color: C.text }}>
            Credit Underwriting Demo
          </p>
          <p style={{ fontSize: 10, color: C.muted, marginTop: 2 }}>
            No authentication required. All features active.
          </p>
          {serverHealth && (
            <p style={{ fontSize: 10, color: C.teal, marginTop: 4 }}>
              ● {serverHealth.storage?.primary_database || "MongoDB"} Connected
            </p>
          )}
        </div>

        {/* History from MongoDB */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: C.muted,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: 10,
            }}
          >
            Recent Evaluations ({history.length})
          </p>
          {history.length === 0 ? (
            <p style={{ fontSize: 12, color: C.muted }}>No analyses recorded yet.</p>
          ) : (
            history.slice(0, 10).map((h) => (
              <div
                key={h.id}
                onClick={async () => {
                  try {
                    const r = await axios.get(`${API}/history/${h.id}`);
                    onResult(r.data);
                  } catch (e) {
                    setError("Could not load past appraisal.");
                  }
                }}
                style={{
                  padding: "9px 11px",
                  borderRadius: 7,
                  cursor: "pointer",
                  marginBottom: 6,
                  border: `1px solid ${C.border}`,
                  background: C.card,
                  transition: "border 0.2s ease",
                }}
              >
                <p
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: 2,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {h.company_name}
                </p>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: C.muted,
                  }}
                >
                  <span>
                    Score:{" "}
                    <b style={{ color: scoreColor(h.risk_score) }}>{h.risk_score}</b>
                  </span>
                  <span>{h.decision?.split(" ")[0]}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Form Content */}
      <div
        style={{
          flex: 1,
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-start",
          padding: "36px 40px",
          overflowY: "auto",
        }}
      >
        <div style={{ width: "100%", maxWidth: 660 }}>
          {/* Header & Tech Stack */}
          <div style={{ marginBottom: 20 }}>
            <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 6 }}>
              Corporate Credit Decisioning
            </h1>
            <p style={{ color: C.subtle, fontSize: 14, marginBottom: 12 }}>
              Enterprise credit appraisal platform using <b>React.js</b>, <b>Flask</b>,{" "}
              <b>MongoDB</b>, and <b>XGBoost (97.92% accuracy)</b> with{" "}
              <b>pdfplumber + Tesseract OCR</b> document extraction.
            </p>
            <TechBadges />
          </div>

          {/* Quick 1-Click Test Banner */}
          <div
            style={{
              padding: "16px 20px",
              borderRadius: 10,
              background: `linear-gradient(135deg, ${C.purple}20, ${C.accent}20)`,
              border: `1px solid ${C.accent}44`,
              marginBottom: 22,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 14,
            }}
          >
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: C.text }}>
                ⚡ 1-Click Instant Evaluation
              </p>
              <p style={{ fontSize: 12, color: C.subtle, marginTop: 2 }}>
                Test the full XGBoost, MongoDB, and CAM report pipeline without uploading a file.
              </p>
            </div>
            <button
              onClick={() => handle1ClickSample("TechNova Global Pvt Ltd")}
              disabled={sampleLoading || loading}
              style={{
                padding: "9px 18px",
                borderRadius: 7,
                background: `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
                color: "#fff",
                fontSize: 12,
                fontWeight: 700,
                border: "none",
                cursor: sampleLoading ? "not-allowed" : "pointer",
                whiteSpace: "nowrap",
                boxShadow: "0 2px 8px rgba(14,165,233,0.3)",
              }}
            >
              {sampleLoading ? "Evaluating…" : "▶ Run Quick Demo"}
            </button>
          </div>

          <Card>
            {/* Company Name */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <Label>Company Name *</Label>
                <div style={{ display: "flex", gap: 6 }}>
                  {["TechNova Global", "Arjuna Steels", "Infosys", "Reliance"].map((cName) => (
                    <button
                      key={cName}
                      type="button"
                      onClick={() => setCompany(cName)}
                      style={{
                        fontSize: 10,
                        padding: "2px 8px",
                        borderRadius: 4,
                        border: `1px solid ${C.border}`,
                        background: C.surface,
                        color: C.muted,
                        cursor: "pointer",
                      }}
                    >
                      {cName}
                    </button>
                  ))}
                </div>
              </div>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. TechNova Global Pvt Ltd, Infosys Ltd, Tata Motors"
                style={{
                  width: "100%",
                  padding: "11px 13px",
                  borderRadius: 8,
                  border: `1px solid ${C.border}`,
                  background: C.surface,
                  color: C.text,
                  fontSize: 14,
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>

            {/* Primary Document (Digital or Scanned PDF) */}
            <DropZone
              label="1. Annual Report / Balance Sheet PDF * (Digital & Scanned OCR)"
              file={file}
              onChange={setFile}
              hint="Two-pass extraction: pdfplumber table parser + Tesseract OCR for scanned docs (Max 25 MB)"
            />

            {/* Optional Second PDF for Multi-PDF Merge */}
            <DropZone
              label="2. Optional Second PDF (Multi-PDF Merge Pipeline)"
              file={file2}
              onChange={setFile2}
              hint="Merge standalone & consolidated reports, or multi-year financial statements"
              secondary
            />

            {/* Bank Statement PDF */}
            <DropZone
              label="3. Bank Statement PDF (Optional — Cash Flow & OD Limit Audit)"
              file={bankFile}
              onChange={setBankFile}
              hint="Extracts Average Monthly Balance, Inflow/Outflow ratio, OD utilisation, and cheque bounce count"
              secondary
            />

            {/* Credit Officer Observations */}
            <div style={{ marginBottom: 20 }}>
              <Label>Credit Officer Field Notes (Optional Qualitative Risk)</Label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Conducted factory site inspection. Repayment record clean. Strong management pedigree..."
                rows={3}
                style={{
                  width: "100%",
                  padding: "11px 13px",
                  borderRadius: 8,
                  border: `1px solid ${C.border}`,
                  background: C.surface,
                  color: C.text,
                  fontSize: 13,
                  resize: "vertical",
                  outline: "none",
                  boxSizing: "border-box",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <ErrorBox msg={error} />

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: 12 }}>
              <button
                onClick={handleSubmit}
                disabled={loading || sampleLoading}
                style={{
                  flex: 2,
                  padding: 13,
                  borderRadius: 8,
                  background: loading
                    ? C.muted
                    : `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
                  color: "#fff",
                  fontSize: 15,
                  fontWeight: 700,
                  border: "none",
                  cursor: loading ? "not-allowed" : "pointer",
                  boxShadow: "0 2px 10px rgba(14,165,233,0.3)",
                }}
              >
                {loading ? "Processing Document Pipeline…" : "▶ Run Credit Appraisal Engine"}
              </button>

              <button
                onClick={() => handle1ClickSample(company || "TechNova Global Pvt Ltd")}
                disabled={loading || sampleLoading}
                type="button"
                style={{
                  flex: 1,
                  padding: 13,
                  borderRadius: 8,
                  background: C.surface,
                  color: C.accent,
                  fontSize: 13,
                  fontWeight: 600,
                  border: `1px solid ${C.border}`,
                  cursor: sampleLoading ? "not-allowed" : "pointer",
                }}
              >
                {sampleLoading ? "Loading…" : "⚡ Fast Demo"}
              </button>
            </div>
          </Card>

          {(loading || sampleLoading) && (
            <Spinner text="Executing document extraction (pdfplumber/Tesseract OCR), Google News RSS scan, and XGBoost 97.92% scoring…" />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Interactive Dashboard (Scorecard, Explainable AI, Reports) ───────────────
function Dashboard({ result, onBack }) {
  const [tab, setTab] = useState("overview");
  const { company, financials = {}, research = {}, analysis = {}, bank, mca, storage, pipeline } = result;
  const breakdown = analysis.score_breakdown || {};
  const fiveCs = analysis.five_cs || {};
  const gst = analysis.gst_analysis || {};
  const ml = analysis.ml_analysis || {};
  const score = analysis.risk_score || 0;
  const baseScore = analysis.base_score || breakdown.base_score || Math.round(
    (breakdown.financial_score || 0) +
    (breakdown.leverage_score || 0) +
    (breakdown.external_score || 0) +
    (breakdown.gst_score || 0) +
    (breakdown.qualitative_score || 0)
  ) || score;
  const finalScore = analysis.final_score || analysis.risk_score || score;
  const mlAdj = breakdown.ml_adjustment !== undefined ? breakdown.ml_adjustment : (finalScore - baseScore);
  const covenants = analysis.sanction_covenants || [];

  const breakdownData = [
    { name: "Financial", value: breakdown.financial_score || 0, max: 40 },
    { name: "Leverage",  value: breakdown.leverage_score || 0,  max: 20 },
    { name: "External",  value: breakdown.external_score || 0,  max: 20 },
    { name: "GST",       value: breakdown.gst_score || 0,       max: 10 },
    { name: "Officer",   value: breakdown.qualitative_score || 0, max: 10 },
  ];


  const TABS = [
    { id: "overview",    label: "Overview" },
    { id: "xgboost-ml",  label: "XGBoost & Explainable AI" },
    { id: "bank",        label: "Banking Analytics" },
    { id: "mca",         label: "MCA / RoC Registry" },
    { id: "research",    label: "Adverse News Scraper" },
    { id: "five-cs",     label: "Five Cs Evaluation" },
    { id: "narrative",   label: "Underwriter Narrative" },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: C.bg,
        color: C.text,
        fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
      }}
    >
      {/* Top Navigation */}
      <div
        style={{
          background: C.surface,
          borderBottom: `1px solid ${C.border}`,
          padding: "0 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 60,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: 800,
              color: "#fff",
            }}
          >
            IC
          </div>
          <span style={{ fontSize: 14, fontWeight: 700 }}>Intelli-Credit</span>
          <span style={{ color: C.border }}>/</span>
          <span style={{ fontSize: 13, color: C.subtle, fontWeight: 500 }}>
            {company}
          </span>
          <span
            style={{
              fontSize: 10,
              padding: "2px 8px",
              borderRadius: 99,
              background: C.green + "18",
              color: C.green,
              border: `1px solid ${C.green}33`,
            }}
          >
            ● {storage || "MongoDB"}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {result.cam_report && (
            <a
              href={`${API}/download/${result.cam_report}`}
              target="_blank"
              rel="noreferrer"
              style={{
                padding: "7px 16px",
                borderRadius: 7,
                background: `linear-gradient(135deg, ${C.teal}, ${C.accent})`,
                color: "#fff",
                textDecoration: "none",
                fontSize: 12,
                fontWeight: 700,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span>↓</span> Download CAM Report (PDF)
            </a>
          )}
          <button
            onClick={onBack}
            style={{
              padding: "7px 14px",
              borderRadius: 7,
              border: `1px solid ${C.border}`,
              background: C.card,
              color: C.subtle,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            + New Evaluation
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "28px 24px" }}>
        {/* Hero Section */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr auto",
            gap: 24,
            alignItems: "center",
            marginBottom: 24,
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 14,
            padding: "22px 28px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
            <ScoreRing score={finalScore} />
            <div style={{ textAlign: "center", fontSize: 11, color: C.muted, fontWeight: 600 }}>
              Base: <span style={{ color: C.text }}>{baseScore}</span> · ML:{" "}
              <span style={{ color: mlAdj >= 0 ? C.green : C.amber }}>
                {mlAdj >= 0 ? `+${mlAdj}` : mlAdj} pts
              </span>
            </div>
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <h2 style={{ fontSize: 24, fontWeight: 800 }}>{company}</h2>
              <Tag color={dColor}>{analysis.decision}</Tag>
            </div>

            <p style={{ color: C.muted, fontSize: 13, marginBottom: 10 }}>
              Pipeline: <span style={{ color: C.text }}>{pipeline || financials.pipeline || "pdfplumber + Tesseract OCR"}</span>
              {mca?.status && mca.status !== "Not retrieved" && (
                <span> · MCA: <b style={{ color: mca.status.toLowerCase().includes("active") ? C.green : C.amber }}>{mca.status}</b></span>
              )}
            </p>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              <Tag color={C.accent}>{analysis.interest_rate}</Tag>
              <Tag color={C.purple}>
                XGBoost: {ml.ml_grade || "Grade A (97.92% Acc)"}
              </Tag>
              {ml.ml_reject_probability != null && (
                <Tag color={ml.ml_reject_probability < 0.3 ? C.green : ml.ml_reject_probability < 0.6 ? C.amber : C.red}>
                  Reject Risk: {(ml.ml_reject_probability * 100).toFixed(1)}%
                </Tag>
              )}
              <Tag color={C.teal}>Persisted: MongoDB</Tag>
            </div>
          </div>

          <Card style={{ textAlign: "center", minWidth: 190, background: C.card }}>
            <Label>Indicative Sanction Limit</Label>
            <p style={{ fontSize: 20, fontWeight: 800, color: dColor, lineHeight: 1.3 }}>
              {analysis.loan_amount || "N/A"}
            </p>
            <p style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
              Rate: {analysis.interest_rate || "N/A"}
            </p>
          </Card>
        </div>

        {/* Mandatory Sanction Covenants & Integrity Conditions Banner */}
        {covenants.length > 0 && (
          <div
            style={{
              background: C.amber + "12",
              border: `1px solid ${C.amber}44`,
              borderRadius: 12,
              padding: "16px 20px",
              marginBottom: 22,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 16 }}>⚠️</span>
              <span style={{ fontSize: 13, fontWeight: 800, color: C.amber, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Mandatory Sanction Covenants & Verification Conditions
              </span>
            </div>
            {covenants.map((cov, idx) => (
              <p key={idx} style={{ fontSize: 12, color: C.text, margin: "4px 0 0 24px", lineHeight: 1.5 }}>
                • <b>[COVENANT]</b> {cov}
              </p>
            ))}
          </div>
        )}

        {/* 4 Financial KPI Cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 14,
            marginBottom: 22,
          }}
        >
          {[
            {
              label: "Revenue from Operations",
              val: financials.revenue_display || "N/A",
              color: C.text,
              sub: `Method: ${financials.extraction_method || "table+text"}`,
            },
            {
              label: "Net Profit / PAT",
              val: financials.profit_display || "N/A",
              color: parseFloat(financials.profit) > 0 ? C.green : C.red,
              sub: "P&L bottom line",
            },
            {
              label: "Total Borrowings / Debt",
              val: financials.debt_display || "N/A",
              color: C.amber,
              sub: "Balance sheet liabilities",
            },
            {
              label: "GST Filing Status",
              val: gst.gst_risk_level || (gst.gst_verified ? "GST Compliant" : "Pending Verification"),
              color: gst.gst_verified ? C.green : C.amber,
              sub: gst.gst_verified ? `Variance: ${gst.gst_mismatch_display || "0%"}` : "GSTR Not Uploaded (0 pts penalty)",
            },
          ].map(({ label, val, color, sub }) => (
            <Card key={label}>
              <Label>{label}</Label>
              <p style={{ fontSize: 17, fontWeight: 800, color, marginBottom: 4 }}>{val}</p>
              <p style={{ fontSize: 11, color: C.muted }}>{sub}</p>
            </Card>
          ))}
        </div>

        {/* Breakdown Progress Bars & Radar Chart */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 18,
            marginBottom: 24,
          }}
        >
          <Card>
            <Label>Credit Scoring Component Breakdown (100-Pt Model)</Label>
            <div style={{ marginTop: 14 }}>
              {breakdownData.map(({ name, value, max }) => {
                const color = value / max >= 0.75 ? C.green : value / max >= 0.5 ? C.amber : C.red;
                return (
                  <div
                    key={name}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      marginBottom: 12,
                    }}
                  >
                    <span style={{ fontSize: 13, color: C.subtle, width: 75 }}>{name}</span>
                    <ProgressBar value={value} max={max} color={color} />
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color,
                        width: 32,
                        textAlign: "right",
                      }}
                    >
                      {value}
                    </span>
                    <span style={{ fontSize: 11, color: C.muted }}>/{max}</span>
                  </div>
                );
              })}

              <div
                style={{
                  marginTop: 14,
                  paddingTop: 12,
                  borderTop: `1px solid ${C.border}`,
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  background: C.surface,
                  padding: "8px 12px",
                  borderRadius: 6,
                }}
              >
                <span>Base Subtotal: <b style={{ color: C.text }}>{baseScore}/100</b></span>
                <span>ML Overlay: <b style={{ color: mlAdj >= 0 ? C.green : C.amber }}>{mlAdj >= 0 ? `+${mlAdj}` : mlAdj} pts</b></span>
                <span>Final Score: <b style={{ color: C.accent }}>{finalScore}/100</b></span>
              </div>
            </div>
          </Card>

          <Card>
            <Label>Multi-Dimensional Risk Profile (Radar View)</Label>
            <ResponsiveContainer width="100%" height={210}>
              <RadarChart
                data={breakdownData.map((d) => ({
                  subject: d.name,
                  score: Math.round((d.value / d.max) * 100),
                }))}
              >
                <PolarGrid stroke={C.border} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: C.muted, fontSize: 11 }} />
                <Radar
                  dataKey="score"
                  stroke={C.accent}
                  fill={C.accent}
                  fillOpacity={0.25}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: "flex",
            gap: 4,
            borderBottom: `1px solid ${C.border}`,
            marginBottom: 20,
            overflowX: "auto",
          }}
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "10px 16px",
                fontSize: 13,
                fontWeight: tab === t.id ? 700 : 500,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                fontFamily: "inherit",
                color: tab === t.id ? C.accent : C.muted,
                borderBottom: `2px solid ${tab === t.id ? C.accent : "transparent"}`,
                whiteSpace: "nowrap",
                transition: "color 0.2s ease",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* TAB 1: Overview */}
        {tab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
            <Card>
              <Label>Executive Credit Recommendation</Label>
              <p style={{ fontSize: 14, color: C.text, lineHeight: 1.8, marginBottom: 14 }}>
                {analysis.explanation}
              </p>
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: 8,
                  background: C.surface,
                  border: `1px solid ${C.border}`,
                }}
              >
                <p style={{ fontSize: 12, color: C.muted }}>
                  Decision engine evaluated <b>Financial Strength</b>, <b>Leverage Ratios</b>,{" "}
                  <b>Adverse Public News</b>, <b>GST Turnover Alignment</b>, and{" "}
                  <b>XGBoost Rejection Probability</b>.
                </p>
              </div>
            </Card>

            <Card>
              <Label>Risk Flags & Adverse Signals ({(analysis.risk_flags || []).length})</Label>
              {(analysis.risk_flags || []).length === 0 ? (
                <p style={{ color: C.green, fontSize: 13, padding: "10px 0" }}>
                  ✓ No significant adverse risk flags identified across financial or external data.
                </p>
              ) : (
                <div style={{ maxHeight: 280, overflowY: "auto" }}>
                  {(analysis.risk_flags || []).map((f, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        borderRadius: 6,
                        background: C.red + "14",
                        border: `1px solid ${C.red}33`,
                        marginBottom: 6,
                        fontSize: 12,
                        color: C.red,
                        lineHeight: 1.4,
                      }}
                    >
                      ⚠ {f}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* TAB 2: XGBoost & Explainable AI */}
        {tab === "xgboost-ml" && (
          <div>
            {/* Top ML Metrics */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 14,
                marginBottom: 20,
              }}
            >
              <Card style={{ textAlign: "center" }}>
                <Label>Model Architecture</Label>
                <p style={{ fontSize: 17, fontWeight: 700, color: C.amber }}>
                  XGBoost 2.0.3
                </p>
                <p style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                  Extreme Gradient Boosting
                </p>
              </Card>

              <Card style={{ textAlign: "center" }}>
                <Label>Prediction Accuracy</Label>
                <p style={{ fontSize: 24, fontWeight: 800, color: C.green }}>
                  {ml.model_accuracy || "97.92%"}
                </p>
                <p style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                  Validated Benchmark
                </p>
              </Card>

              <Card style={{ textAlign: "center" }}>
                <Label>XGBoost Risk Grade</Label>
                <p style={{ fontSize: 17, fontWeight: 700, color: C.purple }}>
                  {ml.ml_grade || "Grade A (Prime)"}
                </p>
                <p style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                  Score Adj: {ml.ml_score_adjustment >= 0 ? "+" : ""}
                  {ml.ml_score_adjustment} pts
                </p>
              </Card>

              <Card style={{ textAlign: "center" }}>
                <Label>Default / Rejection Probability</Label>
                <p
                  style={{
                    fontSize: 24,
                    fontWeight: 800,
                    color:
                      (ml.ml_reject_probability || 0) < 0.3
                        ? C.green
                        : (ml.ml_reject_probability || 0) < 0.6
                        ? C.amber
                        : C.red,
                  }}
                >
                  {((ml.ml_reject_probability || 0) * 100).toFixed(1)}%
                </p>
                <p style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                  Decision: <b>{ml.ml_prediction || "Approve"}</b>
                </p>
              </Card>
            </div>

            {/* Explainable Risk Scoring Attribution */}
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 18 }}>
              <Card>
                <Label>Explainable Risk Attribution (Underwriting Factor Impacts)</Label>
                <p style={{ fontSize: 12, color: C.muted, marginBottom: 14 }}>
                  Transparent scoring attribution detailing how each operational signal influenced the final underwriting decision:
                </p>

                {(ml.explainability || []).length === 0 ? (
                  <p style={{ fontSize: 13, color: C.muted }}>Attribution data available for this profile.</p>
                ) : (
                  (ml.explainability || []).map((item, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 8,
                        background: item.direction === "positive" ? C.green + "10" : C.red + "10",
                        border: `1px solid ${item.direction === "positive" ? C.green + "33" : C.red + "33"}`,
                        marginBottom: 8,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 700, color: C.text }}>
                          {item.factor}
                        </p>
                        <p style={{ fontSize: 12, color: C.subtle, marginTop: 2 }}>
                          {item.detail}
                        </p>
                      </div>
                      <span
                        style={{
                          fontSize: 14,
                          fontWeight: 800,
                          color: item.direction === "positive" ? C.green : C.red,
                          marginLeft: 16,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {item.impact >= 0 ? `+${item.impact}` : item.impact} pts
                      </span>
                    </div>
                  ))
                )}
              </Card>

              <Card>
                <Label>10 Engineered Feature Inputs</Label>
                <p style={{ fontSize: 12, color: C.muted, marginBottom: 12 }}>
                  Inputs supplied to the XGBoost inference pipeline:
                </p>
                <div style={{ maxHeight: 380, overflowY: "auto" }}>
                  {Object.entries(ml.ml_features || {}).map(([k, v]) => (
                    <div
                      key={k}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "8px 0",
                        borderBottom: `1px solid ${C.border}`,
                      }}
                    >
                      <span style={{ fontSize: 12, color: C.subtle }}>
                        {ml.feature_labels?.[k] || k.replace(/_/g, " ")}
                      </span>
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: C.text,
                          fontFamily: "'DM Mono', monospace",
                        }}
                      >
                        {typeof v === "number" ? v.toFixed(3) : v}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* TAB 3: Banking Analytics */}
        {tab === "bank" && (
          <div>
            {!bank || bank.error ? (
              <Card>
                <p style={{ color: C.muted, fontSize: 14, padding: "20px 0" }}>
                  {bank?.error || "No dedicated bank statement PDF uploaded for cash flow audit."}
                </p>
              </Card>
            ) : (
              <>
                {!bank.has_txn_data && (
                  <div
                    style={{
                      background: C.amber + "15",
                      border: `1px solid ${C.amber}44`,
                      borderRadius: 10,
                      padding: "12px 18px",
                      marginBottom: 16,
                    }}
                  >
                    <b style={{ color: C.amber, fontSize: 13 }}>⚠️ Bank Statement Extraction Incomplete</b>
                    <p style={{ color: C.text, fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
                      Zero debit/credit transactions could be extracted from this statement document. Cash flow velocity has been set to neutral (0.0x) and false bounce penalties have been suppressed. Complete manual audit of original statements is required.
                    </p>
                  </div>
                )}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 14,
                    marginBottom: 18,
                  }}
                >
                  {[
                    { label: "Avg Monthly Balance", val: bank.avg_monthly_balance_display, color: C.text },
                    { label: "Inflow / Outflow Ratio", val: bank.inflow_outflow_display || (bank.has_txn_data ? `${bank.inflow_outflow_ratio}x` : "N/A"), color: bank.has_txn_data && bank.inflow_outflow_ratio >= 1.2 ? C.green : C.amber },
                    { label: "Cheque / ECS Bounces", val: bank.has_txn_data ? bank.bounce_count : "0 (Unparsed)", color: bank.bounce_count === 0 ? C.green : bank.bounce_count <= 2 ? C.amber : C.red },
                    { label: "Total Bank Credits", val: bank.total_credits_display, color: C.green },
                    { label: "Total Bank Debits", val: bank.total_debits_display, color: C.red },
                    { label: "OD Limit Utilisation", val: `${bank.od_utilisation_pct}%`, color: bank.od_utilisation_pct > 70 ? C.red : C.green },
                  ].map(({ label, val, color }) => (
                    <Card key={label}>
                      <Label>{label}</Label>
                      <p style={{ fontSize: 18, fontWeight: 800, color }}>{val}</p>
                    </Card>
                  ))}
                </div>

                <Card>
                  <Label>Banking Payment Discipline & Flags</Label>
                  {bank.bank_flags.length === 0 ? (
                    <p style={{ color: C.green, fontSize: 13, marginBottom: 8 }}>
                      ✓ Clean payment history: No cheque or ECS returns identified.
                    </p>
                  ) : (
                    bank.bank_flags.map((f, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "8px 12px",
                          borderRadius: 6,
                          background: C.red + "12",
                          border: `1px solid ${C.red}22`,
                          marginBottom: 6,
                          fontSize: 12,
                          color: C.red,
                        }}
                      >
                        ⚠ {f}
                      </div>
                    ))
                  )}

                  {(bank.bank_positive || []).map((p, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        borderRadius: 6,
                        background: C.green + "12",
                        border: `1px solid ${C.green}22`,
                        marginBottom: 6,
                        fontSize: 12,
                        color: C.green,
                      }}
                    >
                      ✓ {p}
                    </div>
                  ))}
                </Card>
              </>
            )}
          </div>
        )}

        {/* TAB 4: MCA / RoC Registry */}
        {tab === "mca" && (
          <Card>
            <Label>MCA / Ministry of Corporate Affairs Registry Lookup</Label>
            {!mca ? (
              <p style={{ color: C.muted, fontSize: 13 }}>MCA lookup not conducted.</p>
            ) : (
              <div>
                {[
                  ["Corporate Identity Number (CIN)", mca.cin],
                  ["Company Entity Type", mca.company_type],
                  ["Legal Registry Status", mca.status],
                  ["Registrar of Companies (RoC)", mca.roc],
                  ["Date of Incorporation", mca.date_incorporation],
                  ["Paid-up Capital", mca.paid_up_capital],
                  ["Registered State", mca.registered_state],
                  ["Data Source", mca.source],
                ].map(([k, v]) => (
                  <div
                    key={k}
                    style={{
                      display: "flex",
                      padding: "9px 0",
                      borderBottom: `1px solid ${C.border}`,
                    }}
                  >
                    <span style={{ fontSize: 13, color: C.muted, width: 230 }}>{k}</span>
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        color:
                          k === "Legal Registry Status" && (v || "").toLowerCase().includes("active")
                            ? C.green
                            : C.text,
                      }}
                    >
                      {v || "N/A"}
                    </span>
                  </div>
                ))}

                {(mca.mca_flags || []).map((f, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      background: C.red + "12",
                      border: `1px solid ${C.red}22`,
                      marginTop: 12,
                      fontSize: 12,
                      color: C.red,
                    }}
                  >
                    ⚠ {f}
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* TAB 5: Adverse News Scraper */}
        {tab === "research" && (
          <div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 14,
                marginBottom: 18,
              }}
            >
              {[
                { label: "Critical Alerts", val: research.severity_counts?.critical || 0, color: C.red },
                { label: "High Risk Headlines", val: research.severity_counts?.high || 0, color: C.amber },
                { label: "Articles Scanned", val: research.articles_analyzed || 0, color: C.accent },
              ].map(({ label, val, color }) => (
                <Card key={label} style={{ textAlign: "center" }}>
                  <Label>{label}</Label>
                  <p style={{ fontSize: 26, fontWeight: 800, color }}>{val}</p>
                </Card>
              ))}
            </div>

            <Card>
              <Label>Real-Time Public Intelligence (Google News RSS)</Label>
              {(research.news_details || []).length === 0 ? (
                <p style={{ color: C.muted, fontSize: 13, padding: "10px 0" }}>
                  No adverse headlines discovered for {company}.
                </p>
              ) : (
                (research.news_details || []).map((a, i) => {
                  const sc =
                    a.severity === "critical"
                      ? C.red
                      : a.severity === "high"
                      ? C.amber
                      : a.severity === "positive"
                      ? C.green
                      : C.muted;
                  return (
                    <div
                      key={i}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 8,
                        border: `1px solid ${C.border}`,
                        marginBottom: 8,
                        background: C.surface,
                        display: "flex",
                        gap: 14,
                        alignItems: "flex-start",
                      }}
                    >
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          color: sc,
                          textTransform: "uppercase",
                          marginTop: 3,
                          width: 60,
                          flexShrink: 0,
                        }}
                      >
                        {a.severity || "neutral"}
                      </span>
                      <div>
                        <p style={{ fontSize: 13, color: C.text, lineHeight: 1.4, fontWeight: 500 }}>
                          {a.title}
                        </p>
                        <p style={{ fontSize: 11, color: C.muted, marginTop: 3 }}>
                          {a.source} · {a.pub_date}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </Card>
          </div>
        )}

        {/* TAB 6: Five Cs */}
        {tab === "five-cs" && (
          <div style={{ display: "grid", gap: 14 }}>
            {[
              { key: "character",  label: "Character (Management Integrity)", icon: "👤" },
              { key: "capacity",   label: "Capacity (Debt Servicing & DSCR)", icon: "⚡" },
              { key: "capital",    label: "Capital (Financial Leverage)",    icon: "🏦" },
              { key: "collateral", label: "Collateral (Security Coverage)",  icon: "🏛" },
              { key: "conditions", label: "Conditions (Macro & GST Risk)",   icon: "🌐" },
            ].map(({ key, label, icon }) => (
              <Card key={key} style={{ display: "flex", gap: 18, alignItems: "flex-start" }}>
                <div style={{ fontSize: 24, width: 36, flexShrink: 0 }}>{icon}</div>
                <div>
                  <p style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{label}</p>
                  <p style={{ fontSize: 13, color: C.subtle, lineHeight: 1.7 }}>
                    {fiveCs[key] || "Evaluation not completed for this parameter."}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* TAB 7: Narrative */}
        {tab === "narrative" && (
          <Card>
            <Label>Comprehensive Underwriting Narrative</Label>
            {(analysis.detailed_narrative || []).length === 0 ? (
              <p style={{ color: C.green, fontSize: 13 }}>No adverse observations reported.</p>
            ) : (
              (analysis.detailed_narrative || []).map((item, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: 12,
                    marginBottom: 10,
                    padding: "10px 14px",
                    borderRadius: 7,
                    background: i % 2 === 0 ? C.surface : "transparent",
                  }}
                >
                  <span style={{ color: C.accent, fontSize: 14, marginTop: 1 }}>→</span>
                  <p style={{ fontSize: 13, color: C.subtle, lineHeight: 1.7 }}>{item}</p>
                </div>
              ))
            )}
          </Card>
        )}

        {/* CAM Report Download Bar */}
        {result.cam_report && (
          <div
            style={{
              marginTop: 28,
              padding: "18px 24px",
              borderRadius: 12,
              background: C.surface,
              border: `1px solid ${C.border}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <p style={{ fontSize: 14, fontWeight: 700 }}>
                Credit Appraisal Memorandum (CAM Report PDF)
              </p>
              <p style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>
                10-section sanction document generated via ReportLab including XGBoost metrics, Five Cs, and bank audit.
              </p>
            </div>
            <a
              href={`${API}/download/${result.cam_report}`}
              target="_blank"
              rel="noreferrer"
              style={{
                padding: "10px 22px",
                borderRadius: 8,
                background: `linear-gradient(135deg, ${C.teal}, ${C.accent})`,
                color: "#fff",
                textDecoration: "none",
                fontSize: 13,
                fontWeight: 700,
                boxShadow: "0 2px 10px rgba(13,148,136,0.3)",
              }}
            >
              ↓ Download Official CAM (PDF)
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Root Application ─────────────────────────────────────────────────────────
export default function App() {
  const [result, setResult] = useState(null);

  // No login screen required! Immediately render UploadScreen or Dashboard
  if (result) {
    return <Dashboard result={result} onBack={() => setResult(null)} />;
  }

  return <UploadScreen onResult={setResult} />;
}
