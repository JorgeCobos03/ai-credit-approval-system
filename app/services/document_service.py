import fitz
import re
import unicodedata
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
    Limpia espacios repetidos pero conserva estructura lógica.
    """
    return "\n".join([line.strip() for line in text.splitlines() if line.strip()])


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
    # Fallback OCR si no hay texto
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
    # FORMATO ESTRUCTURADO (Name:, Address:, etc.)
    # =====================================================
    for line in lines:
        lower_line = line.lower()

        if "name:" in lower_line and not name:
            name = line.split(":", 1)[1].strip()

        elif ("address:" in lower_line or "direccion:" in lower_line) and not address:
            address = line.split(":", 1)[1].strip()

        elif ("valid until:" in lower_line or "vigencia:" in lower_line) and not valid_until:
            valid_until = line.split(":", 1)[1].strip()

    # =====================================================
    # Fallback inteligente si no encontró campos
    # =====================================================

    full_text = normalize_text(text)

    # ---- Nombre fallback (dos palabras capitalizadas)
    if not name:
        name_match = re.search(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", text)
        if name_match:
            name = name_match.group().strip()

    # ---- Dirección fallback (línea con número y calle)
    if not address:
        for line in lines:
            if re.search(r"\d+", line) and any(
                word in normalize_text(line)
                for word in ["calle", "av", "avenida", "col", "cp"]
            ):
                address = line.strip()
                break

    # ---- Fecha fallback (ISO)
    if not valid_until:
        iso_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if iso_match:
            valid_until = iso_match.group()

    # ---- Fecha fallback mexicana
    if not valid_until:
        mx_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
        if mx_match:
            valid_until = mx_match.group()

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

    extracted_name = extracted_data.get("name")

    if not extracted_name:
        return "REJECTED", "HIGH"

    normalized_doc_name = normalize_text(extracted_name)
    normalized_app_name = normalize_text(application.name)

    # Permitir coincidencia parcial
    if normalized_app_name not in normalized_doc_name:
        return "REJECTED", "HIGH"

    return "APPROVED", "LOW"