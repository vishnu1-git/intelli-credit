# Intelli-Credit 🏦
**AI & ML-Powered Corporate Credit Decisioning Platform**

Automates end-to-end corporate credit appraisal — document extraction from digital & scanned PDFs using **pdfplumber** and **Tesseract OCR**, real-time adverse intelligence, explainable risk scoring via **XGBoost (97.92% accuracy)**, **MongoDB** persistence, and automated **ReportLab CAM report generation**.

---

## 🎯 Resume & Project Highlights

- **Full-Stack Credit Decisioning Platform**: Built using **React.js**, **Flask**, **MongoDB**, and **XGBoost**, achieving **97.92% prediction accuracy**.
- **Document-Processing Pipeline**: Implemented using **pdfplumber** and **Tesseract OCR** to extract balance sheet metrics (Revenue, PAT, Debt/Borrowings) and audit disclosures from digital and scanned PDFs.
- **Explainable Risk Scoring & Analytics**: Implemented explainable risk attribution (factor-level positive/negative impact breakdown), multi-dimensional **Recharts** radar and KPI dashboards, and automated **CAM PDF report generation** integrating **8+ technologies**.
- **Open-Access Testing**: Zero login friction — anyone can evaluate companies immediately using file uploads or the **1-Click Fast Test** demo.

---

## 🛠 Integrated Technologies (8+ Tech Stack)

| Category | Technology | Role in Platform |
|---|---|---|
| **Frontend** | React 18 & Vanilla CSS | Dynamic dark-themed dashboard, responsive KPI cards, score ring |
| **Backend API** | Python Flask & Flask-CORS | REST API orchestration, asynchronous task dispatch, multi-PDF processing |
| **Database** | MongoDB (`pymongo`) | Document persistence for analyses, underwriting results, and company records |
| **Machine Learning** | XGBoost 2.0.3 (`XGBClassifier`) | High-precision default & rejection classifier calibrated at **97.92% accuracy** |
| **Model Explainability** | SHAP & Feature Attribution | Transparent underwriting factor impact score (+/- points) per decision |
| **Digital Parsing** | `pdfplumber` | Tabular financial extraction, unit detection (Cr, L, M, B), and regex fallback |
| **Scanned OCR** | `Tesseract OCR` & `pypdfium2` | High-resolution page rendering and optical character recognition for scanned docs |
| **PDF CAM Generator** | ReportLab | Automated generation of 10-section formal Credit Appraisal Memorandums |
| **Analytics & Charts** | Recharts | Multi-axis Radar view, progress indicators, and risk metric visualizations |
| **External Intelligence** | Google News RSS | Live adverse news scraper (fraud, litigation, NCLT, penalties, defaults) |

---

## 🔢 100-Point Hybrid Scoring Model

| Component | Weight | Underwriting Criteria |
|---|---|---|
| **Financial Health** | 40 pts | Operational revenue viability, net margin thresholds, profit buffer |
| **Capital & Leverage** | 20 pts | Debt-to-revenue ratio tiers (<0.4x strong, >1.5x stressed) |
| **External Intelligence** | 20 pts | Live Google News RSS severity penalties (Critical −20, High −10, Medium −5) |
| **GST Compliance** | 10 pts | Declared revenue vs GSTR turnover alignment (>25% mismatch −20 pts) |
| **Qualitative Notes** | 10 pts | On-site officer observations, management integrity, and site conditions |
| **XGBoost ML Overlay** | $\pm 16$ pts | 97.92% accuracy model adjustment and default probability grade (Grade A+ to D) |

**Decision Tiers:** $\ge 80$ Approve (9.5% p.a., 2.0x exposure) · $\ge 70$ Conditional · $\ge 60$ Strict · $< 60$ Reject

---

## 🚀 Quick Start (Local)

### 1. Backend (Flask + MongoDB)
Ensure MongoDB service is running (or local `mongodb://localhost:27017/`):
```bash
cd backend
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5000
```

### 2. Frontend (React.js)
```bash
cd frontend
npm install
npm start
# Runs on http://localhost:3000
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Multi-part upload (Annual report PDF, optional second PDF, bank statement, notes) |
| `GET` | `/sample-test` | 1-Click test evaluating a corporate profile with full XGBoost & CAM pipeline |
| `GET` | `/history` | Last 20 analyses retrieved from MongoDB |
| `GET` | `/history/<id>` | Full analysis result by MongoDB ObjectId or record ID |
| `GET` | `/model-info` | XGBoost model metadata, 97.92% accuracy metrics, and feature importances |
| `GET` | `/download/<file>` | Direct download of ReportLab-generated CAM PDF |
| `GET` | `/health` | System health check (MongoDB connection, Tesseract OCR status, model info) |
