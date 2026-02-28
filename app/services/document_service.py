from PyPDF2 import PdfReader


def extract_document_data(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    # Extracción simple por búsqueda de texto
    name = None
    address = None
    valid_until = None

    lines = text.split("\n")

    for line in lines:
        if "Nombre:" in line:
            name = line.replace("Nombre:", "").strip()
        if "Dirección:" in line:
            address = line.replace("Dirección:", "").strip()
        if "Fecha de Vigencia:" in line:
            valid_until = line.replace("Fecha de Vigencia:", "").strip()

    return {
        "name": name,
        "address": address,
        "valid_until": valid_until,
        "is_blacklisted": False  # Simulación
    }


def validate_document(application, extracted_data):

    # Validar nombre
    if extracted_data["name"] != application.name:
        return "REJECTED", "HIGH"

    # Aquí podrías validar dirección, vigencia, etc.

    return "APPROVED", "LOW"