# Intelli-Credit

A modular credit risk analysis system that processes financial PDFs, evaluates risk using a weighted scoring engine, and generates structured CAM (Credit Appraisal Memo) reports.

## Current Status
Project under development (40–45% complete)

## Features Implemented
- PDF extraction and data processing
- GST and financial data handling
- Research-based data enrichment module
- Weighted risk scoring engine with breakdown
- Automated CAM report generation (PDF)
- Decision service for credit evaluation
- File upload and report download functionality

## Architecture
The backend follows a modular services-based architecture:

- pdf_service → Handles PDF extraction
- gst_service → Processes GST-related data
- research_service → Adds contextual insights
- risk_service → Calculates credit risk score
- decision_service → Final credit decision logic
- cam_service → Generates CAM reports

## Tech Stack
- Backend: Python (Flask)
- Database: SQLite
- PDF Processing: Python-based libraries
- Architecture: Service-oriented modular backend

