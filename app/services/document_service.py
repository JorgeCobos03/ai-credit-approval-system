from PyPDF2 import PdfReader
import re


def extract_document_data(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    # Debug
    print("RAW TEXT:", text)

    name = None
    address = None
    valid_until = None

    # Regex más flexible
    name_match = re.search(r"Nombre:\s*(.*)", text)
    address_match = re.search(r"Direcci[oó]n:\s*(.*)", text)
    date_match = re.search(r"Fecha.*?:\s*(.*)", text)

    if name_match:
        name = name_match.group(1).strip()

    if address_match:
        address = address_match.group(1).strip()

    if date_match:
        valid_until = date_match.group(1).strip()

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False
    }