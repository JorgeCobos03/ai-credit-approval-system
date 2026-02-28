from sqlalchemy import Column, Integer, String, Float
from app.database import Base
from sqlalchemy import Column, Integer, String, Float, Text
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy import Boolean

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    rfc = Column(String)
    curp = Column(String)
    gender = Column(String)
    monthly_income = Column(Float)
    
    status = Column(String, default="PENDING")
    score = Column(Integer, nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    document_path = Column(String, nullable=True)
    document_verified = Column(String, default="PENDING")
    risk_flag = Column(String, default="LOW")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    monthly_income = Column(Float, nullable=False)
    bank_seniority_months = Column(Integer, nullable=False)
    is_blacklisted = Column(Boolean, default=False)

    rejection_reason = Column(Text, nullable=True)  