def evaluate_application(application, score):
    reasons = []

    if score < 500:
        reasons.append("Score below minimum threshold (500)")

    if application.monthly_income < 10000:
        reasons.append("Monthly income below required minimum (10000)")

    if application.bank_seniority < 12:
        reasons.append("Bank seniority below required minimum (12 months)")

    if reasons:
        return "REJECTED", reasons

    return "APPROVED", ["All rules passed"]