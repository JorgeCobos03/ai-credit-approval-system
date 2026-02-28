from PyPDF2 import PdfReader
import re


def extract_document_data(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    # Regex flexible
    name_match = re.search(r"Nombre:\s*(.*)", text)
    address_match = re.search(r"Direcci[oó]n:\s*(.*)", text)
    date_match = re.search(r"Fecha.*?:\s*(.*)", text)

    name = name_match.group(1).strip() if name_match else None
    address = address_match.group(1).strip() if address_match else None
    valid_until = date_match.group(1).strip() if date_match else None

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }


def validate_document(application, extracted_data):

    # Validar nombre
    if extracted_data["name"] != application.name:
        return "REJECTED", "HIGH"

    # Puedes agregar más validaciones aquí
    return "APPROVED", "LOW"