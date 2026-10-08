import math

POLICY_VERSION = "affordability-v2.0"

def assess(data):
    rate = data.annual_rate / 1200
    discount = -math.expm1(-data.term_months * math.log1p(rate))
    payment = (data.requested_amount * rate / discount
               if rate else data.requested_amount / data.term_months)
    ratio = (payment + data.monthly_debt) / data.monthly_income
    capacity = max(0, data.monthly_income * .35 - data.monthly_debt)
    amount = capacity * discount / rate if rate else capacity * data.term_months
    factors = [
        {"label": "Carga mensual de deuda ≤ 35%", "passed": ratio <= .35, "detail": f"{ratio:.1%} del ingreso mensual"},
        {"label": "Ingreso mínimo de $10,000 MXN", "passed": data.monthly_income >= 10000, "detail": f"${data.monthly_income:,.2f} MXN declarados"},
        {"label": "Antigüedad bancaria ≥ 12 meses", "passed": data.bank_seniority_months >= 12, "detail": f"{data.bank_seniority_months} meses declarados"},
        {"label": "Sin alerta interna reportada", "passed": not data.is_blacklisted, "detail": "Alerta declarada; no representa consulta a un buró"},
    ]
    score = round(max(0, min(100, 100 - max(0, ratio - .15) * 120
                     - (15 if data.monthly_income < 10000 else 0)
                     - (15 if data.bank_seniority_months < 12 else 0)
                     - (40 if data.is_blacklisted else 0))))
    reasons = [f["label"] for f in factors if not f["passed"]]
    return {"policy_version": POLICY_VERSION, "score": score,
            "score_label": "Índice interno de capacidad, no score de buró",
            "recommendation": "REVIEW" if reasons else "ELIGIBLE",
            "risk": "HIGH" if data.is_blacklisted or ratio > .5 else "MEDIUM" if reasons else "LOW",
            "monthly_payment": round(payment, 2), "debt_to_income": round(ratio * 100, 2),
            "total_payment": round(payment * data.term_months, 2),
            "max_amount": round(amount, 2), "available_monthly": round(capacity, 2),
            "factors": factors, "reasons": reasons,
            "notice": "Estimación con tasa fija, sin comisiones ni seguros. Requiere verificación documental y decisión humana."}
