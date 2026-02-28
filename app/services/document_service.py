import fitz
import re
from pdf2image import convert_from_path
import pytesseract


# ==========================================
# EXTRAER INFORMACIÓN DEL DOCUMENTO
# ==========================================
def extract_document_data(file_path: str):

    text = ""

    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print("Error leyendo PDF:", e)

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

    text = re.sub(r"\s+", " ", text).strip()

    name = None
    address = None
    valid_until = None

    name_match = re.search(r"Name:\s*(.+)", text, re.IGNORECASE)
    address_match = re.search(r"Address:\s*(.+)", text, re.IGNORECASE)
    valid_match = re.search(r"Valid Until:\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)

    if name_match:
        name = name_match.group(1).strip()

    if address_match:
        address = address_match.group(1).strip()

    if valid_match:
        valid_until = valid_match.group(1).strip()

    if not valid_until:
        alt_date = re.search(r"\d{2}/\d{2}/\d{4}", text)
        if alt_date:
            valid_until = alt_date.group()

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }


# ==========================================
# VALIDAR DOCUMENTO CONTRA SOLICITUD
# ==========================================
def validate_document(application, extracted_data):

    # Si no se extrajo nombre → rechazar
    if not extracted_data.get("name"):
        return "REJECTED", "HIGH"

    # Comparación case-insensitive
    if extracted_data["name"].strip().lower() != application.name.strip().lower():
        return "REJECTED", "HIGH"

    return "APPROVED", "LOW"