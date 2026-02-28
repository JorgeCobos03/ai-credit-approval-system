from pydantic import BaseModel
from typing import Optional

class ApplicationCreate(BaseModel):
    name: str
    rfc: str
    curp: str
    gender: str
    monthly_income: float
    bank_seniority: int

class ApplicationResponse(BaseModel):
    id: int
    name: str
    status: str
    score: Optional[int]
    decision_reason: Optional[str]

    class Config:
        from_attributes = True