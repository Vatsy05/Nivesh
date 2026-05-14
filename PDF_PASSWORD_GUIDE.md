# Password-Protected PDF Troubleshooting

## The Problem

Your PDF is **password-protected**, and the parser is likely hanging when PyMuPDF tries to authenticate the password. This causes the upload to timeout.

**Symptoms:**
- Upload progress reaches 99% then times out
- Error: "PDF parsing timed out"
- FastAPI logs show no parsing errors, just silence

**Root Cause:**
PyMuPDF's `doc.authenticate(password)` call can hang indefinitely if:
1. The password is **incorrect**
2. The PDF uses **uncommon encryption** that PyMuPDF doesn't handle well
3. There's a **bug in the specific PDF's encryption metadata**

---

## Quick Troubleshooting

### Step 1: Try WITHOUT a Password First

Many CAS/CAS PDFs are "protected" but don't actually require a password to open:

1. Go to the upload page
2. **Leave the password field BLANK**
3. Click "Parse Statement"

If this works, the password field was optional.

### Step 2: If That Fails, Verify Your Password

**Common passwords for Indian mutual fund statements:**
- Your **PAN number** (all 10 characters)
- Your **email address** (exact spelling)
- Your **date of birth** (DDMMYYYY format, e.g., 15051990)
- Sometimes a combination like "PAN+DOB"

**To test your password:**
1. Open the PDF on your computer with a PDF reader
2. Look for a "Document Security" or "Properties" option
3. Try to copy text — if you can, it's not password-protected
4. If it asks for a password when opening, verify you know the correct password

### Step 3: Try a Different Password Format

If you think you know the password but it's still timing out:

**Test these variations:**
- Without spaces: `MyPassword` not `My Password`
- Exact case: `John@123` not `john@123`
- Date formats: `15051990` (DDMMYYYY) vs `1990-05-15` (YYYY-MM-DD)

### Step 4: Contact Your Mutual Fund Custodian

If the password is from your mutual fund account:
- **CAMS:** Contact them directly or check your registered email
- **KFintech:** Contact them directly or check your account
- **Your Fund's Website:** Download a fresh CAS statement (might not have the same password)

---

## For Developers: How to Fix This

### Option 1: Use PyMuPDF Fallback (Recommended)

If PyMuPDF hangs on authentication, we can **skip PyMuPDF entirely** for password-protected PDFs and use **pdfplumber** which is more robust:

```python
# In backend/parser/cam_cas_parser.py, modify CamCasParser.parse():

def parse(self, pdf_bytes: bytes, password: str = "") -> Dict[str, Any]:
    self.errors = []

    # If password-protected, skip PyMuPDF (it hangs sometimes)
    # Go straight to pdfplumber
    doc_test = fitz.open(stream=pdf_bytes, filetype="pdf")
    needs_pass = doc_test.needs_pass
    doc_test.close()

    if needs_pass and password:
        logger.warning(f"PDF needs password — skipping PyMuPDF, using pdfplumber")
        text, errs = _extract_text_pdfplumber(pdf_bytes, password)
        self.errors.extend(errs)
        result = _parse_text(text, "pdfplumber")
    else:
        # No password needed, try PyMuPDF first
        text, errs = _extract_text_pymupdf(pdf_bytes, password)
        self.errors.extend(errs)
        result = _parse_text(text, "PyMuPDF")

        # Fallback to pdfplumber if PyMuPDF got few transactions
        if len(result["transactions"]) < 3:
            logger.info(f"PyMuPDF got {len(result['transactions'])} txns, retrying with pdfplumber...")
            text2, errs2 = _extract_text_pdfplumber(pdf_bytes, password)
            self.errors.extend(errs2)
            result2 = _parse_text(text2, "pdfplumber")
            if len(result2["transactions"]) > len(result["transactions"]):
                logger.info(f"pdfplumber got {len(result2['transactions'])} txns, using it")
                result = result2

    result["errors"].extend(self.errors)
    return result
```

### Option 2: Add Encryption Detection & Skip Password-Protected PDFs

Alternatively, detect password-protected PDFs upfront and reject them:

```python
def _is_password_protected(pdf_bytes: bytes) -> bool:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        needs_pass = doc.needs_pass
        doc.close()
        return needs_pass
    except:
        return False

# In upload.py:
if _is_password_protected(pdf_bytes) and not password:
    raise HTTPException(
        status_code=400,
        detail="This PDF is password-protected. Please enter the password."
    )
```

### Option 3: Increase the Timeout for Password-Protected PDFs

(Current approach — less ideal but working)

Already implemented in the code — 30-second timeout per PDF parse, 2-minute timeout on frontend fetch.

---

## Technical Details

### Why PyMuPDF Hangs

PyMuPDF (`fitz`) uses native C libraries to handle PDF encryption. For some uncommon encryption schemes:
1. The authentication takes very long (>30s)
2. The library enters an infinite loop
3. The decryption succeeds but the library hangs during text extraction

### Why pdfplumber is More Robust

`pdfplumber` uses different PDF handling libraries:
1. More defensive against malformed PDFs
2. Faster on password-protected documents
3. Better error handling

**Trade-off:** pdfplumber might extract slightly different text formatting, but usually works better on difficult PDFs.

---

## Testing the Fix

After implementing Option 1, test with:

```bash
# Create a test PDF (password-protected)
# Then upload it

# Check logs for:
# "PDF needs password — skipping PyMuPDF, using pdfplumber"
```

---

## If All Else Fails

### Convert the PDF to Text Manually

1. Open the PDF on your computer
2. Copy all text and save as a .txt file
3. **Contact us** with the text file instead — we can build a text-import feature

### Use a Different Statement Format

If available from your custodian:
- Excel export (.xlsx)
- CSV export
- Online web portal import

---

## Summary

| Issue | Solution |
|-------|----------|
| **Correct password but still times out** | Use pdfplumber instead of PyMuPDF (needs code fix) |
| **Password is wrong** | Verify password matches what CAMS/KFintech uses |
| **Don't know password** | Try leaving blank; contact custodian |
| **PDF is corrupted** | Try downloading a fresh statement |
| **Encryption is uncommon** | Manually export to text or CSV |

---

**Last Updated:** May 2026

