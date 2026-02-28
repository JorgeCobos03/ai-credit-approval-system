from fastapi import APIRouter
from random import randint

router = APIRouter()

@router.get("/scorecredito")
def get_score():
    return {"score": randint(300, 900)}