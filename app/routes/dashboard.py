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

    top_reason = db.query(
        models.Application.rejection_reason,
        func.count(models.Application.id)
    ).filter(
        models.Application.rejection_reason != None
    ).group_by(
        models.Application.rejection_reason
    ).order_by(
        func.count(models.Application.id).desc()
    ).first()

    return {
        "total_applications_today": total_today,
        "total_applications": total,
        "approved_percentage": round((approved / total * 100), 2) if total else 0,
        "rejected_percentage": round((rejected / total * 100), 2) if total else 0,
        "top_rejection_reason": top_reason[0] if top_reason else None
    }