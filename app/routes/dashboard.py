from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.database import SessionLocal
from app import models

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    if not hasattr(models.Application, "created_at"):
        return {"error": "Model not updated properly"}

    today = date.today()

    total_today = db.query(models.Application).filter(
        func.date(models.Application.created_at) == today
    ).count()

    total = db.query(models.Application).count()

    approved = db.query(models.Application).filter(
        models.Application.status == "APPROVED"
    ).count()

    rejected = db.query(models.Application).filter(
        models.Application.status == "REJECTED"
    ).count()

    approved_percentage = (approved / total * 100) if total > 0 else 0
    rejected_percentage = (rejected / total * 100) if total > 0 else 0

    return {
        "total_applications_today": total_today,
        "total_applications": total,
        "approved_percentage": round(approved_percentage, 2),
        "rejected_percentage": round(rejected_percentage, 2)
    }