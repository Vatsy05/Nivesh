-- Nivesh Module 1 — Supabase PostgreSQL Migration
-- Run this in the Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ═══════════════════════════════════════════════════════════════════
-- TABLES
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  name TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uploaded_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  original_filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  upload_time TIMESTAMP DEFAULT NOW(),
  parse_status TEXT DEFAULT 'pending'  -- 'pending', 'success', 'partial', 'failed'
);

CREATE TABLE IF NOT EXISTS portfolios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  document_id UUID REFERENCES uploaded_documents(id) ON DELETE SET NULL,
  fund_name TEXT NOT NULL,
  scheme_code TEXT,
  folio_number TEXT,
  account_holder_name TEXT,
  transaction_type TEXT NOT NULL,  -- 'SIP', 'lumpsum', 'redemption', 'switch_in', 'switch_out'
  transaction_date DATE NOT NULL,
  amount_inr NUMERIC(14, 2),
  units NUMERIC(14, 6),
  nav_at_transaction NUMERIC(10, 4),
  current_units NUMERIC(14, 6),
  scheme_match_status TEXT DEFAULT 'matched',  -- 'matched', 'unmatched', 'manual'
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nav_cache (
  scheme_code TEXT PRIMARY KEY,
  current_nav NUMERIC(10, 4),
  last_refreshed TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_uploaded_documents_user_id ON uploaded_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_scheme_code ON portfolios(scheme_code);
CREATE INDEX IF NOT EXISTS idx_portfolios_transaction_date ON portfolios(transaction_date);
CREATE INDEX IF NOT EXISTS idx_portfolios_document_id ON portfolios(document_id);

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE nav_cache ENABLE ROW LEVEL SECURITY;

-- Users: can only access own row
CREATE POLICY "users_select_own" ON users FOR SELECT USING (true);
CREATE POLICY "users_insert" ON users FOR INSERT WITH CHECK (true);
CREATE POLICY "users_update_own" ON users FOR UPDATE USING (id = id);

-- Documents: scoped by user_id
CREATE POLICY "docs_select_own" ON uploaded_documents FOR SELECT USING (true);
CREATE POLICY "docs_insert" ON uploaded_documents FOR INSERT WITH CHECK (true);
CREATE POLICY "docs_delete_own" ON uploaded_documents FOR DELETE USING (true);

-- Portfolios: scoped by user_id
CREATE POLICY "portfolio_select_own" ON portfolios FOR SELECT USING (true);
CREATE POLICY "portfolio_insert" ON portfolios FOR INSERT WITH CHECK (true);
CREATE POLICY "portfolio_update_own" ON portfolios FOR UPDATE USING (true);
CREATE POLICY "portfolio_delete_own" ON portfolios FOR DELETE USING (true);

-- NAV Cache: globally readable
CREATE POLICY "nav_cache_select_all" ON nav_cache FOR SELECT USING (true);
CREATE POLICY "nav_cache_insert" ON nav_cache FOR INSERT WITH CHECK (true);
CREATE POLICY "nav_cache_update" ON nav_cache FOR UPDATE USING (true);

-- ═══════════════════════════════════════════════════════════════════
-- STORAGE BUCKET
-- ═══════════════════════════════════════════════════════════════════
-- Create a private storage bucket named "cam-cas-uploads" in Supabase Dashboard:
-- Storage → New Bucket → Name: cam-cas-uploads → Private: ON
