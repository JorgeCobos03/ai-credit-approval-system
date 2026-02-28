"""
rules_engine.py

Motor de reglas de negocio para evaluación crediticia.
Incluye explicabilidad automática de decisiones.
"""

def generate_explanation(status: str, reasons: list[str], score: int) -> str:
    """
    Genera una explicación legible del resultado de evaluación.
    """

    if status == "APPROVED":
        return (
            f"Application APPROVED. "
            f"Score {score} meets minimum requirement (500). "
            f"All business rules satisfied."
        )

    return (
        f"Application REJECTED. "
        f"Score: {score}. "
        f"Reasons: {'; '.join(reasons)}"
    )


def evaluate_application(application, score):
    """
    Evalúa una solicitud de crédito aplicando reglas de negocio.

    Reglas:
    - Score >= 500
    - Ingreso mensual >= 10000
    - Antigüedad bancaria >= 12 meses
    - No estar en lista negra
    """

    reasons = []

    # Regla 1: Score mínimo
    if score < 500:
        reasons.append("Score below minimum threshold (500)")

    # Regla 2: Ingreso mínimo
    if application.monthly_income < 10000:
        reasons.append("Monthly income below minimum required (10000)")

    # Regla 3: Antigüedad bancaria
    if application.bank_seniority_months < 12:
        reasons.append("Bank seniority below 12 months")

    # Regla 4: Lista negra
    if application.is_blacklisted:
        reasons.append("Applicant is blacklisted")

    # Determinar estado
    if reasons:
        status = "REJECTED"
    else:
        status = "APPROVED"

    # Generar explicación automática
    explanation = generate_explanation(status, reasons, score)

    # Agregamos explicación como última razón informativa
    if explanation:
        reasons.append(explanation)

    return status, reasons