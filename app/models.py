from app.clock import utcnow
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
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

    created_at = Column(DateTime, default=utcnow)


class CaseAnalysis(Base):
    __tablename__ = 'case_analyses'
    application_id = Column(Integer, ForeignKey('applications.id'), primary_key=True)
    requested_amount = Column(Float, nullable=False)
    term_months = Column(Integer, nullable=False)
    monthly_debt = Column(Float, nullable=False, default=0)
    annual_rate = Column(Float, nullable=False, default=24)
    assessment = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), index=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash = Column(String, primary_key=True)
    actor = Column(String, nullable=False)
    role = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class RateLimit(Base):
    __tablename__ = 'rate_limits'
    key = Column(String, primary_key=True)
    count = Column(Integer, nullable=False, default=0)
    reset_at = Column(DateTime, nullable=False)
