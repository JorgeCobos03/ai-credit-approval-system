def evaluate_application(application, score):

    # Regla 1: Score mínimo
    if score < 500:
        return "REJECTED", "Score below minimum threshold (500)"

    # Regla 2: Ingreso mínimo
    if application.monthly_income < 10000:
        return "REJECTED", "Monthly income below required minimum (10000)"

    # Regla 3: Antigüedad bancaria
    if application.bank_seniority_months < 12:
        return "REJECTED", "Bank seniority below 12 months"

    # Regla 4: Lista negra
    if application.is_blacklisted:
        return "REJECTED", "Applicant is in blacklist"

    return "APPROVED", "hola"