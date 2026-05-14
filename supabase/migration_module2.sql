-- Nivesh Module 2 — Analytics Migration
-- Run this in the Supabase SQL Editor AFTER migration.sql (Module 1)

-- ═══════════════════════════════════════════════════════════════════
-- historical_nav_cache
-- Stores full NAV history per scheme for rolling return computation.
-- Refreshed every 24 hours from mfapi.in.
-- NOT user-scoped (global per scheme — same NAV for all users).
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS historical_nav_cache (
  scheme_code  TEXT        NOT NULL,
  nav_date     DATE        NOT NULL,
  nav_value    NUMERIC(10, 4) NOT NULL,
  last_fetched TIMESTAMP   DEFAULT NOW(),
  PRIMARY KEY (scheme_code, nav_date)
);

-- ═══════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_hist_nav_scheme ON historical_nav_cache(scheme_code);
CREATE INDEX IF NOT EXISTS idx_hist_nav_date   ON historical_nav_cache(nav_date);
CREATE INDEX IF NOT EXISTS idx_hist_nav_scheme_date
  ON historical_nav_cache(scheme_code, nav_date DESC);

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- Globally readable / writeable (data is not user-sensitive).
-- Matches pattern from migration.sql for nav_cache.
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE historical_nav_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "hist_nav_select_all" ON historical_nav_cache
  FOR SELECT USING (true);

CREATE POLICY "hist_nav_insert" ON historical_nav_cache
  FOR INSERT WITH CHECK (true);

CREATE POLICY "hist_nav_update" ON historical_nav_cache
  FOR UPDATE USING (true);

CREATE POLICY "hist_nav_delete" ON historical_nav_cache
  FOR DELETE USING (true);
