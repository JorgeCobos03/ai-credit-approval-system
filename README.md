# AI Credit Approval System

Microservicio de aprobación de crédito desarrollado con **FastAPI**, que implementa:

- Evaluación de reglas de negocio
- Generación de score de riesgo
- Validación documental con OCR
- Persistencia en base de datos SQLite

El sistema está diseñado como un backend modular con separación clara entre capas de API, lógica de negocio y persistencia.

---

## Uso de IA Agregada

El sistema incorpora técnicas ligeras de Inteligencia Artificial orientadas a validación semántica y explicabilidad de decisiones.

### 1. Validación Semántica de Documento

Se implementa extracción de texto desde el comprobante de domicilio (PDF) mediante procesamiento OCR.

Posteriormente se realiza:

- Normalización de texto (minúsculas, eliminación de acentos y caracteres especiales).
- Comparación semántica básica entre:
  - Nombre del solicitante
  - Dirección ingresada en la solicitud
  - Información extraída del documento

Esto reduce falsos negativos por variaciones de formato y simula controles antifraude utilizados en sistemas financieros reales.

---

### 2. Motor de Reglas con Explicabilidad Automática

El sistema genera una explicación legible del resultado de evaluación crediticia.

Ejemplo:

> “Application REJECTED. Score: 480. Reasons: Monthly income below minimum required (10000); Bank seniority below 12 months.”

O en caso de aprobación:

> “Application APPROVED. Score 720 meets minimum requirement (500). All business rules satisfied.”

Esta funcionalidad cumple con el principio de:

- Transparencia en decisiones
- Trazabilidad
- Preparación para cumplimiento regulatorio

---

### 3. Simulación de Score Crediticio

El endpoint `GET /scorecredito` genera un valor aleatorio entre 300 y 900, simulando un proveedor externo de buró de crédito.

Este diseño permite reemplazar fácilmente la simulación por:

- Modelo de Machine Learning real
- API externa de buró
- Sistema de scoring versionado

---

## Enfoque de IA

El proyecto aplica un enfoque de IA ligera y modular, permitiendo evolucionar hacia:

- Modelos supervisados reales (Logistic Regression, XGBoost)
- Validación avanzada con LLM
- Comparación semántica avanzada de direcciones
- Generación de explicaciones más naturales (Explainable AI)

---

## Arquitectura General

El sistema sigue una arquitectura en capas:

- **API Layer** → FastAPI + Pydantic
- **Business Layer** → Risk Service, Rules Engine, Document Service
- **Persistence Layer** → SQLAlchemy + SQLite

### Diagrama de Arquitectura

![Architecture Diagram](./mermaid-diagram%20(1).png)
---

## Modelo de Datos

Actualmente el sistema utiliza una tabla principal `applications`, que centraliza:

- Información personal
- Información financiera
- Resultado de scoring
- Resultado de reglas
- Estado documental
- Estado final de aprobación

### ERD

![Architecture Diagram](./mermaid-diagram%20(2).png)
---

## Flujo del Proceso

1. Cliente envía solicitud
2. Se persiste en base de datos
3. Se genera score de riesgo
4. Se ejecuta motor de reglas
5. Se valida documento (OCR)
6. Se determina aprobación o rechazo
7. Se retorna respuesta

### Diagrama de Flujo

![Architecture Diagram](./mermaid-diagram%20(3).png)
---

# Decisiones Técnicas

### 1. FastAPI
Elegido por:
- Alto rendimiento (ASGI)
- Tipado fuerte con Pydantic
- Documentación automática (Swagger/OpenAPI)
- Facilidad de escalabilidad

### 2. SQLAlchemy ORM
- Abstracción limpia de la base de datos
- Separación modelo/lógica
- Facilita migración futura a PostgreSQL

### 3. SQLite (MVP)
- Base de datos ligera
- Sin dependencias externas
- Ideal para prototipo y desarrollo local

### 4. Motor de Reglas Separado
El `rules_engine.py` está desacoplado del endpoint:
- Facilita pruebas unitarias
- Permite migrar a motor de reglas más complejo
- Permite integración futura con reglas dinámicas

### 5. Servicio de Riesgo Independiente
`risk_service.py` encapsula el scoring:
- Permite reemplazar el score aleatorio por un modelo ML real
- Mantiene la lógica de negocio limpia

### 6. Validación Documental con OCR
`document_service.py` usa PyMuPDF para:
- Extraer texto
- Validar campos
- Determinar bandera de riesgo

Esto simula una validación bancaria real.

---

# Qué Dejaría Listo para Producción

## 1. Base de Datos

Migrar de SQLite a:
- PostgreSQL
- Con Alembic para migraciones

## 2. Autenticación y Autorización

Agregar:
- JWT
- Roles (admin / analyst / client)
- Rate limiting

## 3. Logging y Auditoría

Agregar:
- Logging estructurado (JSON logs)
- Tabla de auditoría separada
- Trazabilidad por request_id

## 4. Scoring Real

Reemplazar generador aleatorio por:
- Modelo entrenado (XGBoost / Logistic Regression)
- Pipeline versionado
- Feature store

## 5. Validación Documental Avanzada

Integrar:
- OCR robusto (Tesseract o servicio externo)
- Validación antifraude
- API de buró de crédito

## 6. Contenerización

Agregar:
- Dockerfile
- docker-compose
- Variables de entorno
- CI/CD

## 7. Observabilidad

Incluir:
- Prometheus
- Grafana
- Health checks
- Métricas de aprobación

---

## Example Request Payload

El siguiente JSON representa el cuerpo mínimo requerido para crear una solicitud de crédito:

```json
{
  "name": "string",
  "rfc": "string",
  "curp": "string",
  "gender": "string",
  "monthly_income": 0,
  "bank_seniority_months": 0,
  "is_blacklisted": false,
  "address": "string"
}
```

---

# Stack Tecnológico

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- PyMuPDF
- Uvicorn

---

# Ejecutar Localmente

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload