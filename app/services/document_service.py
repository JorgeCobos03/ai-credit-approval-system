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
    Limpia espacios repetidos pero conserva líneas.
    """
    return "\n".join(
        [line.strip() for line in text.splitlines() if line.strip()]
    )


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

        # ---- Nombre
        if lower_line.startswith("name:") and not name:
            name = line.split(":", 1)[1].strip()

        # ---- Dirección
        elif (
            lower_line.startswith("address:")
            or lower_line.startswith("direccion:")
        ) and not address:
            address = line.split(":", 1)[1].strip()

        # ---- Fecha válida (NO Issue Date)
        elif (
            lower_line.startswith("valid until:")
            or lower_line.startswith("vigencia:")
        ) and not valid_until:
            valid_until = line.split(":", 1)[1].strip()

    # =====================================================
    # FALLBACK INTELIGENTE
    # =====================================================

    noise_words = ["utility", "bill", "proof", "company", "address"]

    # ---- Nombre fallback (más restrictivo)
    if not name:
        for line in lines:
            normalized_line = normalize_text(line)

            # Excluir encabezados comunes
            if any(word in normalized_line for word in noise_words):
                continue

            # No debe tener números
            if re.search(r"\d", line):
                continue

            # Debe tener al menos 2 palabras
            words = line.split()
            if len(words) < 2:
                continue

            # Patrón típico de nombre propio
            if re.match(r"^[A-Z][a-z]+\s[A-Z][a-z]+$", line.strip()):
                name = line.strip()
                break

    # ---- Dirección fallback
    if not address:
        for line in lines:
            if re.search(r"\d+", line) and any(
                keyword in normalize_text(line)
                for keyword in ["calle", "av", "avenida", "col", "cp"]
            ):
                address = line.strip()
                break

    # ---- Fecha fallback ISO (pero ignorando Issue Date)
    if not valid_until:
        valid_match = re.search(
            r"(valid until|vigencia)[^\d]*(\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        )
        if valid_match:
            valid_until = valid_match.group(2)

    # ---- Fecha fallback alternativa mexicana
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

    extracted_name = extracted_data.get("name")

    if not extracted_name:
        return "REJECTED", "HIGH"

    normalized_doc_name = normalize_text(extracted_name)
    normalized_app_name = normalize_text(application.name)

    # Coincidencia exacta o contenida
    if normalized_app_name not in normalized_doc_name:
        return "REJECTED", "HIGH"

    return "APPROVED", "LOW"