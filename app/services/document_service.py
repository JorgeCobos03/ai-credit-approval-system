import fitz
import re
import unicodedata
from datetime import datetime
from pdf2image import convert_from_path
import pytesseract


# =====================================================
# UTILIDADES
# =====================================================

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_multiline_text(text: str) -> str:
    return "\n".join(
        [line.strip() for line in text.splitlines() if line.strip()]
    )


def semantic_similarity(a: str, b: str) -> float:
    set_a = set(normalize_text(a).split())
    set_b = set(normalize_text(b).split())

    if not set_a or not set_b:
        return 0.0

    intersection = set_a.intersection(set_b)
    return len(intersection) / max(len(set_a), len(set_b))


# =====================================================
# EXTRAER INFORMACIÓN DEL DOCUMENTO
# =====================================================

def extract_document_data(file_path: str):

    text = ""

    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    except Exception:
        pass

    if not text.strip():
        try:
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page)
        except Exception:
            pass

    text = clean_multiline_text(text)
    lines = text.split("\n")

    name = None
    address = None
    valid_until = None

    for line in lines:
        lower_line = line.lower()

        if lower_line.startswith("name:") and not name:
            name = line.split(":", 1)[1].strip()

        elif (
            lower_line.startswith("address:")
            or lower_line.startswith("direccion:")
        ) and not address:
            address = line.split(":", 1)[1].strip()

        elif (
            lower_line.startswith("valid until:")
            or lower_line.startswith("vigencia:")
        ) and not valid_until:
            valid_until = line.split(":", 1)[1].strip()

    # Fallback fecha ISO
    if not valid_until:
        match = re.search(
            r"(valid until|vigencia)[^\d]*(\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        )
        if match:
            valid_until = match.group(2)

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }


# =====================================================
# VALIDAR DOCUMENTO CONTRA SOLICITUD
# =====================================================

def validate_document(application, extracted_data):

    reasons = []

    extracted_name = extracted_data.get("name")
    extracted_address = extracted_data.get("address")
    extracted_valid = extracted_data.get("valid_until")

    # Validación nombre
    if not extracted_name:
        reasons.append("Document name not found")
    elif normalize_text(application.name) not in normalize_text(extracted_name):
        reasons.append("Document name does not match application name")

    # Validación dirección semántica
    if application.address and extracted_address:
        similarity = semantic_similarity(
            application.address,
            extracted_address
        )
        if similarity < 0.6:
            reasons.append("Address does not match semantically")
    else:
        reasons.append("Address missing in document")

    # Documento vencido
    if extracted_valid:
        try:
            valid_date = datetime.strptime(extracted_valid, "%Y-%m-%d")
            if valid_date < datetime.now():
                reasons.append("Document expired")
        except Exception:
            pass

    if reasons:
        return "REJECTED", "HIGH", reasons

    return "APPROVED", "LOW", []