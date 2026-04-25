import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Cell
} from "recharts";

const API = "https://intelli-credit-5x1a.onrender.com";

/* ─── Design tokens ─────────────────────────────────────────────────────── */
const C = {
  bg:       "#0a0f1e",
  surface:  "#0f1729",
  card:     "#161f35",
  border:   "#1e2d4a",
  accent:   "#0ea5e9",
  teal:     "#0d9488",
  green:    "#10b981",
  amber:    "#f59e0b",
  red:      "#ef4444",
  text:     "#e2e8f0",
  muted:    "#64748b",
  subtle:   "#94a3b8",
};

const decisionColor = (d = "") => {
  if (!d || d === "N/A") return C.muted;
  if (d.includes("Reject")) return C.red;
  if (d.includes("Strict")) return C.amber;
  if (d.includes("Condition")) return C.amber;
  return C.green;
};

const scoreColor = (s) => s >= 80 ? C.green : s >= 60 ? C.amber : C.red;

/* ─── Reusable components ───────────────────────────────────────────────── */
function Card({ children, style = {} }) {
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`,
      borderRadius: 12, padding: "20px 24px", ...style
    }}>
      {children}
    </div>
  );
}

function Label({ children }) {
  return (
    <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em",
      textTransform: "uppercase", color: C.muted, marginBottom: 6 }}>
      {children}
    </p>
  );
}

function Tag({ children, color = C.muted }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 99,
      fontSize: 11, fontWeight: 600, background: color + "22",
      color, border: `1px solid ${color}44`, marginRight: 6, marginBottom: 4
    }}>
      {children}
    </span>
  );
}

function Spinner() {
  return (
    <div style={{ display: "flex", flexDirection: "column",
      alignItems: "center", gap: 20, padding: "60px 0" }}>
      <div style={{
        width: 48, height: 48, border: `3px solid ${C.border}`,
        borderTop: `3px solid ${C.accent}`, borderRadius: "50%",
        animation: "spin 0.8s linear infinite"
      }} />
      <p style={{ color: C.muted, fontSize: 14 }}>Analyzing financial documents…</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ScoreRing({ score }) {
  const r = 54, cx = 64, cy = 64;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(score, 0), 100);
  const dash = (pct / 100) * circ;
  const color = scoreColor(pct);
  return (
    <svg width={128} height={128} viewBox="0 0 128 128">
      <circle cx={cx} cy={cy} r={r} fill="none"
        stroke={C.border} strokeWidth={8} />
      <circle cx={cx} cy={cy} r={r} fill="none"
        stroke={color} strokeWidth={8} strokeLinecap="round"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeDashoffset={circ / 4}
        style={{ transition: "stroke-dasharray 1s ease" }} />
      <text x={cx} y={cy - 6} textAnchor="middle" fill={color}
        fontSize={26} fontWeight={700} fontFamily="monospace">{score}</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill={C.muted}
        fontSize={11} fontFamily="sans-serif">/ 100</text>
    </svg>
  );
}

function ProgressBar({ value, max, color }) {
  const pct = (value / max) * 100;
  return (
    <div style={{ background: C.border, borderRadius: 99, height: 6,
      overflow: "hidden", flex: 1 }}>
      <div style={{
        width: `${pct}%`, height: "100%", borderRadius: 99,
        background: color, transition: "width 0.8s ease"
      }} />
    </div>
  );
}

/* ─── Upload Screen ─────────────────────────────────────────────────────── */
function UploadScreen({ onResult }) {
  const [company, setCompany] = useState("");
  const [file, setFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    axios.get(`${API}/history`).then(r => setHistory(r.data)).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    setError("");
    if (!company.trim()) { setError("Please enter the company name."); return; }
    if (!file) { setError("Please upload a PDF document."); return; }
    if (!file.name.endsWith(".pdf")) { setError("Only PDF files are accepted."); return; }

    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("company_name", company);
    fd.append("officer_notes", notes);

    try {
      const res = await axios.post(`${API}/analyze`, fd,
        { headers: { "Content-Type": "multipart/form-data" } });
      onResult(res.data);
    } catch (err) {
      setError(err.response?.data?.error || "Analysis failed. Check that the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (id) => {
    try {
      const res = await axios.get(`${API}/history/${id}`);
      onResult(res.data);
    } catch {}
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text,
      fontFamily: "'DM Sans', 'Segoe UI', sans-serif", display: "flex" }}>

      {/* Left sidebar */}
      <div style={{ width: 260, background: C.surface,
        borderRight: `1px solid ${C.border}`, padding: "32px 24px",
        display: "flex", flexDirection: "column", gap: 32 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8,
              background: `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 800, color: "#fff" }}>
              IC
            </div>
            <span style={{ fontSize: 16, fontWeight: 700 }}>Intelli-Credit</span>
          </div>
          <p style={{ fontSize: 11, color: C.muted }}>AI Credit Decisioning Engine</p>
        </div>

        <div>
          <p style={{ fontSize: 11, fontWeight: 600, color: C.muted,
            textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>
            Recent Analyses
          </p>
          {history.length === 0
            ? <p style={{ fontSize: 12, color: C.muted }}>No analyses yet</p>
            : history.slice(0, 8).map(h => (
              <div key={h.id} onClick={() => loadHistory(h.id)}
                style={{ padding: "10px 12px", borderRadius: 8, cursor: "pointer",
                  marginBottom: 4, border: `1px solid ${C.border}`,
                  background: C.card, transition: "background 0.15s" }}
                onMouseEnter={e => e.currentTarget.style.background = C.border}
                onMouseLeave={e => e.currentTarget.style.background = C.card}>
                <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>{h.company_name}</p>
                <p style={{ fontSize: 10, color: C.muted }}>
                  Score: <span style={{ color: scoreColor(h.risk_score) }}>{h.risk_score}</span>
                  &nbsp;·&nbsp;{h.decision}
                </p>
              </div>
            ))
          }
        </div>
      </div>

      {/* Main upload form */}
      <div style={{ flex: 1, display: "flex", alignItems: "center",
        justifyContent: "center", padding: 40 }}>
        <div style={{ width: "100%", maxWidth: 560 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
            New Credit Analysis
          </h1>
          <p style={{ color: C.muted, marginBottom: 32, fontSize: 14 }}>
            Upload a PDF annual report or financial statement to get an instant credit decision.
          </p>

          <Card>
            {/* Company name */}
            <div style={{ marginBottom: 20 }}>
              <Label>Company Name *</Label>
              <input
                value={company}
                onChange={e => setCompany(e.target.value)}
                placeholder="e.g. Infosys Ltd, TCS, Reliance Industries"
                style={{
                  width: "100%", padding: "12px 14px", borderRadius: 8,
                  border: `1px solid ${C.border}`, background: C.surface,
                  color: C.text, fontSize: 14, outline: "none",
                  boxSizing: "border-box"
                }}
              />
            </div>

            {/* File upload */}
            <div style={{ marginBottom: 20 }}>
              <Label>Financial Document (PDF) *</Label>
              <label style={{
                display: "flex", flexDirection: "column", alignItems: "center",
                padding: "28px 20px", borderRadius: 8, border: `2px dashed ${file ? C.teal : C.border}`,
                cursor: "pointer", background: file ? C.teal + "10" : "transparent",
                transition: "all 0.2s"
              }}>
                <input type="file" accept=".pdf" style={{ display: "none" }}
                  onChange={e => setFile(e.target.files[0])} />
                <div style={{ fontSize: 28, marginBottom: 8 }}>📄</div>
                <p style={{ fontSize: 13, color: file ? C.teal : C.muted, fontWeight: 500 }}>
                  {file ? file.name : "Click to upload PDF"}
                </p>
                <p style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
                  Annual reports, financial statements · Max 20 MB
                </p>
              </label>
            </div>

            {/* Officer notes */}
            <div style={{ marginBottom: 24 }}>
              <Label>Credit Officer Notes (optional)</Label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="e.g. management met on-site, strong repayment history, active litigation in Bombay HC..."
                rows={3}
                style={{
                  width: "100%", padding: "12px 14px", borderRadius: 8,
                  border: `1px solid ${C.border}`, background: C.surface,
                  color: C.text, fontSize: 14, resize: "vertical",
                  outline: "none", boxSizing: "border-box", fontFamily: "inherit"
                }}
              />
            </div>

            {error && (
              <div style={{ padding: "10px 14px", borderRadius: 8,
                background: C.red + "15", border: `1px solid ${C.red}44`,
                color: C.red, fontSize: 13, marginBottom: 16 }}>
                ⚠ {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              style={{
                width: "100%", padding: "14px", borderRadius: 8,
                background: loading ? C.muted : `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
                color: "#fff", fontSize: 15, fontWeight: 700, border: "none",
                cursor: loading ? "not-allowed" : "pointer", letterSpacing: "0.02em"
              }}>
              {loading ? "Analyzing…" : "▶  Run Credit Analysis"}
            </button>
          </Card>

          {loading && <Spinner />}
        </div>
      </div>
    </div>
  );
}

/* ─── Dashboard Screen ──────────────────────────────────────────────────── */
function Dashboard({ result, onBack }) {
  const [tab, setTab] = useState("overview");

  const { company, financials = {}, research = {}, analysis = {} } = result;
  const breakdown = analysis.score_breakdown || {};
  const fiveCs    = analysis.five_cs || {};
  const gst       = analysis.gst_analysis || {};
  const score     = analysis.risk_score || 0;
  const dColor    = decisionColor(analysis.decision);

  const breakdownData = [
    { name: "Financial", value: breakdown.financial_score || 0, max: 40 },
    { name: "Leverage",  value: breakdown.leverage_score  || 0, max: 20 },
    { name: "External",  value: breakdown.external_score  || 0, max: 20 },
    { name: "GST",       value: breakdown.gst_score       || 0, max: 10 },
    { name: "Officer",   value: breakdown.qualitative_score || 0, max: 10 },
  ];

  const radarData = breakdownData.map(d => ({
    subject: d.name,
    score: Math.round((d.value / d.max) * 100),
  }));

  const TABS = ["overview", "research", "five-cs", "narrative"];

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text,
      fontFamily: "'DM Sans', 'Segoe UI', sans-serif" }}>

      {/* Top nav */}
      <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`,
        padding: "0 32px", display: "flex", alignItems: "center",
        justifyContent: "space-between", height: 60 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8,
            background: `linear-gradient(135deg, ${C.accent}, ${C.teal})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, fontWeight: 800, color: "#fff" }}>IC</div>
          <span style={{ fontSize: 14, fontWeight: 600 }}>Intelli-Credit</span>
          <span style={{ color: C.border }}>›</span>
          <span style={{ fontSize: 14, color: C.muted }}>{company}</span>
        </div>
        <button onClick={onBack} style={{
          padding: "7px 16px", borderRadius: 7,
          border: `1px solid ${C.border}`, background: "transparent",
          color: C.subtle, cursor: "pointer", fontSize: 13
        }}>
          + New Analysis
        </button>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>

        {/* Hero row */}
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 24,
          alignItems: "center", marginBottom: 28 }}>
          <ScoreRing score={score} />
          <div>
            <h2 style={{ fontSize: 26, fontWeight: 700, marginBottom: 4 }}>{company}</h2>
            <p style={{ color: C.muted, fontSize: 14, marginBottom: 12 }}>
              {research.articles_analyzed || 0} articles analyzed ·
              Sentiment: <span style={{ color: score >= 70 ? C.green : score >= 55 ? C.amber : C.red }}>
                {research.overall_sentiment || "Neutral"}
              </span>
            </p>
            <div>
              <Tag color={dColor}>{analysis.decision}</Tag>
              <Tag color={C.accent}>{analysis.interest_rate}</Tag>
              {analysis.risk_flags?.slice(0, 2).map((f, i) => (
                <Tag key={i} color={C.red}>{f.slice(0, 45)}{f.length > 45 ? "…" : ""}</Tag>
              ))}
            </div>
          </div>
          <Card style={{ textAlign: "center", minWidth: 180 }}>
            <Label>Indicative Loan</Label>
            <p style={{ fontSize: 18, fontWeight: 700, color: dColor, lineHeight: 1.3 }}>
              {analysis.loan_amount || "N/A"}
            </p>
          </Card>
        </div>

        {/* Metric cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
          {[
            { label: "Revenue",       val: financials.revenue_display || "N/A", color: C.text },
            { label: "Net Profit/PAT", val: financials.profit_display  || "N/A",
              color: parseFloat(financials.profit) > 0 ? C.green : C.red },
            { label: "Total Debt",    val: financials.debt_display    || "N/A", color: C.amber },
            { label: "GST Status",    val: gst.gst_risk_level         || "N/A",
              color: (gst.gst_penalty || 0) === 0 ? C.green : C.amber },
          ].map(({ label, val, color }) => (
            <Card key={label}>
              <Label>{label}</Label>
              <p style={{ fontSize: 16, fontWeight: 700, color }}>{val}</p>
            </Card>
          ))}
        </div>

        {/* Score breakdown */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
          <Card>
            <Label>Score breakdown</Label>
            {breakdownData.map(({ name, value, max }) => {
              const color = value / max >= 0.75 ? C.green : value / max >= 0.5 ? C.amber : C.red;
              return (
                <div key={name} style={{ display: "flex", alignItems: "center",
                  gap: 12, marginBottom: 12 }}>
                  <span style={{ fontSize: 12, color: C.subtle, width: 68 }}>{name}</span>
                  <ProgressBar value={value} max={max} color={color} />
                  <span style={{ fontSize: 12, fontWeight: 600, color, width: 30,
                    textAlign: "right" }}>{value}</span>
                </div>
              );
            })}
          </Card>
          <Card style={{ display: "flex", flexDirection: "column" }}>
            <Label>Radar view</Label>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid stroke={C.border} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: C.muted, fontSize: 11 }} />
                <Radar dataKey="score" stroke={C.accent} fill={C.accent} fillOpacity={0.25}
                  strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 20,
          borderBottom: `1px solid ${C.border}`, paddingBottom: 0 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "10px 18px", fontSize: 13, fontWeight: 500,
              background: "transparent", border: "none", cursor: "pointer",
              color: tab === t ? C.accent : C.muted,
              borderBottom: tab === t ? `2px solid ${C.accent}` : "2px solid transparent",
              textTransform: "capitalize", letterSpacing: "0.02em",
              fontFamily: "inherit"
            }}>
              {t.replace("-", " ")}
            </button>
          ))}
        </div>

        {/* Tab: Overview */}
        {tab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <Card>
              <Label>Explainable Decision</Label>
              <p style={{ fontSize: 13, color: C.subtle, lineHeight: 1.7 }}>
                {analysis.explanation}
              </p>
            </Card>
            <Card>
              <Label>Risk Flags ({analysis.risk_flags?.length || 0})</Label>
              {(analysis.risk_flags || []).length === 0
                ? <p style={{ color: C.green, fontSize: 13 }}>✓ No significant risk flags</p>
                : (analysis.risk_flags || []).map((f, i) => (
                  <div key={i} style={{ padding: "7px 10px", borderRadius: 6,
                    background: C.red + "12", border: `1px solid ${C.red}22`,
                    marginBottom: 6, fontSize: 12, color: C.red }}>
                    ⚠ {f}
                  </div>
                ))
              }
            </Card>
          </div>
        )}

        {/* Tab: Research */}
        {tab === "research" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 20 }}>
              {[
                { label: "Critical Alerts", val: research.severity_counts?.critical || 0, color: C.red },
                { label: "High Risk Signals", val: research.severity_counts?.high || 0, color: C.amber },
                { label: "Positive News", val: (research.positive_signals || []).length, color: C.green },
              ].map(({ label, val, color }) => (
                <Card key={label} style={{ textAlign: "center" }}>
                  <Label>{label}</Label>
                  <p style={{ fontSize: 28, fontWeight: 700, color }}>{val}</p>
                </Card>
              ))}
            </div>
            <Card>
              <Label>News articles scanned</Label>
              {(research.news_details || []).length === 0
                ? <p style={{ color: C.muted, fontSize: 13 }}>No articles found</p>
                : (research.news_details || []).map((a, i) => {
                  const sColor = a.severity === "critical" ? C.red
                    : a.severity === "high" ? C.amber
                    : a.severity === "medium" ? "#f97316"
                    : a.severity === "positive" ? C.green : C.muted;
                  return (
                    <div key={i} style={{ padding: "10px 12px", borderRadius: 8,
                      border: `1px solid ${C.border}`, marginBottom: 8,
                      display: "flex", gap: 12, alignItems: "flex-start" }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: sColor,
                        textTransform: "uppercase", marginTop: 2, width: 52,
                        flexShrink: 0 }}>
                        {a.severity || "neutral"}
                      </span>
                      <div>
                        <p style={{ fontSize: 13, color: C.text, lineHeight: 1.4 }}>{a.title}</p>
                        <p style={{ fontSize: 11, color: C.muted, marginTop: 3 }}>
                          {a.source} · {a.pub_date}
                        </p>
                      </div>
                    </div>
                  );
                })
              }
            </Card>
          </div>
        )}

        {/* Tab: Five Cs */}
        {tab === "five-cs" && (
          <div style={{ display: "grid", gap: 14 }}>
            {[
              { key: "character",  label: "Character",  icon: "👤" },
              { key: "capacity",   label: "Capacity",   icon: "⚡" },
              { key: "capital",    label: "Capital",    icon: "🏦" },
              { key: "collateral", label: "Collateral", icon: "🏛" },
              { key: "conditions", label: "Conditions", icon: "🌐" },
            ].map(({ key, label, icon }) => (
              <Card key={key} style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
                <div style={{ fontSize: 24, width: 40, flexShrink: 0 }}>{icon}</div>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>{label}</p>
                  <p style={{ fontSize: 13, color: C.subtle, lineHeight: 1.7 }}>
                    {fiveCs[key] || "Not assessed"}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Tab: Narrative */}
        {tab === "narrative" && (
          <Card>
            <Label>Detailed risk narrative</Label>
            {(analysis.detailed_narrative || []).length === 0
              ? <p style={{ color: C.green, fontSize: 13 }}>No risk observations.</p>
              : (analysis.detailed_narrative || []).map((item, i) => (
                <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12,
                  padding: "10px 14px", borderRadius: 8,
                  background: i % 2 === 0 ? C.surface : "transparent" }}>
                  <span style={{ color: C.accent, fontSize: 16, marginTop: 1 }}>→</span>
                  <p style={{ fontSize: 13, color: C.subtle, lineHeight: 1.7 }}>{item}</p>
                </div>
              ))
            }
          </Card>
        )}

        {/* Download CAM */}
        {result.cam_report && (
          <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
            <a href={`${API}/download/${result.cam_report}`} target="_blank" rel="noreferrer"
              style={{
                padding: "12px 28px", borderRadius: 8,
                background: `linear-gradient(135deg, ${C.teal}, ${C.accent})`,
                color: "#fff", textDecoration: "none", fontSize: 14, fontWeight: 700
              }}>
              ↓ Download CAM Report PDF
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── App root ──────────────────────────────────────────────────────────── */
export default function App() {
  const [result, setResult] = useState(null);
  return result
    ? <Dashboard result={result} onBack={() => setResult(null)} />
    : <UploadScreen onResult={setResult} />;
}