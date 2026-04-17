"""
CAM & CAS PDF Statement Parser for Indian Mutual Fund Statements.

Handles:
- CAM reports: issued by CAMS (Axis, HDFC, ICICI, Kotak, SBI, Mirae, etc.)
- CAS reports: issued by NSDL/CDSL (consolidated across all AMCs)

Uses pdfplumber as primary parser, PyMuPDF (fitz) as fallback.
Multiple regex patterns per field for robustness.
"""
import re
import io
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

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
    "Bank of India", "BOI", "LIC", "PGIM",
]

# ── Folio patterns ───────────────────────────────────────────────────────────

FOLIO_PATTERNS = [
    re.compile(r"Folio\s*(?:No|Number|#)?[\s:.]*([A-Za-z0-9/\-]+)", re.IGNORECASE),
    re.compile(r"Folio:\s*([A-Za-z0-9/\-]+)", re.IGNORECASE),
    re.compile(r"Folio\s+(\d[\d/\-]+\d)", re.IGNORECASE),
]

# ── Transaction line patterns ────────────────────────────────────────────────

TRANSACTION_PATTERNS = [
    # Pattern 1 (CAMS): Date  Description  Amount  Units  NAV  [Balance]
    re.compile(
        r"(\d{1,2}[-/]\w{2,3}[-/]\d{2,4})\s+"
        r"([\w\s\-/()]+?)\s+"
        r"([\d,]+\.\d{2})\s+"
        r"([\d,]+\.\d{2,6})\s+"
        r"([\d,]+\.\d{2,4})"
    ),
    # Pattern 2 (CAS): Date  Transaction  Amount  Units  Price
    re.compile(
        r"(\d{1,2}[-/]\w{2,3}[-/]\d{2,4})\s+"
        r"(.+?)\s+"
        r"(?:₹|INR)?\s*([\d,]+\.?\d*)\s+"
        r"(-?[\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)"
    ),
    # Pattern 3 (Flexible): Date + numbers
    re.compile(
        r"(\d{1,2}[-/]\w{2,3}[-/]\d{2,4})"
        r".*?"
        r"(-?[\d,]+\.\d{2})\s+"
        r"(-?[\d,]+\.\d{2,6})\s+"
        r"([\d,]+\.\d{2,4})"
    ),
    # Pattern 4 (Minimal): Date DD/MM/YYYY + 3 numbers
    re.compile(
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+"
        r".*?"
        r"([\d,]+\.?\d+)\s+"
        r"([\d,]+\.?\d+)\s+"
        r"([\d,]+\.?\d+)"
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_date(date_str: str) -> Optional[date]:
    """Parse a date string trying multiple formats."""
    date_str = date_str.strip()
    for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%y", "%d/%m/%y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    logger.warning(f"Could not parse date: '{date_str}'")
    return None


def parse_amount(s: str) -> Optional[float]:
    """Parse an amount string handling commas, currency symbols, and negative parens."""
    if not s:
        return None
    s = s.strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    if s.startswith("-"):
        neg = True
        s = s[1:]
    s = s.replace(",", "").replace("₹", "").replace("INR", "").strip()
    try:
        val = float(s)
        return -val if neg else val
    except ValueError:
        return None


def classify_transaction_type(text: str) -> str:
    """Map raw transaction description to enum type."""
    text_lower = text.strip().lower()
    if text_lower in TRANSACTION_TYPE_MAP:
        return TRANSACTION_TYPE_MAP[text_lower]
    for key, val in TRANSACTION_TYPE_MAP.items():
        if key in text_lower:
            return val
    return "lumpsum"


# ── Parser Class ──────────────────────────────────────────────────────────────

class CamCasParser:
    """
    Dual-mode parser for CAM and CAS mutual fund PDF statements.
    Tries pdfplumber first; if < 3 transactions extracted, retries with PyMuPDF.
    """

    def __init__(self):
        self.errors: List[str] = []

    def parse(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Parse a PDF and return extracted transactions + metadata.
        
        Returns:
            {
                "transactions": [list of dicts],
                "fund_names": [unique fund names],
                "amc_names": [unique AMC names],
                "account_holder_name": str,
                "parser_used": str,
                "errors": [error messages]
            }
        """
        self.errors = []

        # Attempt 1: pdfplumber
        logger.info("Parsing with pdfplumber...")
        text = self._extract_text_pdfplumber(pdf_bytes)
        result = self._parse_transactions(text, "pdfplumber")

        # Fallback: if < 3 transactions, retry with PyMuPDF
        if len(result["transactions"]) < 3:
            logger.info(f"pdfplumber got {len(result['transactions'])} txns, retrying with PyMuPDF...")
            text2 = self._extract_text_pymupdf(pdf_bytes)
            result2 = self._parse_transactions(text2, "PyMuPDF")
            if len(result2["transactions"]) > len(result["transactions"]):
                logger.info(f"PyMuPDF got {len(result2['transactions'])} txns, using PyMuPDF")
                result = result2

        result["errors"] = self.errors
        return result

    def _extract_text_pdfplumber(self, pdf_bytes: bytes) -> str:
        pages = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
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
                        self.errors.append(f"pdfplumber page {i+1}: {e}")
        except Exception as e:
            self.errors.append(f"pdfplumber open failed: {e}")
        return "\n".join(pages)

    def _extract_text_pymupdf(self, pdf_bytes: bytes) -> str:
        pages = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for i in range(len(doc)):
                try:
                    pages.append(doc[i].get_text("text"))
                except Exception as e:
                    self.errors.append(f"PyMuPDF page {i+1}: {e}")
            doc.close()
        except Exception as e:
            self.errors.append(f"PyMuPDF open failed: {e}")
        return "\n".join(pages)

    def _detect_format(self, text: str) -> str:
        """Detect if this is a CAS or CAM format statement."""
        cas_indicators = ["consolidated account statement", "nsdl", "cdsl", "depository", "cas"]
        return "CAS" if any(kw in text[:5000].lower() for kw in cas_indicators) else "CAM"

    def _parse_transactions(self, text: str, parser_name: str) -> Dict[str, Any]:
        result = {
            "transactions": [],
            "fund_names": [],
            "amc_names": [],
            "account_holder_name": "",
            "parser_used": parser_name,
        }

        if not text or len(text.strip()) < 50:
            self.errors.append("Extracted text too short")
            return result

        result["account_holder_name"] = self._extract_account_holder(text)
        doc_format = self._detect_format(text)
        logger.info(f"Document format: {doc_format}")

        # Split into fund/folio sections
        sections = self._split_into_sections(text)
        if not sections:
            sections = [("Unknown Fund", "", text)]

        fund_names = set()
        amc_names = set()

        for fund_name, folio, section_text in sections:
            txns = self._extract_from_section(section_text, fund_name, folio, result["account_holder_name"])
            result["transactions"].extend(txns)
            if fund_name and fund_name != "Unknown Fund":
                fund_names.add(fund_name)
                for amc in AMC_KEYWORDS:
                    if amc.lower() in fund_name.lower():
                        amc_names.add(amc)
                        break

        result["fund_names"] = list(fund_names)
        result["amc_names"] = list(amc_names)
        logger.info(f"Parsed {len(result['transactions'])} transactions, {len(fund_names)} funds, {len(amc_names)} AMCs")
        return result

    def _extract_account_holder(self, text: str) -> str:
        patterns = [
            re.compile(r"(?:Name|Account\s*Holder|Investor)\s*:?\s*([A-Z][A-Za-z\s.]+?)(?:\n|Email|PAN|Address|Mobile)", re.IGNORECASE),
            re.compile(r"Dear\s+([A-Z][A-Za-z\s.]+?)(?:\n|,)", re.IGNORECASE),
            re.compile(r"(?:Mr|Mrs|Ms)\.?\s+([A-Z][A-Za-z\s]+)", re.IGNORECASE),
        ]
        for p in patterns:
            m = p.search(text[:2000])
            if m:
                name = m.group(1).strip().rstrip(",.:;")
                if 3 < len(name) < 80:
                    return name
        return ""

    def _split_into_sections(self, text: str) -> List[Tuple[str, str, str]]:
        sections = []
        lines = text.split("\n")
        current_fund = ""
        current_folio = ""
        current_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_lines.append(line)
                continue

            # Check for folio
            folio_match = None
            for p in FOLIO_PATTERNS:
                folio_match = p.search(stripped)
                if folio_match:
                    break

            if folio_match:
                if current_fund and current_lines:
                    sections.append((current_fund, current_folio, "\n".join(current_lines)))
                current_folio = folio_match.group(1).strip()
                current_lines = [line]
                fund = self._find_fund_name(stripped, lines, lines.index(line) if line in lines else 0)
                if fund:
                    current_fund = fund
                continue

            # Check for fund name
            fund = self._match_fund_name(stripped)
            if fund and not self._is_transaction_line(stripped):
                if current_fund and current_lines:
                    sections.append((current_fund, current_folio, "\n".join(current_lines)))
                current_fund = fund
                current_lines = [line]
                continue

            current_lines.append(line)

        if current_fund and current_lines:
            sections.append((current_fund, current_folio, "\n".join(current_lines)))

        return sections

    def _find_fund_name(self, folio_line: str, all_lines: List[str], idx: int) -> str:
        for i in range(max(0, idx - 3), min(len(all_lines), idx + 2)):
            fund = self._match_fund_name(all_lines[i].strip())
            if fund:
                return fund
        return ""

    def _match_fund_name(self, text: str) -> str:
        if len(text) < 10 or len(text) > 200:
            return ""
        has_amc = any(a.lower() in text.lower() for a in AMC_KEYWORDS)
        if not has_amc:
            return ""
        fund_kw = ["fund", "plan", "scheme", "growth", "dividend", "direct", "regular",
                    "idcw", "option", "flexi", "cap", "equity", "debt", "hybrid", "liquid"]
        if any(k in text.lower() for k in fund_kw):
            name = re.sub(r"\s+\d{1,2}[-/]\w{2,3}[-/]\d{2,4}.*$", "", text)
            name = re.sub(r"\s+Folio.*$", "", name, flags=re.IGNORECASE)
            name = name.strip()
            if len(name) > 10:
                return name
        return ""

    def _is_transaction_line(self, line: str) -> bool:
        return bool(re.match(r"^\s*\d{1,2}[-/]\w{2,3}[-/]\d{2,4}", line))

    def _extract_from_section(self, text: str, fund_name: str, folio: str, holder: str) -> List[Dict]:
        transactions = []
        seen = set()

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or len(stripped) < 15:
                continue
            if any(k in stripped.lower() for k in ["date", "description", "amount", "nav", "balance", "---"]):
                if stripped.lower().startswith("date"):
                    continue

            txn = self._try_parse_line(stripped)
            if txn and txn.get("transaction_date"):
                key = f"{txn['transaction_date']}_{txn.get('amount_inr')}_{txn.get('units')}"
                if key not in seen:
                    txn["fund_name"] = fund_name or "Unknown Fund"
                    txn["folio_number"] = folio
                    txn["account_holder_name"] = holder
                    transactions.append(txn)
                    seen.add(key)

        return transactions

    def _try_parse_line(self, line: str) -> Optional[Dict]:
        for i, pattern in enumerate(TRANSACTION_PATTERNS):
            m = pattern.search(line)
            if m:
                try:
                    return self._build_txn(m, i, line)
                except Exception as e:
                    logger.debug(f"Pattern {i} failed: {e}")
        return None

    def _build_txn(self, m: re.Match, idx: int, line: str) -> Optional[Dict]:
        g = m.groups()
        txn: Dict[str, Any] = {}

        if idx == 0:  # CAMS format
            txn["transaction_date"] = parse_date(g[0])
            txn["transaction_type"] = classify_transaction_type(g[1])
            txn["amount_inr"] = parse_amount(g[2])
            txn["units"] = parse_amount(g[3])
            txn["nav_at_transaction"] = parse_amount(g[4])
        elif idx == 1:  # CAS format
            txn["transaction_date"] = parse_date(g[0])
            txn["transaction_type"] = classify_transaction_type(g[1])
            txn["amount_inr"] = parse_amount(g[2])
            txn["units"] = parse_amount(g[3])
            txn["nav_at_transaction"] = parse_amount(g[4])
        elif idx == 2:  # Flexible
            txn["transaction_date"] = parse_date(g[0])
            txn["amount_inr"] = parse_amount(g[1])
            txn["units"] = parse_amount(g[2])
            txn["nav_at_transaction"] = parse_amount(g[3])
            txn["transaction_type"] = self._type_from_text(line)
        elif idx == 3:  # Minimal
            txn["transaction_date"] = parse_date(g[0])
            nums = sorted([abs(parse_amount(x) or 0) for x in g[1:4]])
            if len(nums) == 3:
                txn["nav_at_transaction"] = nums[0]
                txn["units"] = nums[1]
                txn["amount_inr"] = nums[2]
            txn["transaction_type"] = self._type_from_text(line)

        if not txn.get("transaction_date"):
            return None
        if txn.get("amount_inr") is None and txn.get("units") is None:
            return None
        return txn

    def _type_from_text(self, text: str) -> str:
        tl = text.lower()
        for k, v in TRANSACTION_TYPE_MAP.items():
            if k in tl:
                return v
        return "lumpsum"


def parse_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Main entry point: parse a mutual fund PDF statement."""
    return CamCasParser().parse(pdf_bytes)
