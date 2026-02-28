from pydantic import BaseModel
from typing import Optional


class ApplicationCreate(BaseModel):
    name: str
    rfc: str
    curp: str
    gender: str
    monthly_income: float
    bank_seniority_months: int
    is_blacklisted: bool = False


class ApplicationResponse(BaseModel):
    id: int
    name: str
    status: str
    score: Optional[int]
    rejection_reason: Optional[str]
    monthly_income: float
    bank_seniority_months: int
    is_blacklisted: bool

    class Config:
        from_attributes = True