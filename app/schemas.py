from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class FinancialInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    monthly_income: float = Field(ge=0.01, le=1_000_000_000)
    bank_seniority_months: int = Field(ge=0, le=1200)
    requested_amount: float = Field(default=50000, ge=0.01, le=100_000_000)
    term_months: int = Field(default=24, ge=1, le=120)
    monthly_debt: float = Field(default=0, ge=0, le=1_000_000_000)
    annual_rate: float = Field(default=24, ge=0, le=100)
    is_blacklisted: bool = False

class ApplicationCreate(FinancialInput):
    name: str = Field(min_length=2, max_length=150)
    rfc: str = Field(pattern=r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
    curp: str = Field(default="", max_length=18)
    gender: str = Field(default="X", max_length=20)
    address: str = Field(min_length=5, max_length=400)

    @field_validator("name", "address", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("rfc", "curp", mode="before")
    @classmethod
    def upper_id(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    status: str
    score: int | None
    rejection_reason: str | None
    monthly_income: float
    bank_seniority_months: int
    is_blacklisted: bool
    address: str | None = None
    document_verified: str | None = None
    risk_flag: str | None = None
    created_at: datetime | None = None

class ReviewInput(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "REVIEW"]
    note: str = Field(min_length=10, max_length=2000)
    version: int = Field(ge=1)

    @field_validator("note", mode="before")
    @classmethod
    def strip_note(cls, value):
        return value.strip() if isinstance(value, str) else value

class CopilotInput(BaseModel):
    task: Literal["summary", "checklist", "customer_message"] = "summary"
