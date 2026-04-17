# Graph Report - .  (2026-04-17)

## Corpus Check
- Corpus is ~9,860 words - fits in a single context window. You may not need a graph.

## Summary
- 164 nodes · 239 edges · 41 communities detected
- Extraction: 67% EXTRACTED · 33% INFERRED · 0% AMBIGUOUS · INFERRED: 80 edges (avg confidence: 0.59)
- Token cost: 100 input · 50 output

## Community Hubs (Navigation)
- [[_COMMUNITY_CAMCAS PDF Parser Logic|CAM/CAS PDF Parser Logic]]
- [[_COMMUNITY_Data Models and Pydantic Schemas|Data Models and Pydantic Schemas]]
- [[_COMMUNITY_Portfolio Router & Fund Matcher|Portfolio Router & Fund Matcher]]
- [[_COMMUNITY_Upload Router & User DB|Upload Router & User DB]]
- [[_COMMUNITY_Encryption Services|Encryption Services]]
- [[_COMMUNITY_API Routes & Supabase Proxy|API Routes & Supabase Proxy]]
- [[_COMMUNITY_Database Initialization|Database Initialization]]
- [[_COMMUNITY_App Config & Settings|App Config & Settings]]
- [[_COMMUNITY_Authentication UI Pages|Authentication UI Pages]]
- [[_COMMUNITY_Backend FastAPI Main|Backend FastAPI Main]]
- [[_COMMUNITY_Frontend Root Layout|Frontend Root Layout]]
- [[_COMMUNITY_Frontend LandingHome Page|Frontend Landing/Home Page]]
- [[_COMMUNITY_Dashboard Layout Wrapper|Dashboard Layout Wrapper]]
- [[_COMMUNITY_Dashboard Overview Page|Dashboard Overview Page]]
- [[_COMMUNITY_Dashboard Portfolio View|Dashboard Portfolio View]]
- [[_COMMUNITY_Dashboard File Upload View|Dashboard File Upload View]]
- [[_COMMUNITY_Confirm Dialog Component|Confirm Dialog Component]]
- [[_COMMUNITY_Navigation Component|Navigation Component]]
- [[_COMMUNITY_Transaction Data Table|Transaction Data Table]]
- [[_COMMUNITY_SIP Heatmap Chart|SIP Heatmap Chart]]
- [[_COMMUNITY_Frontend Providers|Frontend Providers]]
- [[_COMMUNITY_Supabase Client Utils|Supabase Client Utils]]
- [[_COMMUNITY_Frontend README Concepts|Frontend README Concepts]]
- [[_COMMUNITY_PostCSS Configuration|PostCSS Configuration]]
- [[_COMMUNITY_Next.js Configuration|Next.js Configuration]]
- [[_COMMUNITY_Next.js Environment Definitions|Next.js Environment Definitions]]
- [[_COMMUNITY_Tailwind CSS Config|Tailwind CSS Config]]
- [[_COMMUNITY_Next.js Middleware|Next.js Middleware]]
- [[_COMMUNITY_NextAuth API Route|NextAuth API Route]]
- [[_COMMUNITY_Upload Zone UI Component|Upload Zone UI Component]]
- [[_COMMUNITY_Parser Summary UI Component|Parser Summary UI Component]]
- [[_COMMUNITY_Auth Client Library|Auth Client Library]]
- [[_COMMUNITY_Backend App Init|Backend App Init]]
- [[_COMMUNITY_Backend Routers Init|Backend Routers Init]]
- [[_COMMUNITY_Backend Parser Init|Backend Parser Init]]
- [[_COMMUNITY_Backend Matcher Init|Backend Matcher Init]]
- [[_COMMUNITY_Backend Services Init|Backend Services Init]]
- [[_COMMUNITY_FastAPI Dependency|FastAPI Dependency]]
- [[_COMMUNITY_SQLAlchemy Dependency|SQLAlchemy Dependency]]
- [[_COMMUNITY_Supabase Dependency|Supabase Dependency]]
- [[_COMMUNITY_PDFPlumber Dependency|PDFPlumber Dependency]]

## God Nodes (most connected - your core abstractions)
1. `CamCasParser` - 18 edges
2. `Portfolio` - 15 edges
3. `NavCache` - 11 edges
4. `TransactionResponse` - 10 edges
5. `PortfolioResponse` - 10 edges
6. `upload_pdf()` - 10 edges
7. `TransactionCreate` - 9 edges
8. `TransactionUpdate` - 9 edges
9. `Base` - 8 edges
10. `GET()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `upload_pdf()` --calls--> `GET()`  [INFERRED]
  backend/app/routers/upload.py → frontend/src/app/api/python/[...path]/route.ts
- `_search_api()` --calls--> `GET()`  [INFERRED]
  backend/matcher/fund_matcher.py → frontend/src/app/api/python/[...path]/route.ts
- `get_latest_nav()` --calls--> `GET()`  [INFERRED]
  backend/matcher/fund_matcher.py → frontend/src/app/api/python/[...path]/route.ts
- `upload_pdf()` --calls--> `set()`  [INFERRED]
  backend/app/routers/upload.py → frontend/src/components/AddTransactionModal.tsx
- `delete_transaction()` --calls--> `DELETE()`  [INFERRED]
  backend/app/routers/portfolio.py → frontend/src/app/api/python/[...path]/route.ts

## Communities

### Community 0 - "CAM/CAS PDF Parser Logic"
Cohesion: 0.1
Nodes (14): set(), CamCasParser, classify_transaction_type(), parse_amount(), parse_date(), parse_pdf(), CAM & CAS PDF Statement Parser for Indian Mutual Fund Statements.  Handles: - CA, Parse a date string trying multiple formats. (+6 more)

### Community 1 - "Data Models and Pydantic Schemas"
Cohesion: 0.33
Nodes (18): Base, BaseModel, NavCache, Portfolio, Portfolio router — CRUD + NAV refresh with 4-hour caching., Update a transaction. Re-runs scheme matching if fund_name changed., Delete a transaction (ownership verified)., For each unique scheme_code:     1. Check nav_cache — skip if refreshed < 4 hour (+10 more)

### Community 2 - "Portfolio Router & Fund Matcher"
Cohesion: 0.19
Nodes (13): get_latest_nav(), match_scheme_code(), Fund name → AMFI scheme code matcher using mfapi.in REST API., Search mfapi.in for a mutual fund by name and return the scheme code.          S, Call mfapi.in search and return top result., Get the latest NAV for a scheme code from mfapi.in., _search_api(), add_manual_transaction() (+5 more)

### Community 3 - "Upload Router & User DB"
Cohesion: 0.23
Nodes (12): Base, Declarative base for all ORM models., DeclarativeBase, SQLAlchemy ORM models matching the Supabase PostgreSQL schema., UploadedDocument, User, UploadResponse, _get_user_id() (+4 more)

### Community 4 - "Encryption Services"
Cohesion: 0.23
Nodes (11): decrypt_data(), decrypt_string(), encrypt_data(), encrypt_string(), _get_key(), AES-256-CBC encryption/decryption for transaction data at rest., Derive a 32-byte AES-256 key from the ENCRYPTION_KEY setting., Encrypt data using AES-256-CBC. Returns [16-byte IV][ciphertext]. (+3 more)

### Community 5 - "API Routes & Supabase Proxy"
Cohesion: 0.29
Nodes (7): delete_transaction(), DELETE(), GET(), PATCH(), POST(), proxyToFastAPI(), createServerClient()

### Community 6 - "Database Initialization"
Cohesion: 0.33
Nodes (5): _get_database_url(), get_db(), SQLAlchemy database engine and session management. Connects to Supabase PostgreS, Convert DATABASE_URL to use psycopg3 dialect., Dependency that yields a database session.

### Community 7 - "App Config & Settings"
Cohesion: 0.4
Nodes (4): BaseSettings, Config, Application configuration loaded from environment variables., Settings

### Community 8 - "Authentication UI Pages"
Cohesion: 0.67
Nodes (1): handleSubmit()

### Community 9 - "Backend FastAPI Main"
Cohesion: 0.67
Nodes (1): Nivesh FastAPI Application — internal service proxied by Next.js. Handles PDF pa

### Community 10 - "Frontend Root Layout"
Cohesion: 1.0
Nodes (0): 

### Community 11 - "Frontend Landing/Home Page"
Cohesion: 1.0
Nodes (0): 

### Community 12 - "Dashboard Layout Wrapper"
Cohesion: 1.0
Nodes (0): 

### Community 13 - "Dashboard Overview Page"
Cohesion: 1.0
Nodes (0): 

### Community 14 - "Dashboard Portfolio View"
Cohesion: 1.0
Nodes (0): 

### Community 15 - "Dashboard File Upload View"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Confirm Dialog Component"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Navigation Component"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Transaction Data Table"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "SIP Heatmap Chart"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Frontend Providers"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Supabase Client Utils"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Frontend README Concepts"
Cohesion: 1.0
Nodes (2): Next.js, Vercel

### Community 23 - "PostCSS Configuration"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Next.js Configuration"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Next.js Environment Definitions"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Tailwind CSS Config"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Next.js Middleware"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "NextAuth API Route"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Upload Zone UI Component"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Parser Summary UI Component"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Auth Client Library"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Backend App Init"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Backend Routers Init"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Backend Parser Init"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Backend Matcher Init"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Backend Services Init"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "FastAPI Dependency"
Cohesion: 1.0
Nodes (1): fastapi

### Community 38 - "SQLAlchemy Dependency"
Cohesion: 1.0
Nodes (1): sqlalchemy

### Community 39 - "Supabase Dependency"
Cohesion: 1.0
Nodes (1): supabase

### Community 40 - "PDFPlumber Dependency"
Cohesion: 1.0
Nodes (1): pdfplumber

## Knowledge Gaps
- **33 isolated node(s):** `Config`, `Application configuration loaded from environment variables.`, `SQLAlchemy database engine and session management. Connects to Supabase PostgreS`, `Convert DATABASE_URL to use psycopg3 dialect.`, `Declarative base for all ORM models.` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Frontend Root Layout`** (2 nodes): `layout.tsx`, `RootLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Landing/Home Page`** (2 nodes): `page.tsx`, `HomePage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard Layout Wrapper`** (2 nodes): `layout.tsx`, `DashboardLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard Overview Page`** (2 nodes): `page.tsx`, `DashboardPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard Portfolio View`** (2 nodes): `page.tsx`, `PortfolioPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard File Upload View`** (2 nodes): `page.tsx`, `handleUpload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Confirm Dialog Component`** (2 nodes): `ConfirmDialog()`, `ConfirmDialog.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Navigation Component`** (2 nodes): `Navbar.tsx`, `Navbar()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Transaction Data Table`** (2 nodes): `TransactionTable.tsx`, `TransactionTable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `SIP Heatmap Chart`** (2 nodes): `SIPHeatmap.tsx`, `getCellColor()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Providers`** (2 nodes): `Providers.tsx`, `Providers()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Supabase Client Utils`** (2 nodes): `supabase-browser.ts`, `createBrowserClient()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend README Concepts`** (2 nodes): `Next.js`, `Vercel`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PostCSS Configuration`** (1 nodes): `postcss.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Configuration`** (1 nodes): `next.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Environment Definitions`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tailwind CSS Config`** (1 nodes): `tailwind.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Middleware`** (1 nodes): `middleware.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `NextAuth API Route`** (1 nodes): `route.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Upload Zone UI Component`** (1 nodes): `UploadZone.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Parser Summary UI Component`** (1 nodes): `ParseSummary.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Auth Client Library`** (1 nodes): `auth.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend App Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Routers Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Parser Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Matcher Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Services Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `FastAPI Dependency`** (1 nodes): `fastapi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `SQLAlchemy Dependency`** (1 nodes): `sqlalchemy`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Supabase Dependency`** (1 nodes): `supabase`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PDFPlumber Dependency`** (1 nodes): `pdfplumber`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `upload_pdf()` connect `Upload Router & User DB` to `CAM/CAS PDF Parser Logic`, `Data Models and Pydantic Schemas`, `Portfolio Router & Fund Matcher`, `Encryption Services`, `API Routes & Supabase Proxy`?**
  _High betweenness centrality (0.237) - this node is a cross-community bridge._
- **Why does `Portfolio` connect `Data Models and Pydantic Schemas` to `Portfolio Router & Fund Matcher`, `Upload Router & User DB`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `GET()` connect `API Routes & Supabase Proxy` to `CAM/CAS PDF Parser Logic`, `Portfolio Router & Fund Matcher`, `Upload Router & User DB`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Portfolio` (e.g. with `Base` and `Upload router — PDF upload to Supabase Storage → parse → match → store.`) actually correct?**
  _`Portfolio` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `NavCache` (e.g. with `Base` and `Portfolio router — CRUD + NAV refresh with 4-hour caching.`) actually correct?**
  _`NavCache` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `TransactionResponse` (e.g. with `Portfolio router — CRUD + NAV refresh with 4-hour caching.` and `Get all portfolio transactions. Refreshes current_units from mfapi.in     with 4`) actually correct?**
  _`TransactionResponse` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `PortfolioResponse` (e.g. with `Portfolio router — CRUD + NAV refresh with 4-hour caching.` and `Get all portfolio transactions. Refreshes current_units from mfapi.in     with 4`) actually correct?**
  _`PortfolioResponse` has 8 INFERRED edges - model-reasoned connections that need verification._