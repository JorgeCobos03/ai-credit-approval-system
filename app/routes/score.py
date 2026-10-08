from fastapi import APIRouter, Depends
from app.auth import require_user
from app.schemas import FinancialInput
from app.services.risk_service import assess, POLICY_VERSION
router = APIRouter(tags=["Analysis"], dependencies=[Depends(require_user)])

@router.get("/scorecredito")
def score_policy():
    return {"policy_version": POLICY_VERSION, "type": "deterministic_affordability",
            "message": "Usa POST /simulate. No se generan scores aleatorios."}

@router.post("/simulate")
def simulate(data: FinancialInput):
    return assess(data)
