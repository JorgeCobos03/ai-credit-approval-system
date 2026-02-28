import fitz  # PyMuPDF
import re
from pdf2image import convert_from_path
import pytesseract
import os


# -----------------------------
# EXTRAER TEXTO PDF (PyMuPDF)
# -----------------------------
def extract_text_pymupdf(file_path: str) -> str:
    text = ""
    doc = fitz.open(file_path)

    for page in doc:
        text += page.get_text()

    return text


# -----------------------------
# OCR SI NO HAY TEXTO
# -----------------------------
def extract_text_ocr(file_path: str) -> str:
    text = ""
    pages = convert_from_path(file_path)

    for page in pages:
        text += pytesseract.image_to_string(page)

    return text


# -----------------------------
# EXTRACCIÓN PRINCIPAL
# -----------------------------
def extract_document_data(file_path):

    text = extract_text_pymupdf(file_path)

    # Si no encontró texto, usar OCR
    if not text.strip():
        text = extract_text_ocr(file_path)

    # -------------------------
    # Limpieza básica
    # -------------------------
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # -------------------------
    # Regex más robustas
    # -------------------------
    name_match = re.search(r"(Nombre|Titular)[:\s]+([A-Za-zÁÉÍÓÚÑáéíóúñ ]+)", text)
    address_match = re.search(r"(Direcci[oó]n)[:\s]+(.+?)(CP|C\.P\.|Colonia|Municipio)", text)
    date_match = re.search(r"(Vigencia|Fecha.*?)(\d{2}/\d{2}/\d{4})", text)

    name = name_match.group(2).strip() if name_match else None
    address = address_match.group(2).strip() if address_match else None
    valid_until = date_match.group(2).strip() if date_match else None

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }


# -----------------------------
# VALIDACIÓN DOCUMENTO
# -----------------------------
def validate_document(application, extracted_data):

    # Si no extrajo nada -> riesgo alto
    if not extracted_data["name"]:
        return "REJECTED", "HIGH"

    # Comparación flexible (case insensitive)
    if extracted_data["name"].strip().lower() != application.name.strip().lower():
        return "REJECTED", "HIGH"

    return "APPROVED", "LOW"