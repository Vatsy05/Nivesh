# Nivesh: Indian Mutual Fund Portfolio Tracker

Nivesh is a comprehensive portfolio management application designed to help Indian retail investors track their mutual fund investments by automating the extraction and analysis of Consolidated Account Statements (CAS) from CAMS/KFintech.

## 🚀 Key Features

- **Automated CAS Parsing**: Intelligent extraction of transaction data from CAMS/KFintech PDF statements using `pdfplumber` and custom regex-based parsing logic.
- **Smart Fund Matching**: Automatically matches fund names from statements to official AMFI scheme codes using the `mfapi.in` REST API.
- **Real-time NAV Tracking**: Fetches and caches the latest Net Asset Values (NAV) for accurate portfolio valuation.
- **Secure Data Storage**: Implements **AES-256-CBC encryption** for sensitive transaction data at rest.
- **Interactive Dashboard**:
    - **Portfolio Overview**: Visual summary of total investments, current value, and returns.
    - **SIP Heatmap**: A visual calendar representation of investment frequency and volume.
    - **Transaction History**: Detailed tabular view of all historical trades.
- **Built-in Authentication**: Secure user login and registration powered by **NextAuth.js** and **Supabase**.

---

## 🏗️ System Architecture & Data Flow

### **Next.js & FastAPI Proxy Pattern**
To maintain a unified authentication layer and simplify deployment, the project utilizes a **Next.js API Route Proxy**.
- All frontend calls hit `/api/python/[...path]`.
- The Next.js route (`frontend/src/app/api/python/[...path]/route.ts`) proxies these requests to the internal FastAPI server.
- This allows **NextAuth.js** to handle user sessions which are seamlessly passed to the backend parser and matching services.

---

## 📊 Knowledge Graph & Analysis (`graphify-out/`)

The repository includes a **Graphify** output which provides a structural map of the codebase.
- **`GRAPH_REPORT.md`**: Detailed community detection report.
- **`graph.html`**: Interactive visualization of file relationships and code flow.
- **Key Insights from Graph**:
    - `CamCasParser` and `Portfolio` are identified as "God Nodes" (central orchestrators).
    - Detected 41 distinct code communities (e.g., PDF Parser Logic, Encryption Services, Dashboard Components).
    - Clear separation between UI components and PDF processing pipelines.

---

## 📂 Detailed Project Structure

```text
Nivesh/
├── backend/                # FASTAPI CORE
│   ├── app/                # Main application logic
│   │   ├── routers/        # API endpoints (upload, portfolio)
│   │   ├── models.py       # SQLAlchemy ORM (User, Transaction, NavCache)
│   │   └── schemas.py      # Pydantic models for validation
│   ├── parser/             # PDF STRATEGIES
│   │   └── cam_cas_parser.py # Regex-based extraction logic for CAMS/KFintech
│   ├── matcher/            # FUND RECOGNITION
│   │   └── fund_matcher.py  # AMFI Scheme code lookup (mfapi.in)
│   └── services/           # UTILITIES
│       └── encryption.py   # AES-256 data security
├── frontend/               # NEXT.JS UI
│   ├── src/app/            # App Router pages & API handlers
│   ├── src/components/     # UI Kit (SIPHeatmap, TransactionTable, etc.)
│   └── src/lib/            # Client wrappers (Supabase, NextAuth)
├── graphify-out/           # CODEBASE ANALYSIS
│   ├── GRAPH_REPORT.md     # Structural overview
│   └── graph.html          # Interactive graph viz
└── supabase/               # DATABASE SCHEMA
```

---

## ⚙️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, FastAPI, SQLAlchemy, Pydantic, PDFPlumber |
| **Frontend** | React, Next.js 14, TypeScript, Tailwind CSS, Lucide |
| **Database** | PostgreSQL (Supabase) |
| **Analytics** | Graphify (Graph Analysis) |
| **Security** | AES-256-CBC, NextAuth.js |
| **Data APIs** | MFAPI.in (NAV Data) |

---

## 🛠️ Work Completed (To Date)

- [x] **Core Backend**: Built a FastAPI server with SQLAlchemy models for user ownership and transaction history.
- [x] **PDF Intelligence**: Developed a sophisticated parser in `cam_cas_parser.py` that handles CAMS/KFintech quirks.
- [x] **Fund Matching**: Implemented fuzzy search and exact matching for Indian Mutual Funds.
- [x] **Security**: Integrated encryption for sensitive portfolio data at rest.
- [x] **Frontend Dashboard**: Created a comprehensive UI with:
    - `SIPHeatmap`: Visualizing investment patterns.
    - `TransactionTable`: Sortable and filterable investment records.
    - `UploadZone`: Drag-and-drop PDF ingestion.
- [x] **Auth System**: Full integration with NextAuth and Supabase PostgreSQL.
- [x] **Analysis**: Generated a full codebase knowledge graph using Graphify.

---

## 🚦 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase Account

### Setting up Backend
1. `cd backend`
2. `pip install -r requirements.txt`
3. Create `.env` from `.env.example` and set `DATABASE_URL` and `ENCRYPTION_KEY`.

### Setting up Frontend
1. `cd frontend`
2. `npm install`
3. Set `.env.local` with Supabase and NextAuth secrets.

### Concurrent Startup
Run both the FastAPI server (usually port 8000) and Next.js (port 3000). The proxy will bridge them.
