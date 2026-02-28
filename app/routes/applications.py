from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.services.risk_service import generate_credit_score
from app.services.rules_engine import evaluate_application
from app.services.document_service import extract_document_data, validate_document
import shutil
import os

router = APIRouter(
    prefix="/applications",
    tags=["Applications"]
)

# ---------------------------
# DB Dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# CREATE APPLICATION
# ---------------------------
@router.post("/", response_model=schemas.ApplicationResponse)
def create_application(
    application: schemas.ApplicationCreate,
    db: Session = Depends(get_db)
):
    score = generate_credit_score()

    status, rejection_reason = evaluate_application(application, score)

    db_application = models.Application(
        name=application.name,
        rfc=application.rfc,
        curp=application.curp,
        gender=application.gender,
        monthly_income=application.monthly_income,
        bank_seniority_months=application.bank_seniority_months,
        is_blacklisted=application.is_blacklisted,
        status=status,
        score=score,
        rejection_reason=rejection_reason
    )

    db.add(db_application)
    db.commit()
    db.refresh(db_application)

    return db_application


# ---------------------------
# GET APPLICATION
# ---------------------------
@router.get("/{application_id}", response_model=schemas.ApplicationResponse)
def get_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(models.Application).filter(
        models.Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


# ---------------------------
# UPLOAD DOCUMENT
# ---------------------------
@router.post("/{application_id}/documents")
def upload_document(
    application_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    application = db.query(models.Application).filter(
        models.Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    os.makedirs("storage/documents", exist_ok=True)
    file_path = f"storage/documents/{application_id}_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_data = extract_document_data(file_path)
    verified, risk = validate_document(application, extracted_data)

    application.document_path = file_path
    application.document_verified = verified
    application.risk_flag = risk

    if verified == "REJECTED":
        application.status = "REJECTED"
        application.rejection_reason = "Document validation failed - Name mismatch or unreadable document"

    db.commit()
    db.refresh(application)

    return {
        "message": "Document uploaded",
        "extracted_data": extracted_data,
        "document_verified": verified,
        "risk_flag": risk,
        "final_status": application.status
    }