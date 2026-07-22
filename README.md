<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:06b6d4,50:3b82f6,100:6366f1&height=220&section=header&text=DocIntel%20Platform&fontSize=42&fontColor=ffffff&fontAlignY=40&desc=Enterprise%20AI%20Document%20Intelligence%20with%20Hybrid%20RAG,%20Citations%20%26%20OCR&descAlignY=65&descScale=18" width="100%" alt="DocIntel Banner" />
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Platform-DocIntel_v1.0-06b6d4?style=for-the-badge&logo=hyper&logoColor=white" alt="Platform Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/Tailwind_CSS-v3.4-38BDF8?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/FAISS-Dense_Search-00599C?style=for-the-badge&logo=cplusplus&logoColor=white" alt="FAISS Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/BM25-Sparse_Search-FF6F00?style=for-the-badge&logo=apache&logoColor=white" alt="BM25 Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/LLM-NVIDIA_NIM_%7C_Groq-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="NVIDIA NIM Badge"></a>
  <a href="#"><img src="https://img.shields.io/badge/Auth-Clerk_JWT-6C47FF?style=for-the-badge&logo=clerk&logoColor=white" alt="Clerk Auth Badge"></a>
</p>

---

## Executive Overview

**DocIntel** is a generic enterprise AI document intelligence platform designed to ingest, process, index, and query complex technical documentation, engineering specifications, tender contracts, spreadsheets, and scanned manuals.

The system combines **Hybrid Retrieval (FAISS Dense Vector + BM25 Sparse Keyword Search)** with **Cross-Encoder Re-Ranking**, **Adaptive Hierarchical Chunking**, **NVIDIA NIM LLM generation with Groq fallback**, **Strict Faithfulness Groundedness Verification**, and **Interactive PDF Citation Bounding Box Highlight Rendering**.

---

## System Architecture

The high-level architecture separates the modern React/Vite frontend from the FastAPI backend and AI pipelines:

<p align="center">
  <img src="./Architecture%20Diagram.png" alt="DocIntel High-Level Architecture Diagram" width="100%" />
</p>

```
                       ┌────────────────────────┐
                       │     Next.js / Vite     │
                       │ Clerk + Tailwind + UI  │
                       └────────────┬───────────┘
                                    │
                               HTTPS / API
                                    │
                       ┌────────────▼────────────┐
                       │      FastAPI Backend    │
                       │ Authentication, APIs,   │
                       │ Chat, Document Service  │
                       └──────┬─────────┬────────┘
                              │         │
                   Document Pipeline   Chat Pipeline
```

---

## Core Engineering Features

### 1. Multi-Format Document Parsing Engine
Instead of restricting ingestion to PDFs, DocIntel provides dedicated parsers for all standard enterprise file types:

- **PDF Parser (`PyMuPDF` + `PyTesseract OCR`)**: Extracts native text and structured layout blocks. Automatically switches to Tesseract OCR when scanning physical or image-based pages.
- **Word Parser (`python-docx`)**: Preserves document headings, sections, styled paragraphs, and embedded tables.
- **Excel Parser (`openpyxl` + `pandas`)**: Reads multi-sheet workbooks and formats tabular data into clean Markdown tables.
- **CSV Parser (`pandas`)**: Parses delimiter-separated datasets while maintaining schema structure.
- **Image Parser (`Tesseract OCR`)**: OCR text extraction with character bounding boxes (`x0`, `y0`, `x1`, `y1`).
- **Plain Text Parser**: Handles markdown, logs, and plain configuration files.

### 2. Adaptive Hierarchical Chunking
Unlike fixed character sliding windows, DocIntel uses a dynamic structural hierarchy:
```
Heading -> Section -> Paragraph -> Sentence
```
- **Table Preservation**: Tables remain intact as single atomic chunks to prevent loss of relational row/column context.
- **Metadata Tagging**: Every chunk retains document ID, filename, page number, heading, section name, paragraph ID, and bounding box coordinates.

### 3. Hybrid RAG & Re-Ranking Pipeline
```
User Query -> Guardrails -> Query Rewrite -> FAISS + BM25 Retrieval -> Cross Encoder Rerank -> Context Compression -> LLM Generation -> Faithfulness Check -> Citation Output
```
- **Dense Retrieval**: `BAAI/bge-small-en-v1.5` embeddings stored in a FAISS index.
- **Sparse Retrieval**: `BM25Okapi` keyword indexing for exact serial numbers, code identifiers, and technical terminology.
- **Rank Fusion**: Reciprocal Rank Fusion (RRF) merges dense and sparse result sets.
- **Cross-Encoder Re-Ranking**: Evaluates the top 30 retrieved candidates down to the top 5 most relevant context snippets.
- **Context Compression**: Compresses retrieved passages into minimal context tokens before LLM prompting.

### 4. Dual LLM Provider Fallback Engine
- **Primary LLM**: NVIDIA NIM API (`meta/llama3-70b-instruct`).
- **Fallback LLM**: Groq API (`llama3-70b-8192`).
- **Offline Resilient Mode**: If external API keys are omitted or unreachable, local synthesis rules extract verified answers directly from document context snippets.

### 5. Strict Faithfulness Audit Verification
Every generated answer undergoes an automated audit prompt asking: *"Is every claim in the proposed answer strictly backed up by the retrieved context?"*
- Returns `FAITHFUL` badge if supported.
- Returns `INSUFFICIENT_EVIDENCE` flag if claims exceed context boundaries.

### 6. Interactive Citation PDF Highlight Viewer
Clicking any citation badge (`Transformer_Manual.pdf | Page 21 | Warranty`) instantly:
- Opens the PDF document viewer canvas.
- Navigates directly to the cited page.
- Highlights the exact source paragraph using an animated glowing bounding box overlay (`bbox`).

### 7. Role-Based Access Control (RBAC)
FastAPI security dependencies enforce Clerk JWT token validation and role permissions:
- **Admin**: Full access including document deletion and system analytics.
- **Tender Specialist**: Document upload, hybrid chat, and bookmarking.
- **Sales**: Document upload, chat, and bookmarking.
- **Engineer**: Document upload, chat, and bookmarking.
- **Viewer**: Read-only access to chat and document previewer (uploading and deletion restricted).

### 8. Enterprise Admin Analytics Dashboard
Telemetry dashboard tracks key metrics:
- Most searched documents.
- Most frequent user queries.
- Total uploaded files and processed queries.
- Unanswered questions log for identifying documentation coverage gaps.

---

## Directory Structure

```
DocIntel/
├── Architecture Diagram.png
├── README.md
├── .env.example
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── documents_router.py
│   │   ├── chat_router.py
│   │   ├── bookmarks_router.py
│   │   └── analytics_router.py
│   ├── auth/
│   │   └── clerk_auth.py
│   ├── database/
│   │   ├── models.py
│   │   └── session.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── excel_parser.py
│   │   ├── csv_parser.py
│   │   ├── image_parser.py
│   │   └── txt_parser.py
│   └── pipeline/
│       ├── ingestion.py
│       ├── adaptive_chunking.py
│       ├── retrieval.py
│       ├── generation.py
│       └── faithfulness.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── index.css
    │   └── components/
    │       ├── DocumentViewer.tsx
    │       ├── UploadDropzone.tsx
    │       ├── AdminAnalytics.tsx
    │       └── BookmarksView.tsx
    └── public/
```

---

## Setup & Installation Guide

### Prerequisites
- Python 3.11 or higher
- Node.js 18.0 or higher
- Tesseract OCR engine (optional, for scanned PDF/Image OCR)

### 1. Clone & Environment Configuration
```bash
git clone https://github.com/YourOrg/DocIntel.git
cd DocIntel
cp .env.example .env
```

Edit `.env` or set environment variables:
```env
NVIDIA_API_KEY=nvapi-your-nvidia-nim-key
GROQ_API_KEY=gsk_your-groq-key
CLERK_SECRET_KEY=sk_test_your-clerk-secret
DATABASE_URL=sqlite:///./docintel.db
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Backend API server will run at `http://localhost:8000`.

### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```
Frontend Web application will run at `http://localhost:5173`.

---

## API Endpoints Reference

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/documents/upload` | Upload & parse document (PDF, DOCX, XLSX, CSV, TXT, Image) | Admin, Specialist, Sales, Engineer |
| `GET` | `/api/documents/` | List all ingested documents and metrics | All Roles |
| `GET` | `/api/documents/{id}/chunks` | Inspect adaptive chunks of a document | All Roles |
| `DELETE` | `/api/documents/{id}` | Delete document and remove vector indices | Admin |
| `POST` | `/api/chat/query` | Run hybrid RAG query pipeline with citations | All Roles |
| `GET` | `/api/chat/sessions` | List user chat session history | All Roles |
| `GET` | `/api/chat/sessions/{id}` | Retrieve messages and citations for session | All Roles |
| `POST` | `/api/bookmarks/` | Save answer & citation bookmark | All Roles |
| `GET` | `/api/bookmarks/` | Search saved bookmarks library | All Roles |
| `DELETE` | `/api/bookmarks/{id}` | Remove saved bookmark | All Roles |
| `GET` | `/api/analytics/dashboard` | Admin telemetry, top documents, unanswered queries | Admin, Specialist, Sales |

---

## License

Distributed under the MIT License. Enterprise deployment rights apply.
