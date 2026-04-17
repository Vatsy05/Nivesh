"""
CAM & CAS PDF Statement Parser for Indian Mutual Fund Statements.

Handles:
- CAMS + KFintech Consolidated Account Statements (CAS)
- Multi-line transaction format where each transaction is 5-6 consecutive lines

PDF layout per transaction block:
  DD-Mon-YYYY
  amount (e.g. 999.95 or (5,000.00))
  nav/price
  units (e.g. 13.194 or (154.609))
  description text
  unit_balance

Uses PyMuPDF as primary parser, pdfplumber as fallback.
"""
import re
import io
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

import pdfplumber
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ── Transaction type mapping ──────────────────────────────────────────────────

TRANSACTION_TYPE_MAP = {
    "purchase": "lumpsum",
    "purchase-sip": "SIP",
    "sip": "SIP",
    "sip purchase": "SIP",
    "systematic investment": "SIP",
    "systematic": "SIP",
    "systematic purchase": "SIP",
    "purchase systematic": "SIP",
    "si": "SIP",
    "redemption": "redemption",
    "redeem": "redemption",
    "repurchase": "redemption",
    "sale": "redemption",
    "switch in": "switch_in",
    "switch-in": "switch_in",
    "switchin": "switch_in",
    "sw in": "switch_in",
    "switch out": "switch_out",
    "switch-out": "switch_out",
    "switchout": "switch_out",
    "sw out": "switch_out",
    "dividend payout": "dividend",
    "dividend reinvestment": "dividend_reinvest",
    "div reinvest": "dividend_reinvest",
    "lumpsum": "lumpsum",
    "additional purchase": "lumpsum",
    "new purchase": "lumpsum",
    "purchase - additional": "lumpsum",
}

# ── AMC identifiers ──────────────────────────────────────────────────────────

AMC_KEYWORDS = [
    "HDFC", "ICICI", "SBI", "Axis", "Kotak", "Mirae", "Nippon",
    "DSP", "Tata", "UTI", "Aditya Birla", "ABSL", "Franklin",
    "Motilal", "Parag Parikh", "PPFAS", "Edelweiss", "Sundaram",
    "Canara", "IDFC", "Bandhan", "Baroda", "HSBC", "Quant",
    "Invesco", "L&T", "Mahindra", "JM", "Quantum", "Union",
    "Bank of India", "BOI", "LIC", "PGIM", "KFintech", "WhiteOak",
    "NJ", "360 ONE", "ITI", "Navi",
]

# ── Regex helpers ─────────────────────────────────────────────────────────────

DATE_RE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{4}$")
AMOUNT_RE = re.compile(r"^\(?[\d,]+\.\d{2,}\)?$")
NUMBER_RE = re.compile(r"^\(?[\d,]+\.[\d]+\)?$")
FOLIO_RE = re.compile(r"Folio\s*(?:No)?[:\s]*([A-Za-z0-9/\-]+)", re.IGNORECASE)
FUND_SECTION_RE = re.compile(
    r"^([A-Z][A-Za-z\s'&.()\-]+(?:Mutual Fund|MF|Aditya Birla|PPFAS|Quant|Tata|HDFC|ICICI|SBI|Axis|Kotak|Mirae|Nippon|DSP|UTI|Franklin|Motilal|Parag Parikh|Edelweiss|Sundaram|Canara|IDFC|Bandhan|Baroda|HSBC|Invesco|PGIM|LIC|BOI|WhiteOak|NJ|ITI|Navi)[A-Za-z\s'&.()\-]*)$"
)

# Lines to skip that are not real transactions
SKIP_PATTERNS = [
    re.compile(r"^\*\*\*", re.IGNORECASE),          # ***Address Updated...
    re.compile(r"^\*\*\*NCT", re.IGNORECASE),
    re.compile(r"^Opening Unit Balance", re.IGNORECASE),
    re.compile(r"^Closing Unit Balance", re.IGNORECASE),
    re.compile(r"^NAV on", re.IGNORECASE),
    re.compile(r"^Market Value on", re.IGNORECASE),
    re.compile(r"^Total Cost Value", re.IGNORECASE),
    re.compile(r"^Page \d+ of \d+", re.IGNORECASE),
    re.compile(r"^CAMSCASWS", re.IGNORECASE),
    re.compile(r"^Consolidated Account Statement", re.IGNORECASE),
    re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4} To \d{2}-[A-Za-z]{3}-\d{4}$"),  # date range header
]

STAMP_DUTY_RE = re.compile(r"stamp duty", re.IGNORECASE)
STT_RE = re.compile(r"STT Paid", re.IGNORECASE)


def _is_skip_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    for p in SKIP_PATTERNS:
        if p.search(s):
            return True
    return False


def _is_date(s: str) -> bool:
    return bool(DATE_RE.match(s.strip()))


def _is_amount(s: str) -> bool:
    return bool(AMOUNT_RE.match(s.strip()))


def _is_number(s: str) -> bool:
    return bool(NUMBER_RE.match(s.strip()))


def _parse_date(s: str) -> Optional[date]:
    s = s.strip()
    for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%y"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace(",", "").replace("₹", "").replace("INR", "").strip()
    try:
        val = float(s)
        return -val if neg else val
    except ValueError:
        return None


def _classify_type(text: str) -> str:
    tl = text.lower()
    if any(k in tl for k in ["redemption", "redeem", "repurchase"]):
        return "redemption"
    if any(k in tl for k in ["switch in", "switchin", "sw in"]):
        return "switch_in"
    if any(k in tl for k in ["switch out", "switchout", "sw out"]):
        return "switch_out"
    if any(k in tl for k in ["dividend payout"]):
        return "dividend"
    if any(k in tl for k in ["dividend reinvest", "div reinvest"]):
        return "dividend_reinvest"
    if any(k in tl for k in ["systematic", "sip", "purchase systematic", "purchase sip"]):
        return "SIP"
    if any(k in tl for k in ["purchase", "lumpsum", "additional"]):
        return "lumpsum"
    return "lumpsum"


def _extract_fund_name(line: str) -> Optional[str]:
    """Return fund name if line is a short top-level AMC section header.
    We only match the short header like 'PPFAS Mutual Fund', not the
    long scheme lines like '166ISDGG-quant Infrastructure Fund...').
    """
    s = line.strip()
    # Must be a short line (AMC headers are short)
    if len(s) < 4 or len(s) > 60:
        return None
    # Must NOT look like a scheme code line (starts with alphanumeric code)
    if re.match(r'^[A-Z0-9]{4,}-', s):
        return None
    has_amc = any(a.lower() in s.lower() for a in AMC_KEYWORDS)
    if not has_amc:
        return None
    fund_kw = ["fund", "mf"]
    if any(k in s.lower() for k in fund_kw):
        return s
    return None


# ── Core multi-line block parser ──────────────────────────────────────────────

def _parse_blocks(lines: List[str], fund_name: str, folio: str, holder: str) -> List[Dict]:
    """
    Group consecutive lines into transaction blocks.

    A real transaction block looks like:
      [date]          e.g. 23-Apr-2024
      [amount]        e.g. 999.95 or (5,000.00)
      [nav]           e.g. 47.5941
      [units]         e.g. 21.010 or (32.127)
      [description]   e.g. Purchase SIP-BSE...
      [unit_balance]  e.g. 507.067

    Stamp Duty and STT Paid entries are 3-line blocks with tiny amounts — skipped.
    """
    transactions = []
    seen = set()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        if not line or _is_skip_line(line):
            i += 1
            continue

        # Must start with a date
        if not _is_date(line):
            i += 1
            continue

        txn_date_str = line
        # Peek next lines
        block = [txn_date_str]
        j = i + 1
        while j < n and len(block) < 8:
            nl = lines[j].strip()
            if not nl:
                j += 1
                continue
            # If we hit another date, stop
            if _is_date(nl) and len(block) > 2:
                break
            block.append(nl)
            j += 1

        # skip short blocks (stamp duty / STT: date + tiny amount + description)
        if len(block) < 4:
            i = j
            continue

        # Identify amount, nav, units, description from block[1:]
        numbers = []
        desc_parts = []
        for item in block[1:]:
            if (_is_amount(item) or _is_number(item)) and len(numbers) < 4:
                numbers.append(item)
            elif not _is_number(item):
                desc_parts.append(item)

        if len(numbers) < 3:
            i = j
            continue

        parsed_date = _parse_date(txn_date_str)
        if not parsed_date:
            i = j
            continue

        # numbers order: amount, nav, units (, unit_balance optionally)
        amount = _parse_amount(numbers[0])
        nav = _parse_amount(numbers[1])
        units = _parse_amount(numbers[2])
        description = " ".join(desc_parts).strip()

        # Skip stamp duty / STT lines (very small amounts, specific keywords)
        if STAMP_DUTY_RE.search(description) or STT_RE.search(description):
            i = j
            continue

        # Skip lines that are clearly non-transactions
        if not amount or not units:
            i = j
            continue

        key = f"{parsed_date}_{amount}_{units}"
        if key in seen:
            i = j
            continue
        seen.add(key)

        transactions.append({
            "transaction_date": parsed_date,
            "transaction_type": _classify_type(description),
            "amount_inr": amount,
            "units": units,
            "nav_at_transaction": nav,
            "fund_name": fund_name or "Unknown Fund",
            "folio_number": folio,
            "account_holder_name": holder,
        })

        i = j

    return transactions


# ── Top-level extractor ───────────────────────────────────────────────────────

def _parse_text(text: str, parser_name: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "transactions": [],
        "fund_names": [],
        "amc_names": [],
        "account_holder_name": "",
        "scheme_name_map": {},   # fund_name -> full scheme string from PDF
        "parser_used": parser_name,
        "errors": [],
    }

    if not text or len(text.strip()) < 50:
        result["errors"].append("Extracted text too short — PDF may be an image or still locked")
        return result

    lines = text.split("\n")

    # Extract account holder name (skip document title lines)
    skip_names = {"consolidated account statement", "date", "transaction", "amount", "units", "price"}
    for line in lines[:25]:
        s = line.strip()
        if s.lower() in skip_names:
            continue
        m = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z]+){1,4})$', s)
        if m and 5 < len(m.group(1)) < 60:
            result["account_holder_name"] = m.group(1).strip()
            break

    # ── Build sections ────────────────────────────────────────────────────────
    # A section = one AMC block. Within it we look for:
    #   - scheme line: starts with code prefix like "PP001ZG-..."
    #   - folio line
    #   - transaction lines
    SCHEME_LINE_RE = re.compile(r'^[A-Z0-9]{4,}-')
    WATERMARK_RE = re.compile(r'CAMSCASWS|Version:|Live-\d', re.IGNORECASE)

    sections: List[Tuple[str, str, str, List[str]]] = []  # (fund, folio, scheme_name, lines)
    fund_names: set = set()
    amc_names: set = set()

    current_fund = "Unknown Fund"
    current_folio = ""
    current_scheme = ""
    current_lines: List[str] = []

    for line in lines:
        s = line.strip()

        # AMC-level fund header (short, e.g. "PPFAS Mutual Fund")
        fn = _extract_fund_name(s)
        if fn:
            if current_lines:
                sections.append((current_fund, current_folio, current_scheme, current_lines))
            current_fund = fn
            current_folio = ""
            current_scheme = ""
            current_lines = []
            fund_names.add(fn)
            for amc in AMC_KEYWORDS:
                if amc.lower() in fn.lower():
                    amc_names.add(amc)
                    break
            continue

        # Scheme line (e.g. "PP001ZG-Parag Parikh Flexi Cap Fund - Direct Plan Growth...")
        if SCHEME_LINE_RE.match(s) and len(s) > 10 and not WATERMARK_RE.search(s):
            # Extract the human-readable part after the code prefix
            scheme_human = re.sub(r'^[A-Z0-9]{4,}-', '', s)
            # Strip ISIN and advisor suffixes
            scheme_human = re.sub(r'\s*-\s*ISIN:.*$', '', scheme_human, flags=re.IGNORECASE)
            scheme_human = re.sub(r'\(Advisor:.*?\)', '', scheme_human, flags=re.IGNORECASE)
            scheme_human = re.sub(r'\(formerly.*?\)', '', scheme_human, flags=re.IGNORECASE)
            scheme_human = re.sub(r'\(Non-Demat\)', '', scheme_human, flags=re.IGNORECASE)
            current_scheme = scheme_human.strip(" -,")
            current_lines.append(line)
            continue

        # Folio line
        fm = FOLIO_RE.search(s)
        if fm:
            current_folio = fm.group(1).strip()

        current_lines.append(line)

    if current_lines:
        sections.append((current_fund, current_folio, current_scheme, current_lines))

    # ── Extract transactions from each section ───────────────────────────────
    all_txns: List[Dict] = []
    scheme_name_map: Dict[str, str] = {}

    for fund, folio, scheme, sec_lines in sections:
        txns = _parse_blocks(sec_lines, fund, folio, result["account_holder_name"])
        all_txns.extend(txns)
        if scheme and fund not in scheme_name_map:
            scheme_name_map[fund] = scheme

    result["transactions"] = all_txns
    result["fund_names"] = list(fund_names)
    result["amc_names"] = list(amc_names)
    result["scheme_name_map"] = scheme_name_map

    logger.info(
        f"[{parser_name}] Parsed {len(all_txns)} transactions across "
        f"{len(fund_names)} funds from {len(sections)} sections"
    )
    return result


# ── PDF text extractors ───────────────────────────────────────────────────────

def _extract_text_pymupdf(pdf_bytes: bytes, password: str = "") -> Tuple[str, List[str]]:
    errors: List[str] = []
    pages = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.needs_pass:
            if not password:
                errors.append("PyMuPDF: PDF is password-protected — no password provided")
                doc.close()
                return "", errors
            success = doc.authenticate(password)
            if not success:
                errors.append("PyMuPDF: Incorrect PDF password")
                doc.close()
                return "", errors
            logger.info("PyMuPDF: PDF unlocked successfully")
        for i in range(len(doc)):
            try:
                pages.append(doc[i].get_text("text"))
            except Exception as e:
                errors.append(f"PyMuPDF page {i+1}: {e}")
        doc.close()
    except Exception as e:
        errors.append(f"PyMuPDF open failed: {e}")
    return "\n".join(pages), errors


def _extract_text_pdfplumber(pdf_bytes: bytes, password: str = "") -> Tuple[str, List[str]]:
    errors: List[str] = []
    pages = []
    try:
        open_kwargs = {"password": password} if password else {}
        with pdfplumber.open(io.BytesIO(pdf_bytes), **open_kwargs) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                    else:
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if row:
                                    pages.append("  ".join(str(c) for c in row if c))
                except Exception as e:
                    errors.append(f"pdfplumber page {i+1}: {e}")
    except Exception as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ("password", "encrypted", "decrypt")):
            errors.append(f"pdfplumber: Wrong or missing PDF password — {e}")
        else:
            errors.append(f"pdfplumber open failed: {e}")
    return "\n".join(pages), errors


# ── Public API ────────────────────────────────────────────────────────────────

class CamCasParser:
    """
    Multi-line block parser for CAMS/KFintech Consolidated Account Statements.
    Tries PyMuPDF first; falls back to pdfplumber.
    """

    def __init__(self):
        self.errors: List[str] = []

    def parse(self, pdf_bytes: bytes, password: str = "") -> Dict[str, Any]:
        self.errors = []

        # Primary: PyMuPDF
        logger.info("Parsing with PyMuPDF...")
        text, errs = _extract_text_pymupdf(pdf_bytes, password)
        self.errors.extend(errs)
        result = _parse_text(text, "PyMuPDF")

        # Fallback: pdfplumber
        if len(result["transactions"]) < 3:
            logger.info(f"PyMuPDF got {len(result['transactions'])} txns, retrying with pdfplumber...")
            text2, errs2 = _extract_text_pdfplumber(pdf_bytes, password)
            self.errors.extend(errs2)
            result2 = _parse_text(text2, "pdfplumber")
            if len(result2["transactions"]) > len(result["transactions"]):
                logger.info(f"pdfplumber got {len(result2['transactions'])} txns, using pdfplumber")
                result = result2

        result["errors"].extend(self.errors)
        return result


def parse_pdf(pdf_bytes: bytes, password: str = "") -> Dict[str, Any]:
    """Main entry point: parse a mutual fund PDF statement."""
    return CamCasParser().parse(pdf_bytes, password=password)
