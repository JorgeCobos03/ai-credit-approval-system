"""Compatibility adapter. New applications always require a human review."""
from app.services.risk_service import assess

def evaluate_application(application, score=None):
    return "REVIEW", assess(application)["reasons"]
