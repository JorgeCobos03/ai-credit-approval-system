"""Bounded PDF extraction. Text matching is evidence for review, not identity proof."""
import io
import re
import unicodedata
from datetime import date, datetime
import fitz
from fastapi import HTTPException

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 12

def normalize_text(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

def semantic_similarity(a, b):
    a, b = set(normalize_text(a).split()), set(normalize_text(b).split())
    return len(a & b) / max(len(a), len(b)) if a and b else 0

def extract_document_data(source):
    raw = source if isinstance(source, bytes) else open(source, "rb").read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "El PDF supera el límite de 8 MB.")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(422, "El archivo debe ser un PDF válido.")
    parts, warnings = [], []
    try:
        with fitz.open(stream=raw, filetype="pdf") as doc:
            if doc.needs_pass or not 0 < len(doc) <= MAX_PAGES:
                raise HTTPException(422, "Usa un PDF sin contraseña, de 1 a 12 páginas.")
            for page in doc:
                text = page.get_text()[:20000]
                if len(text.strip()) < 20:
                    try:
                        import pytesseract
                        from PIL import Image
                        if page.rect.width * page.rect.height * 2.25 > 20_000_000:
                            raise ValueError("Oversized page")
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                        text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))), timeout=8)[:20000]
                    except Exception:
                        warnings.append("OCR no disponible o página ilegible. Adjunta un PDF con texto o revisa manualmente.")
                parts.append(text)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "No fue posible leer el PDF.") from None
    text = "\n".join(parts)
    labels = {
        "name": r"(?:nombre(?: del solicitante)?|name)",
        "address": r"(?:direcci[oó]n|domicilio|address)",
        "rfc": r"rfc", "curp": r"curp",
        "monthly_income": r"(?:ingreso mensual|monthly income)",
        "bank_seniority_months": r"(?:antig[uü]edad bancaria|bank seniority)",
        "valid_until": r"(?:vigencia|valid until)",
    }
    data = {}
    for field, label in labels.items():
        match = re.search(r"^\s*" + label + r"\s*:\s*([^\r\n]+)", text, re.I | re.M)
        data[field] = match.group(1).strip()[:400] if match else None
    for field in ("monthly_income", "bank_seniority_months"):
        value = data[field]
        if value:
            match = re.search(r"\d[\d,]*(?:\.\d+)?", value)
            data[field] = float(match.group().replace(",", "")) if match else None
            if field == "bank_seniority_months" and data[field] is not None:
                data[field] = int(data[field])
    data["warnings"] = list(dict.fromkeys(warnings))
    data["method"] = "pdf_text_or_local_ocr"
    data["requires_confirmation"] = True
    return data

def validate_document(application, data):
    reasons = []
    if not data.get("name") or semantic_similarity(application.name, data["name"]) < .8:
        reasons.append("Nombre ausente o con diferencias: confirmar identidad.")
    if not data.get("address") or semantic_similarity(application.address, data["address"]) < .7:
        reasons.append("Domicilio ausente o con diferencias: revisar comprobante.")
    if data.get("rfc") and normalize_text(data["rfc"]) != normalize_text(application.rfc):
        reasons.append("RFC distinto al expediente.")
    if data.get("valid_until"):
        parsed = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(data["valid_until"], fmt).date()
                break
            except ValueError:
                continue
        if not parsed:
            reasons.append("Vigencia ilegible.")
        elif parsed < date.today():
            reasons.append("Documento vencido.")
    reasons.extend(data.get("warnings", []))
    return ("REVIEW", "HIGH", reasons) if reasons else ("MATCHED", "LOW", [])
