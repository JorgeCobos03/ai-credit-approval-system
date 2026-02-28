def evaluate_application(application, score):

    reasons = []

    if score < 500:
        reasons.append("Score below minimum threshold (500)")

    if application.monthly_income < 10000:
        reasons.append("Monthly income below minimum required (10000)")

    if application.bank_seniority_months < 12:
        reasons.append("Bank seniority below 12 months")

    if application.is_blacklisted:
        reasons.append("Applicant is blacklisted")

    if reasons:
        return "REJECTED", reasons

    return "APPROVED", []