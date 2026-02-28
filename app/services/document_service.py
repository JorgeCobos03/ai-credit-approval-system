import random

def extract_document_data(file_path: str):
    """
    Simulación de extracción IA.
    En producción usarías OCR + LLM.
    """
    fake_addresses = [
        "Av. Reforma 123, CDMX",
        "Calle Juarez 456, Monterrey",
        "Blvd. Independencia 789, Guadalajara"
    ]

    return {
        "name": "Maria Lopez",
        "address": random.choice(fake_addresses),
        "valid_until": "2026-12-31"
    }


def validate_document(application, extracted_data):
    """
    Validación semántica simulada.
    """
    risk = "LOW"
    verified = "VERIFIED"

    if extracted_data["name"].lower() != application.name.lower():
        risk = "HIGH"
        verified = "REJECTED"

    return verified, risk