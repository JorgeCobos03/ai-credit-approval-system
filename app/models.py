from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from datetime import datetime
from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    # Applicant info
    name = Column(String, nullable=False)
    rfc = Column(String, nullable=False)
    curp = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    address = Column(String, nullable=True)


    # Financial data
    monthly_income = Column(Float, nullable=False)
    bank_seniority_months = Column(Integer, nullable=False)
    is_blacklisted = Column(Boolean, default=False)

    # Decision data
    status = Column(String, default="PENDING")
    score = Column(Integer, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Risk & documents
    document_path = Column(String, nullable=True)
    document_verified = Column(String, default="PENDING")
    risk_flag = Column(String, default="LOW")

    created_at = Column(DateTime, default=datetime.utcnow)