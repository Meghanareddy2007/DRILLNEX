"""Document ingestion for demo/authorized documents.
PDF text extraction works with pypdf. OCR is optional and requires Tesseract + pytesseract.
"""
import os, re, uuid
from datetime import datetime
from werkzeug.utils import secure_filename

def extract_text(path):
    ext=os.path.splitext(path)[1].lower()
    if ext==".txt":
        return open(path,"r",encoding="utf-8",errors="ignore").read()
    if ext==".pdf":
        try:
            from pypdf import PdfReader
            reader=PdfReader(path)
            text="\n".join((p.extract_text() or "") for p in reader.pages)
            if text.strip(): return text
        except Exception:
            pass
        # Optional OCR fallback.
        try:
            import pytesseract
            from pdf2image import convert_from_path
            pages=convert_from_path(path, dpi=160, first_page=1, last_page=20)
            return "\n".join(pytesseract.image_to_string(p) for p in pages)
        except Exception:
            return ""
    return ""

def parse_fields(text):
    t=" ".join(text.split())
    def find(p):
        m=re.search(p,t,re.I); return m.group(1) if m else None
    return {
        "well_id":find(r"(?:well|well\s*id)\s*[:#-]?\s*([A-Z]-?\d{2,4})"),
        "depth_m":float(find(r"(?:depth|at)\s*[:#-]?\s*(\d{3,4})\s*m") or 0),
        "formation":find(r"formation\s*[:#-]?\s*([A-Za-z0-9 _-]+?)(?:\.|,|;| incident| cause| action|$)"),
        "mud_weight":find(r"mud\s*weight\s*[:#-]?\s*([\d.]+)"),
        "incident":find(r"(?:incident|event)\s*[:#-]?\s*([A-Za-z _-]+?)(?:\.|,|;| cause| action|$)")
    }

def save_upload(file, folder):
    name=secure_filename(file.filename or "")
    if not name: raise ValueError("Filename is required")
    ext=os.path.splitext(name)[1].lower()
    if ext not in (".pdf",".txt"): raise ValueError("Only PDF and TXT are supported")
    os.makedirs(folder,exist_ok=True)
    stored=f"{uuid.uuid4().hex}_{name}"
    path=os.path.join(folder,stored)
    file.save(path)
    text=extract_text(path)
    return {"document_id":"UP-"+uuid.uuid4().hex[:8].upper(),"filename":name,
            "stored_name":stored,"pages_or_text":"extracted","text_preview":text[:1800],
            "fields":parse_fields(text),"extracted_at":datetime.utcnow().isoformat()+"Z"}
