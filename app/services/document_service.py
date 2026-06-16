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
    rfc = None
    curp = None
    gender = None
    address = None
    valid_until = None
    monthly_income = None
    bank_seniority_months = None
    is_blacklisted = False

    # =====================================================
    # EXTRACCIÓN ESTRUCTURADA (PRIORIDAD ALTA)
    # =====================================================

    for line in lines:
        lower_line = line.lower()

        if lower_line.startswith("name:") and not name:
            name = line.split(":", 1)[1].strip()

        elif lower_line.startswith("nombre:") and not name:
            name = line.split(":", 1)[1].strip()

        elif lower_line.startswith("rfc:") and not rfc:
            rfc = line.split(":", 1)[1].strip()

        elif lower_line.startswith("curp:") and not curp:
            curp = line.split(":", 1)[1].strip()

        elif (
            lower_line.startswith("gender:")
            or lower_line.startswith("genero:")
        ) and not gender:
            gender = line.split(":", 1)[1].strip()

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

        elif (
            lower_line.startswith("monthly income:")
            or lower_line.startswith("ingreso mensual:")
        ) and monthly_income is None:
            monthly_income = parse_money(line.split(":", 1)[1])

        elif (
            lower_line.startswith("bank seniority:")
            or lower_line.startswith("antiguedad bancaria:")
            or lower_line.startswith("antigüedad bancaria:")
        ) and bank_seniority_months is None:
            bank_seniority_months = parse_integer(line.split(":", 1)[1])

        elif (
            lower_line.startswith("blacklisted:")
            or lower_line.startswith("lista negra:")
        ):
            is_blacklisted = parse_bool(line.split(":", 1)[1])

    # =====================================================
    # FALLBACK INTELIGENTE (tu lógica original intacta)
    # =====================================================

    if not name:
        name_match = re.search(
            r"(?:name|nombre(?: del solicitante)?)\s*:\s*([^\n]+)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            name = name_match.group(1).strip()

    if not curp:
        curp_match = re.search(
            r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b",
            text,
            re.IGNORECASE,
        )
        if curp_match:
            curp = curp_match.group(0).upper()

    if not rfc:
        rfc_match = re.search(
            r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b",
            text,
            re.IGNORECASE,
        )
        if rfc_match:
            rfc = rfc_match.group(0).upper()

    if not gender:
        gender_match = re.search(
            r"(?:gender|genero|sexo)\s*:\s*([FMX])\b",
            text,
            re.IGNORECASE,
        )
        if gender_match:
            gender = gender_match.group(1).upper()

    if monthly_income is None:
        income_match = re.search(
            r"(?:monthly income|ingreso mensual)[^\d\n]*(\$?\s*[\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if income_match:
            monthly_income = parse_money(income_match.group(1))

    if bank_seniority_months is None:
        seniority_match = re.search(
            r"(?:bank seniority|antig[uü]edad bancaria)[^\d\n]*(\d+)",
            text,
            re.IGNORECASE,
        )
        if seniority_match:
            bank_seniority_months = parse_integer(seniority_match.group(1))

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
        "rfc": rfc,
        "curp": curp,
        "gender": gender,
        "address": address,
        "valid_until": valid_until,
        "monthly_income": monthly_income,
        "bank_seniority_months": bank_seniority_months,
        "is_blacklisted": is_blacklisted
    }


def parse_money(value: str):
    amount = re.sub(r"[^\d.]", "", value or "")
    return float(amount) if amount else None


def parse_integer(value: str):
    amount = re.sub(r"[^\d]", "", value or "")
    return int(amount) if amount else None


def parse_bool(value: str) -> bool:
    return normalize_text(value) in {"true", "yes", "si", "1", "blacklisted"}


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
