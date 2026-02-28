import fitz
import re
from pdf2image import convert_from_path
import pytesseract


def extract_document_data(file_path: str):

    text = ""

    # ---------------------------------
    # Intentar extracción directa
    # ---------------------------------
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print("Error leyendo PDF con PyMuPDF:", e)

    # ---------------------------------
    # Si no hay texto → usar OCR
    # ---------------------------------
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

    # ---------------------------------
    # Limpieza básica
    # ---------------------------------
    text = re.sub(r"\s+", " ", text)  # eliminar saltos múltiples
    text = text.strip()

    name = None
    address = None
    valid_until = None

    # ---------------------------------
    # FORMATO ESTRUCTURADO (tu PDF)
    # ---------------------------------
    name_match = re.search(r"Name:\s*(.+)", text, re.IGNORECASE)
    address_match = re.search(r"Address:\s*(.+)", text, re.IGNORECASE)
    valid_match_iso = re.search(r"Valid Until:\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)

    if name_match:
        name = name_match.group(1).strip()

    if address_match:
        address = address_match.group(1).strip()

    if valid_match_iso:
        valid_until = valid_match_iso.group(1).strip()

    # ---------------------------------
    # Fallback para formatos distintos
    # ---------------------------------
    if not name:
        lines = text.split(" ")
        possible_name = re.search(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", text)
        if possible_name:
            name = possible_name.group()

    if not address:
        possible_address = re.search(
            r"(Av\.?|Avenida|Calle)\s.+?\d+.*?(?=City|Postal|Issue|Valid|$)",
            text,
            re.IGNORECASE
        )
        if possible_address:
            address = possible_address.group().strip()

    if not valid_until:
        # Intentar formato DD/MM/YYYY
        date_match_alt = re.search(r"\d{2}/\d{2}/\d{4}", text)
        if date_match_alt:
            valid_until = date_match_alt.group()

    # ---------------------------------
    # Normalización final
    # ---------------------------------
    if name:
        name = name.strip()

    if address:
        address = address.strip()

    if valid_until:
        valid_until = valid_until.strip()

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }