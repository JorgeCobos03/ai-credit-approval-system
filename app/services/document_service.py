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
    """
    Elimina acentos, convierte a minúsculas y limpia espacios.
    """
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_multiline_text(text: str) -> str:
    """
    Limpia espacios repetidos pero conserva líneas.
    """
    return "\n".join(
        [line.strip() for line in text.splitlines() if line.strip()]
    )


def semantic_similarity(a: str, b: str) -> float:
    """
    Similaridad simple basada en intersección de palabras.
    """
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

    # -----------------------------------------
    # Intentar lectura directa PDF
    # -----------------------------------------
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print("Error leyendo PDF:", e)

    # -----------------------------------------
    # OCR fallback si no hay texto
    # -----------------------------------------
    if not text.strip():
        try:
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page)
        except Exception as e:
            print("Error usando OCR:", e)

    print("======= TEXTO EXTRAIDO =======")
    print(text)
    print("======= FIN TEXTO =======")

    text = clean_multiline_text(text)
    lines = text.split("\n")

    name = None
    address = None
    valid_until = None

    # =====================================================
    # EXTRACCIÓN ESTRUCTURADA (PRIORIDAD ALTA)
    # =====================================================

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

    # =====================================================
    # FALLBACK INTELIGENTE (tu lógica original intacta)
    # =====================================================

    noise_words = ["utility", "bill", "proof", "company", "address"]

    if not name:
        for line in lines:
            normalized_line = normalize_text(line)

            if any(word in normalized_line for word in noise_words):
                continue

            if re.search(r"\d", line):
                continue

            words = line.split()
            if len(words) < 2:
                continue

            if re.match(r"^[A-Z][a-z]+\s[A-Z][a-z]+$", line.strip()):
                name = line.strip()
                break

    if not address:
        for line in lines:
            if re.search(r"\d+", line) and any(
                keyword in normalize_text(line)
                for keyword in ["calle", "av", "avenida", "col", "cp"]
            ):
                address = line.strip()
                break

    if not valid_until:
        valid_match = re.search(
            r"(valid until|vigencia)[^\d]*(\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        )
        if valid_match:
            valid_until = valid_match.group(2)

    if not valid_until:
        mx_match = re.search(
            r"(valid until|vigencia)[^\d]*(\d{2}/\d{2}/\d{4})",
            text,
            re.IGNORECASE,
        )
        if mx_match:
            valid_until = mx_match.group(2)

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
    extracted_valid_until = extracted_data.get("valid_until")

    # Validación nombre
    if not extracted_name:
        reasons.append("Document name not found")
    elif normalize_text(application.name) not in normalize_text(extracted_name):
        reasons.append("Document name does not match application name")

    # Validación semántica dirección
    if hasattr(application, "address") and application.address and extracted_address:
        similarity = semantic_similarity(application.address, extracted_address)
        if similarity < 0.6:
            reasons.append("Address does not match semantically")
    else:
        reasons.append("Address missing in document")

    # Documento vencido
    if extracted_valid_until:
        try:
            valid_date = datetime.strptime(extracted_valid_until, "%Y-%m-%d")
            if valid_date < datetime.now():
                reasons.append("Document expired")
        except Exception:
            pass

    if reasons:
        return "REJECTED", "HIGH", reasons

    return "APPROVED", "LOW", []