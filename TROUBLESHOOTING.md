# Nivesh Troubleshooting Guide

## Issue 1: PDF Upload Stuck at 99%

**Root Cause:** The fund matching phase (`asyncio.gather()`) had no timeout and could hang indefinitely if mfapi.in was slow or unresponsive.

**Fixes Applied:**
1. ✅ Added **10-second timeout per fund** in fund matching
2. ✅ Added **60-second overall timeout** for all funds combined
3. ✅ Added **detailed progress logging** at each stage
4. ✅ Graceful fallback if matching times out (funds remain "unmatched" but processing continues)

### New Upload Flow with Logging

```
User uploads PDF
    ↓ [Log: "Starting PDF parse for {file}"]
    ↓
Parse PDF (extract transactions, fund names, closing balances)
    ↓ [Log: "PDF parse complete: N transactions extracted"]
    ↓
Fund Matching (concurrent, with 10s timeout per fund)
    ↓ [Log: "Starting concurrent fund matching for N funds..."]
    ↓ [Log per fund: "Matched 'fund_name' → scheme_code=12345"]
    ↓ [Log: "Fund matching complete: M/N matched"]
    ↓
Store Transactions (bulk insert)
    ↓ [Log: "Storing N transactions to database..."]
    ↓
Update Closing Units (SQL bulk update)
    ↓ [Log: "Processing K closing balances..."]
    ↓
Commit to Database
    ↓ [Log: "Committing N transactions to database..."]
    ↓ [Log: "Database commit successful"]
    ↓
Return Response (document_id, parse_status, count)
```

### Debugging Stuck Uploads

Check the **FastAPI logs** for these indicators:

```bash
# Good signs:
INFO     | PDF parse complete: 47 transactions extracted
INFO     | Starting concurrent fund matching for 12 funds...
INFO     | Matched 'PPFAS Mutual Fund' → scheme_code=119539
INFO     | Fund matching complete: 11/12 matched

# Warning signs (timeout recovery):
WARNING  | mfapi.in match TIMEOUT for 'Some Fund' (10s)
WARNING  | Overall fund matching timeout — continuing with partial results

# Error (database issue):
ERROR    | Database commit failed: ...
```

**If stuck on fund matching:**
- Check if mfapi.in API is responding: `curl https://api.mfapi.in/mf`
- Check network connectivity: `ping google.com`
- Try uploading a simpler PDF with fewer funds first

**If stuck on database commit:**
- Check PostgreSQL connection: verify `DATABASE_URL` in `.env`
- Check if database is accepting connections
- Look for long-running transactions that might be blocking

---

## Issue 2: `compute_all_metrics()` Missing Argument

**Error:** `TypeError: compute_all_metrics() missing 1 required positional argument: 'current_value'`

**Root Cause:** The function signature was updated to require 3 args: `(cashflows, invested_amount, current_value)`, but the call in `holdings.py` only passed 2 args: `(cashflows, total_current)`.

**Fix Applied:** ✅ Updated call to pass both `total_invested` and `total_current`

```python
# Before (broken):
metrics = compute_all_metrics(cashflows, total_current)

# After (fixed):
metrics = compute_all_metrics(cashflows, total_invested, total_current)
```

---

## Common Issues & Solutions

### 1. Dashboard Shows "No Data"

**Symptoms:** After uploading a PDF, the portfolio dashboard shows empty.

**Likely Causes:**
- PDF has no recognized transactions (parser failed silently)
- Fund matching failed for all funds (scheme_code = None)
- Database connection lost before commit

**Solutions:**
```bash
# Check backend logs for parse errors
tail -100 /var/log/uvicorn.log | grep -i "error\|failed"

# Verify data was inserted
psql $DATABASE_URL -c "SELECT COUNT(*) FROM portfolios WHERE user_id='your_user_id';"

# Re-upload with verbose logging
# Add DEBUG level logging in .env:
# LOG_LEVEL=DEBUG
```

### 2. Fund Matching Very Slow

**Symptoms:** Upload takes 2+ minutes even for small PDFs.

**Causes:**
- mfapi.in API is slow (each fund takes 5+ seconds)
- Network latency
- Many funds in the portfolio

**Solutions:**
- Check mfapi.in status: `time curl https://api.mfapi.in/mf/119539`
- If > 2 seconds, it's an mfapi.in issue
- Workaround: Consider caching scheme codes locally after first match

### 3. NAV Not Updating

**Symptoms:** Portfolio value stays stale, doesn't change day-to-day.

**Causes:**
- NAV cache not refreshed (4-hour TTL)
- mfapi.in returning no data for a scheme
- scheme_code is NULL (fund not matched)

**Solutions:**
```bash
# Force NAV refresh
curl -X POST http://localhost:8000/portfolio/refresh-nav \
  -H "X-User-Id: your_user_id"

# Check NAV cache
psql $DATABASE_URL -c "SELECT * FROM nav_cache LIMIT 5;"

# If scheme_code is NULL, re-upload PDF
```

### 4. Encryption Key Error

**Symptoms:** `ValueError: Invalid key size. Key must be 32 bytes for AES-256`

**Causes:**
- `ENCRYPTION_KEY` in `.env` is not exactly 32 bytes

**Solutions:**
```bash
# Generate a valid 32-byte key (base64 encoded)
python3 -c "import os; print(os.urandom(32).hex())"

# Add to .env:
# ENCRYPTION_KEY=<the 64-char hex string above>
```

### 5. Database Connection Timeout

**Symptoms:** `psycopg2.OperationalError: server closed the connection unexpectedly`

**Causes:**
- Database is down or unreachable
- Network issue
- Connection pool exhausted

**Solutions:**
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Restart the backend to reset connection pool
kill $(lsof -t -i:8000)
uvicorn app.main:app --reload

# Check Supabase dashboard for connection logs
```

---

## Diagnostic Checklist

Before reporting a bug, verify:

- [ ] FastAPI is running: `curl http://localhost:8000/health`
- [ ] Next.js is running on port 3000
- [ ] Database connection works: `psql $DATABASE_URL -c "SELECT 1;"`
- [ ] PDF is valid: `file your_cas.pdf` (should show "PDF")
- [ ] Supabase credentials are correct in `.env`
- [ ] Encryption key is 32 bytes: `echo $ENCRYPTION_KEY | wc -c` (should be 65 = 64 hex chars + newline)

---

## Performance Tuning

### For Large Portfolios (100+ transactions)

**Slow Steps:**
1. PDF parsing — O(pages)
2. Fund matching — O(unique_funds) × 10s timeout
3. Closing balance updates — O(funds) × 1 SQL update

**Optimizations:**
1. **Cache fund matches**: Store `fund_name → scheme_code` lookup locally
2. **Batch SQL updates**: Use `INSERT ... ON CONFLICT` instead of individual UPDATEs
3. **Async parsing**: Use async PDF parsing (currently synchronous)

### Database Query Optimization

Add indexes for faster lookups:

```sql
-- Speed up portfolio queries by user
CREATE INDEX idx_portfolio_user_id ON portfolios(user_id);
CREATE INDEX idx_portfolio_scheme_code ON portfolios(scheme_code);

-- Speed up NAV cache lookups
CREATE INDEX idx_nav_cache_scheme ON nav_cache(scheme_code);
```

---

## When All Else Fails

**1. Clear all data and re-upload fresh:**

```bash
# Connect to database
psql $DATABASE_URL

-- Delete all transactions for user
DELETE FROM portfolios WHERE user_id = 'your_user_id';
DELETE FROM portfolio_snapshots WHERE user_id = 'your_user_id';
DELETE FROM historical_nav_cache; -- careful, affects all users

-- Then re-upload PDF
```

**2. Restart everything:**

```bash
# Kill backend
pkill -f "uvicorn app.main"

# Kill Next.js
pkill -f "next dev"

# Clear caches
rm -rf /Users/dosvatsky/Nivesh/backend/.pytest_cache
rm -rf /Users/dosvatsky/Nivesh/frontend/.next

# Restart
cd backend && uvicorn app.main:app --reload &
cd frontend && npm run dev &
```

**3. Enable debug logging:**

```python
# In backend/app/main.py, change logging level:
logging.basicConfig(level=logging.DEBUG)  # was INFO
```

---

## Monitoring & Alerts

### Key Metrics to Watch

1. **Upload time**: Should be <30 seconds for typical 10-transaction CAS
2. **Fund matching rate**: Should be >90% matched
3. **Portfolio load time**: Dashboard should load in <2 seconds
4. **NAV staleness**: Cache should refresh every 4 hours

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "Nivesh FastAPI"}

# Frontend health (check for 200 status)
curl -I http://localhost:3000/dashboard

# Database connection
psql $DATABASE_URL -c "SELECT COUNT(*) as users FROM users;"
```

---

**Last Updated:** May 2026  
**Version:** 1.1 (after fixes for timeouts and function signature)
