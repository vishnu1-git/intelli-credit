# Intelli-Credit 🏦
**AI-Powered Corporate Credit Decisioning Engine**

Automates end-to-end corporate credit appraisal — PDF extraction, real-time news research, risk scoring, and professional CAM report generation. No API keys required.

---

## ✨ What it does

| Feature | Details |
|---|---|
| 📄 PDF Extraction | Two-pass extraction: table-first (pdfplumber), regex fallback |
| 🌐 Research Agent | Live Google News RSS — scans for fraud, litigation, NCLT, defaults |
| 📊 Risk Scoring | 100-point weighted model across 5 components |
| 📋 CAM Report | Professional PDF with Five Cs, score breakdown, dynamic narrative |
| 🗄 History | SQLite persistence — every analysis saved and reloadable |
| 🐳 Docker | One-command deploy with docker-compose |

---

## 🚀 Quick Start (Local)

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5000
```

### Frontend
```bash
cd frontend
npm install
npm start
# Runs on http://localhost:3000
```

---

## 🐳 Docker Deploy (One Command)

```bash
docker-compose up --build
```

- Frontend → http://localhost:3000  
- Backend API → http://localhost:5000

---

## 📁 Project Structure

```
Intelli-Credit/
├── backend/
│   ├── app.py                    # Flask API — routes, DB, orchestration
│   ├── requirements.txt
│   ├── Dockerfile
│   └── services/
│       ├── pdf_service.py        # Two-pass PDF extraction
│       ├── research_service.py   # Google News RSS research agent
│       ├── gst_service.py        # GST compliance analysis
│       ├── risk_service.py       # 100-pt scoring + Five Cs
│       └── cam_service.py        # ReportLab CAM PDF generator
├── frontend/
│   ├── src/
│   │   ├── App.js                # Full React dashboard
│   │   ├── App.css               # Dark theme + DM Sans font
│   │   └── index.js
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml
```

---

## 🔢 Scoring Model

| Component | Weight | How it's calculated |
|---|---|---|
| Financial Health | 40 pts | Revenue > 0, profit margin tiers |
| Leverage | 20 pts | Debt-to-revenue ratio (0–2x scale) |
| External Intelligence | 20 pts | News severity: Critical −20, High −10, Medium −5 |
| GST Compliance | 10 pts | Mismatch %: >25% −20, >15% −15, >10% −10, >5% −5 |
| Qualitative | 10 pts | Officer keyword scoring |

**Decision tiers:** ≥80 Approve · ≥70 Conditional · ≥60 Strict · <60 Reject

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyze` | Run full analysis (multipart: file, company_name, officer_notes) |
| GET | `/history` | Last 20 analyses |
| GET | `/history/<id>` | Full result for one analysis |
| GET | `/download/<filename>` | Download CAM PDF |
| GET | `/health` | Health check |

---

## 🗺 Roadmap

- [ ] Real GSTIN API integration
- [ ] Bank statement parser (OD limits, average balance)
- [ ] JWT authentication + multi-user
- [ ] Sector benchmarking
- [ ] Email CAM report delivery
- [ ] MCA / ROC data integration
