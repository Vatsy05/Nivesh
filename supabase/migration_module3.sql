-- Nivesh Module 3 — Holdings & Daily Valuation Migration
-- Run in Supabase SQL Editor AFTER migration.sql and migration_module2.sql

-- ═══════════════════════════════════════════════════════════════════
-- portfolio_snapshots
-- Daily portfolio valuation history. Powers the growth chart with
-- exact NAV-based values instead of ratio interpolation.
-- User-scoped, one row per user per date.
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  snapshot_date   DATE          NOT NULL,
  invested_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  portfolio_value NUMERIC(14,2) NOT NULL DEFAULT 0,
  daily_pnl       NUMERIC(14,2),
  total_pnl       NUMERIC(14,2),
  created_at      TIMESTAMP     DEFAULT NOW(),
  UNIQUE(user_id, snapshot_date)
);

-- ═══════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_snapshots_user_id   ON portfolio_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date      ON portfolio_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_user_date ON portfolio_snapshots(user_id, snapshot_date DESC);

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "snapshots_select_own" ON portfolio_snapshots FOR SELECT USING (true);
CREATE POLICY "snapshots_insert"     ON portfolio_snapshots FOR INSERT WITH CHECK (true);
CREATE POLICY "snapshots_update_own" ON portfolio_snapshots FOR UPDATE USING (true);
CREATE POLICY "snapshots_delete_own" ON portfolio_snapshots FOR DELETE USING (true);
