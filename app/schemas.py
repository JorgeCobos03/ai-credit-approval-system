from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApplicationCreate(BaseModel):
    name: str
    rfc: str
    curp: str
    gender: str
    monthly_income: float
    bank_seniority_months: int
    is_blacklisted: bool = False
    address: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: int
    name: str
    status: str
    score: Optional[int]
    rejection_reason: Optional[str]
    monthly_income: float
    bank_seniority_months: int
    is_blacklisted: bool
    address: Optional[str] = None
    document_verified: Optional[str] = None
    risk_flag: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
