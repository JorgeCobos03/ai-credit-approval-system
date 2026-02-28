import fitz
import re
from pdf2image import convert_from_path
import pytesseract


def extract_document_data(file_path):

    # ----------------------
    # 1. Extraer texto normal
    # ----------------------
    text = ""
    doc = fitz.open(file_path)

    for page in doc:
        text += page.get_text()

    # Si no hay texto → OCR
    if not text.strip():
        pages = convert_from_path(file_path)
        for page in pages:
            text += pytesseract.image_to_string(page)

    print("======= TEXTO EXTRAIDO =======")
    print(text)
    print("======= FIN TEXTO =======")

    # ----------------------
    # Limpieza
    # ----------------------
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    name = None
    address = None
    valid_until = None

    # ----------------------
    # Detectar nombre (línea mayúsculas larga)
    # ----------------------
    for line in lines:
        if line.isupper() and len(line.split()) >= 2 and not any(char.isdigit() for char in line):
            name = line
            break

    # ----------------------
    # Detectar dirección (línea con número)
    # ----------------------
    for line in lines:
        if re.search(r"\d+", line) and any(word in line.lower() for word in ["calle", "col", "avenida", "av", "cp"]):
            address = line
            break

    # ----------------------
    # Detectar fecha
    # ----------------------
    date_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    if date_match:
        valid_until = date_match.group()

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }