# CreditOS · Operaciones de crédito

Mesa de análisis de crédito con FastAPI, SQLAlchemy y una interfaz responsive en español. Incluye expedientes, análisis reproducible de capacidad, documentos, revisión humana y copiloto opcional con OpenAI.

**Web:** https://ai-credit-approval-system.onrender.com

## Qué hace

- Dashboard con métricas globales, actividad de siete días (UTC) y bandeja paginada con búsqueda y filtros.
- Alta de solicitudes con monto, plazo, ingreso, deuda, antigüedad bancaria y tasa nominal anual.
- Simulación de amortización a tasa fija; cuota, carga mensual de deuda y monto orientativo a 35% de capacidad. No incluye comisiones ni seguros.
- Extracción de campos etiquetados de PDF (8 MB / 12 páginas), con confirmación humana. OCR local opcional si Tesseract está instalado. No conserva archivos ni imprime su contenido.
- Comparación documental contra nombre, domicilio, RFC y vigencia cuando existe. Una coincidencia textual **no verifica autenticidad ni ausencia de fraude**.
- Revisión por administrador, justificación obligatoria, control optimista de concurrencia y bitácora.
- Exportación CSV de la selección completa, con protección ante fórmulas de hoja de cálculo.
- Sesiones HttpOnly de ocho horas, cierre con revocación, protección CSRF y límites de solicitudes.
- Demo pública con datos ficticios en el navegador. No lee la base de datos real.

## IA y límites del análisis

El copiloto dispone de tres tareas: resumen ejecutivo, lista de verificaciones y borrador para el cliente. Usa OpenAI Responses API, con `store: false`, solo si existe `OPENAI_API_KEY`. El proveedor recibe indicadores financieros y estados mediante una lista explícita de campos: **no recibe nombre, RFC, CURP, domicilio, texto del PDF ni notas de revisión**. La organización debe autorizar este tratamiento antes de activar la integración.

El modelo se configura con `OPENAI_MODEL` (predeterminado `gpt-4.1-mini`). Si no hay clave o falla el proveedor, se devuelve un resumen determinista identificado como local. No se presenta ese fallback como IA generativa. La integración tiene timeout, límite de salida y diez solicitudes por usuario cada cinco minutos.

La política `affordability-v2.0` es una **heurística no entrenada ni validada para predecir impago**. Sustituye el score aleatorio anterior por un índice interno de 0 a 100 y factores verificables. Nombre, RFC, CURP y género no intervienen en el cálculo. Los umbrales son de ejemplo (35% de carga, $10,000 de ingreso, 12 meses de antigüedad): deben adaptarse y validarse por la empresa. Todas las solicitudes nuevas quedan en revisión; el sistema no aprueba ni rechaza automáticamente.

## Ejecutar localmente

Requiere Python 3.13.

```powershell
python -m venv venv
venv/Scripts/python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Edita .env y define una contraseña larga y única en APP_PASSWORD.
venv/Scripts/python -m uvicorn app.main:app --reload
```

En macOS/Linux activa el entorno y usa `python` y `uvicorn`.
Abre http://127.0.0.1:8000. Usuarios disponibles:

| Usuario | Variable | Permisos |
| --- | --- | --- |
| admin | APP_PASSWORD | Crear, consultar, documentos, copiloto, exportar y decidir |
| analyst | ANALYST_PASSWORD | Crear, consultar, documentos, copiloto y exportar |

Sin credenciales configuradas, el acceso privado queda cerrado y la demo sigue disponible. No hay contraseñas predeterminadas. Las contraseñas de las cuentas de servicio deben tener al menos 12 caracteres. El espacio corresponde a **una sola organización**, sin aislamiento multiempresa.

### Cuentas individuales para el equipo

Usa `python scripts/password_hash.py` para generar hashes PBKDF2-SHA256 con 600,000 iteraciones y sal aleatoria, sin imprimir la contraseña. Define `APP_USERS_JSON` en el servidor con este formato:

```json
{"ana":{"role":"admin","password_hash":"HASH_GENERADO"},"luis":{"role":"analyst","password_hash":"OTRO_HASH_GENERADO"}}
```

Esta configuración sustituye las cuentas compartidas. La bitácora identifica a cada usuario. Quitar un usuario del JSON revoca su acceso; los cambios de rol se aplican a sus sesiones existentes. Una configuración inválida cierra el acceso. SSO/MFA y gestión de usuarios mediante interfaz no están incluidos. Tras rotar una contraseña, revoca las sesiones correspondientes en la base de datos o espera su vencimiento de ocho horas.

## Render y publicación automática

El repositorio incluye `render.yaml` y GitHub Actions. La rama de despliegue es `main`; el blueprint usa `autoDeployTrigger: checksPass` y `/health`.

**Publicar un archivo render.yaml no cambia por sí solo un servicio que no está administrado por Blueprints.** Para un servicio existente confirma en Render: repositorio correcto, rama main, Auto-Deploy habilitado, build `pip install -r requirements.txt` y start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Si adoptas el blueprint, revisa la configuración antes de sincronizar.

Variables en Render:

| Variable | Uso |
| --- | --- |
| APP_PASSWORD | Obligatoria para habilitar el espacio privado |
| ANALYST_PASSWORD | Opcional, acceso de analista |
| APP_USERS_JSON | Opcional, cuentas individuales con hashes y roles; reemplaza las cuentas de servicio |
| DATABASE_URL | PostgreSQL persistente recomendado |
| COOKIE_SECURE | true en HTTPS; Render lo activa también por detección de entorno |
| OPENAI_API_KEY | Opcional: activa generación externa; nunca se entrega al frontend |
| OPENAI_MODEL | Modelo disponible para tu cuenta de API |
| PYTHON_VERSION | 3.13.14 |

No uses SQLite en el disco efímero de Render con datos reales. Configura PostgreSQL antes de cargar expedientes, o monta un disco persistente y usa SQLite con una sola instancia. No cambies `DATABASE_URL` sin respaldar y migrar los datos existentes: cambiar la URL **no copia los expedientes**.

El runtime nativo procesa PDFs con texto. Para OCR de documentos escaneados instala Tesseract en tu infraestructura o usa el Dockerfile incluido. Si OCR no está disponible, se muestra una advertencia y se exige revisión; no se da el documento por válido.

### Docker con OCR

```bash
docker build -t creditos .
docker run --env-file .env -e DATABASE_URL=sqlite:////data/credit.db -p 8000:8000 -v creditos-data:/data creditos
```

El contenedor funciona como usuario sin privilegios. No incluye archivos .env ni bases locales.

## Persistencia y compatibilidad

La tabla original `applications` se conserva. Las nuevas tablas son `case_analyses`, `audit_events`, `login_sessions` y `rate_limits`; el inicio crea únicamente tablas ausentes. Los expedientes históricos conservan su decisión y su score anterior, pero se etiquetan como históricos; para evaluarlos con capacidad se crea un nuevo caso. La versión 2 cambia deliberadamente el contrato de listado a `{items,total,page,page_size}`.

Antes de actualizar una instalación con datos reales, respalda la base. La creación aditiva sirve para la transición de este esquema; futuras alteraciones de columnas requieren migraciones versionadas. Los PDFs históricos en storage/uploads no se eliminan ni se publican: aplica la política de retención de tu organización.

## API

Swagger: `/docs`. Los datos requieren una cookie de sesión válida.
En escrituras autenticadas incluye `X-Credit-Request: 1`.

- `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET/POST /applications/`
- `GET /applications/{id}` (incluye bitácora)
- `POST /applications/extract-document` (prefill que debe confirmarse)
- `POST /applications/{id}/documents`
- `POST /applications/{id}/review` (admin; versión actual y motivo)
- `POST /applications/{id}/copilot` (`summary`, `checklist`, `customer_message`)
- `GET /applications/export.csv`
- `POST /simulate`
- `GET /dashboard/metrics`, `GET /health`, `GET /config`

La creación automática `/applications/from-document` se retiró (410) para no usar información extraída sin confirmación. `/scorecredito` describe la política; ya no genera valores aleatorios.

## Pruebas

```bash
python -m unittest discover -v
node --check app/static/app.js
```

Las pruebas usan SQLite temporal en memoria y no modifican la base de desarrollo. Cubren acceso, permisos, CSRF, revocación, límites, validación, cálculo determinista, documentos, revisión, concurrencia, métricas, paginación, CSV y contratos del copiloto con proveedor simulado. GitHub Actions también ejecuta las pruebas con PostgreSQL.

La integración OpenAI se prueba con mocks: una llamada real requiere clave y presupuesto. El sistema no integra buró, KYC, firma, desembolsos o verificación antifraude externa. Para producción empresarial deben configurarse cuentas individuales, recuperación y respaldos probados, monitoreo, gestión de retención, validación del modelo/política y evaluación de seguridad; SSO/MFA según los requisitos de la empresa. La bitácora es persistente, pero no es un registro inmutable frente al administrador de la base.

## Documentación de integración

- [OpenAI Responses y generación de texto](https://developers.openai.com/api/docs/guides/text)
- [Render Blueprint](https://render.com/docs/blueprint-spec)
- [Despliegues automáticos Render](https://render.com/docs/deploys)

Licencia: MIT.
