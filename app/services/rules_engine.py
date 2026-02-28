def evaluate_application(application, score):

    reasons = []

    # Regla 1: Score mínimo
    if score < 500:
        reasons.append("Score below minimum threshold (500)")

    # Regla 2: Ingreso mínimo
    if application.monthly_income < 10000:
        reasons.append("Monthly income below required minimum (10000)")

    # Regla 3: Antigüedad bancaria
    if application.bank_seniority_months < 12:
        reasons.append("Bank seniority below 12 months")

    # Regla 4: Lista negra
    if application.is_blacklisted:
        reasons.append("Applicant is in blacklist")

    if reasons:
        return "REJECTED", " | ".join(reasons)

    return "APPROVED", None