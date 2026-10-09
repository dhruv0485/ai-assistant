# src/parser.py
import pdfplumber
import docx
import re
from pathlib import Path

def extract_text_from_pdf(path: str) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return clean_text(text)

def extract_text_from_docx(path: str) -> str:
    doc = docx.Document(path)
    return clean_text("\n".join([p.text for p in doc.paragraphs]))

def extract_text_from_txt(path: str) -> str:
    return clean_text(Path(path).read_text(encoding="utf-8", errors="ignore"))

def clean_text(text: str) -> str:
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def mask_pii(text: str) -> str:
    """Remove phone numbers and emails for privacy compliance."""
    text = re.sub(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', '[EMAIL]', text, flags=re.IGNORECASE)
    # Mask phones with formats like +91 70205 83122, 7020583122, +91-702-058-3122
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}\b', '[PHONE]', text)
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{9}\b', '[PHONE]', text)
    return text

def parse_resume(path: str) -> str:
    """Main entry — auto-detect format, extract and mask PII."""
    path = str(path).lower()
    if path.endswith(".pdf"):
        text = extract_text_from_pdf(path)
    elif path.endswith(".docx"):
        text = extract_text_from_docx(path)
    else:
        text = extract_text_from_txt(path)
    return mask_pii(text)

def parse_jd(text_or_path: str) -> str:
    """JD can be raw text or a file path (PDF, DOCX, TXT)."""
    p = Path(text_or_path)
    if p.exists() and p.is_file():
        path_str = str(text_or_path).lower()
        if path_str.endswith(".pdf"):
            return extract_text_from_pdf(str(p))
        elif path_str.endswith(".docx"):
            return extract_text_from_docx(str(p))
        else:
            return clean_text(p.read_text(encoding="utf-8", errors="ignore"))
    return clean_text(text_or_path)
