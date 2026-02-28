# AI Credit Approval System

Microservicio de aprobación de crédito desarrollado con **FastAPI**, que implementa:

- Evaluación de reglas de negocio
- Generación de score de riesgo
- Validación documental con OCR
- Persistencia en base de datos SQLite

El sistema está diseñado como un backend modular con separación clara entre capas de API, lógica de negocio y persistencia.

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