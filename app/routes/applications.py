import csv
import io
import json
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_, update
from app import models, schemas
from app.auth import require_user, limit
from app.database import get_db
from app.services.risk_service import assess
from app.services.document_service import MAX_BYTES, extract_document_data, validate_document
from app.services.ai_service import generate_brief

router = APIRouter(prefix="/applications", tags=["Applications"], dependencies=[Depends(require_user)])

def event(db, app_id, user, action, detail):
    db.add(models.AuditEvent(application_id=app_id, actor=user.actor, action=action,
                             detail=json.dumps(detail, ensure_ascii=False)))

def find_case(db, case_id):
    row = db.get(models.Application, case_id)
    if not row:
        raise HTTPException(404, "Expediente no encontrado.")
    return row

def query_cases(db, search="", status=""):
    query = db.query(models.Application)
    if search:
        query = query.filter(or_(models.Application.name.contains(search, autoescape=True),
                                 models.Application.rfc.contains(search.upper(), autoescape=True)))
    if status:
        query = query.filter(models.Application.status == status)
    return query

def serialize(db, row):
    data = schemas.ApplicationResponse.model_validate(row).model_dump(mode="json")
    detail = db.get(models.CaseAnalysis, row.id)
    data.update({"assessment": json.loads(detail.assessment) if detail else None,
                 "requested_amount": detail.requested_amount if detail else None,
                 "term_months": detail.term_months if detail else None,
                 "monthly_debt": detail.monthly_debt if detail else None,
                 "annual_rate": detail.annual_rate if detail else None,
                 "version": detail.version if detail else None})
    return data

@router.get("/")
def list_applications(search: str = Query("", max_length=100), status: str = Query("", max_length=20),
                      page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), db=Depends(get_db)):
    query = query_cases(db, search, status)
    total = query.count()
    rows = query.order_by(models.Application.created_at.desc(), models.Application.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {"items": [serialize(db, row) for row in rows], "total": total, "page": page, "page_size": page_size}

@router.get("/export.csv")
def export(search: str = Query("", max_length=100), status: str = Query("", max_length=20),
           db=Depends(get_db), user=Depends(require_user)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Solicitante", "Estado", "Ingreso mensual MXN", "Documento", "Fecha UTC"])
    count = 0
    for row in query_cases(db, search, status).order_by(models.Application.id).yield_per(200):
        name = row.name
        if name.lstrip().startswith(("=", "+", "-", "@")):
            name = "'" + name
        writer.writerow([row.id, name, row.status, row.monthly_income, row.document_verified, row.created_at.isoformat()])
        count += 1
    event(db, None, user, "EXPORT", {"records": count})
    db.commit()
    return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="creditos.csv"'})

@router.post("/", status_code=201)
def create_application(data: schemas.ApplicationCreate, db=Depends(get_db), user=Depends(require_user)):
    limit(db, "create:" + user.actor, 30)
    result = assess(data)
    values = data.model_dump(exclude={"requested_amount", "term_months", "monthly_debt", "annual_rate"})
    row = models.Application(**values, score=result["score"], status="REVIEW", risk_flag=result["risk"],
                             rejection_reason=" | ".join(result["reasons"]) or None)
    db.add(row)
    db.flush()
    db.add(models.CaseAnalysis(application_id=row.id, requested_amount=data.requested_amount, term_months=data.term_months,
                              monthly_debt=data.monthly_debt, annual_rate=data.annual_rate, assessment=json.dumps(result)))
    event(db, row.id, user, "CREATED", {"policy_version": result["policy_version"], "recommendation": result["recommendation"]})
    db.commit()
    db.refresh(row)
    return serialize(db, row)

@router.post("/extract-document")
def extract(file: UploadFile = File(...), db=Depends(get_db), user=Depends(require_user)):
    limit(db, "document:" + user.actor, 10)
    return extract_document_data(file.file.read(MAX_BYTES + 1))

@router.post("/from-document", status_code=410)
def old_document_flow():
    raise HTTPException(410, "Primero extrae con /applications/extract-document, confirma los datos y crea la solicitud.")

@router.get("/{application_id}")
def get_application(application_id: int, db=Depends(get_db)):
    row = find_case(db, application_id)
    data = serialize(db, row)
    data["audit"] = [{"actor": e.actor, "action": e.action, "detail": json.loads(e.detail), "created_at": e.created_at.isoformat()}
                     for e in db.query(models.AuditEvent).filter_by(application_id=application_id).order_by(models.AuditEvent.id.desc()).limit(100)]
    return data

@router.post("/{application_id}/documents")
def upload_document(application_id: int, file: UploadFile = File(...), db=Depends(get_db), user=Depends(require_user)):
    limit(db, "document:" + user.actor, 10)
    row = find_case(db, application_id)
    detail = db.get(models.CaseAnalysis, row.id)
    if not detail:
        raise HTTPException(409, "Expediente histórico: crea una nueva evaluación con monto y plazo para continuar.")
    version = detail.version
    data = extract_document_data(file.file.read(MAX_BYTES + 1))
    verified, risk, reasons = validate_document(row, data)
    changed = db.execute(update(models.CaseAnalysis).where(models.CaseAnalysis.application_id == row.id,
                         models.CaseAnalysis.version == version).values(version=version+1))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "El expediente cambió durante la extracción. Actualiza e intenta de nuevo.")
    row.document_verified = verified
    row.status = "REVIEW"
    row.risk_flag = "HIGH" if risk == "HIGH" else json.loads(detail.assessment)["risk"]
    # Keep financial reasons; documents must not erase financial findings.
    financial = json.loads(detail.assessment)["reasons"]
    row.rejection_reason = " | ".join(financial + reasons) or None
    event(db, row.id, user, "DOCUMENT_CHECKED", {"result": verified, "reasons": reasons, "method": data["method"]})
    db.commit()
    return {"document_verified": verified, "reasons": reasons, "application": serialize(db, row)}

@router.post("/{application_id}/review")
def review(application_id: int, data: schemas.ReviewInput, db=Depends(get_db), user=Depends(require_user)):
    if user.role != "admin":
        raise HTTPException(403, "Solo el responsable admin puede registrar decisiones.")
    row = find_case(db, application_id)
    detail = db.get(models.CaseAnalysis, row.id)
    if not detail:
        raise HTTPException(409, "Expediente histórico: se requiere una nueva evaluación.")
    if data.decision == "APPROVED" and row.document_verified != "MATCHED":
        raise HTTPException(409, "Revisa primero un comprobante coincidente antes de aprobar.")
    changed = db.execute(update(models.CaseAnalysis).where(models.CaseAnalysis.application_id == row.id,
                          models.CaseAnalysis.version == data.version).values(version=data.version+1))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Otro usuario actualizó el expediente. Recarga antes de decidir.")
    previous = row.status
    row.status = data.decision
    event(db, row.id, user, "REVIEWED", {"previous": previous, "decision": data.decision, "note": data.note})
    db.commit()
    return serialize(db, row)

@router.post("/{application_id}/copilot")
def copilot(application_id: int, data: schemas.CopilotInput, db=Depends(get_db), user=Depends(require_user)):
    limit(db, "ai:" + user.actor, 10, 300)
    row = find_case(db, application_id)
    detail = db.get(models.CaseAnalysis, row.id)
    if not detail:
        raise HTTPException(409, "El expediente histórico no tiene una evaluación de capacidad.")
    # Explicit allowlist: no name, RFC, CURP, address, document text or review notes leave the server.
    context = {"assessment": json.loads(detail.assessment), "document_status": row.document_verified,
               "status": row.status, "amount": detail.requested_amount, "term_months": detail.term_months}
    result = generate_brief(context, data.task)
    event(db, row.id, user, "COPILOT", {"task": data.task, "provider": result["provider"]})
    db.commit()
    return result
