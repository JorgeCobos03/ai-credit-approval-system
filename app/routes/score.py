from fastapi import APIRouter
import random

router = APIRouter(
    prefix="/scorecredito",
    tags=["Score"]
)

@router.get("/")
def get_score():
    score = random.randint(300, 900)
    return {"score": score}