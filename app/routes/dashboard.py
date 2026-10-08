from app.clock import utcnow
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from app.auth import require_user
from app.database import get_db
from app.models import Application, CaseAnalysis
router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_user)])

@router.get("/metrics")
def get_metrics(db=Depends(get_db)):
    counts = dict(db.query(Application.status, func.count(Application.id)).group_by(Application.status).all())
    total = sum(counts.values())
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    series = []
    for offset in range(6, -1, -1):
        day = start - timedelta(days=offset)
        count = db.query(Application).filter(Application.created_at >= day, Application.created_at < day+timedelta(days=1)).count()
        series.append({"date": day.date().isoformat(), "count": count})
    volume = db.query(func.sum(CaseAnalysis.requested_amount)).scalar() or 0
    pending_docs = db.query(Application).filter(Application.document_verified != "MATCHED").count()
    return {"total_applications": total, "total_applications_today": series[-1]["count"],
            "approved": counts.get("APPROVED", 0), "rejected": counts.get("REJECTED", 0),
            "review": counts.get("REVIEW", 0)+counts.get("PENDING", 0),
            "approved_percentage": round(counts.get("APPROVED", 0)/total*100, 1) if total else 0,
            "requested_volume": volume, "pending_documents": pending_docs, "daily": series,
            "timezone": "UTC"}
