import json
import os
import urllib.request
import urllib.error

TASKS = {
    "summary": "Redacta un resumen ejecutivo para un analista: capacidad de pago, alertas y próximos pasos.",
    "checklist": "Genera una lista concreta de verificaciones pendientes y preguntas para completar el expediente.",
    "customer_message": "Redacta un borrador cordial para solicitar documentación al cliente, sin prometer aprobación ni inventar motivos."
}

def local_brief(context, task):
    a = context["assessment"]
    if task == "customer_message":
        return "Gracias por tu solicitud. Para continuar con la revisión, confirma tus ingresos y compromisos mensuales y adjunta un comprobante de domicilio vigente. El equipo revisará tu expediente antes de comunicar una decisión."
    checks = [f["label"] + ": " + ("cumple según datos declarados" if f["passed"] else "requiere revisión") for f in a["factors"]]
    if task == "checklist":
        return "\n".join(["Verificar ingresos y deudas con documentos.", "Confirmar identidad y domicilio.", *checks, "Registrar la decisión y su justificación."])
    return (f'Pago estimado: ${a["monthly_payment"]:,.2f} MXN al mes. '
            f'Carga de deuda: {a["debt_to_income"]}%.\n' + "\n".join(checks)
            + "\nLa evaluación es orientativa. La decisión corresponde al responsable autorizado.")

def generate_brief(context, task):
    key = os.getenv("OPENAI_API_KEY", "")
    fallback = {"text": local_brief(context, task), "provider": "local", "generated": False,
                "notice": "Resumen basado en reglas; no es una respuesta de IA generativa."}
    if not key:
        return fallback
    payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), "store": False,
               "max_output_tokens": 800,
               "instructions": "Eres un asistente de operaciones de crédito. Responde en español. Usa solo los hechos JSON. No decidas aprobar o rechazar. No infieras atributos personales, fraude ni probabilidades de impago. Nunca cambies cifras. Señala datos faltantes. Tu salida es un borrador que debe revisar una persona. " + TASKS[task],
               "input": json.dumps(context, ensure_ascii=False)}
    request = urllib.request.Request("https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.load(response)
        text = "\n".join(c.get("text", "") for item in result.get("output", []) if item.get("type") == "message"
                         for c in item.get("content", []) if c.get("type") == "output_text")
        if not text.strip():
            raise ValueError("No text")
        return {"text": text[:12000], "provider": "openai", "generated": True,
                "notice": "Borrador de IA. Verifica las cifras y el contenido antes de utilizarlo."}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        fallback["notice"] = "IA externa no disponible. Se muestra un resumen local verificable."
        return fallback
