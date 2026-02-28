from fastapi import FastAPI

app = FastAPI(
    title="AI Credit Approval System",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "API running"}

from app.database import engine, Base
from app.routes import applications, score

Base.metadata.create_all(bind=engine)

app.include_router(applications.router)
app.include_router(score.router)

from app.routes import dashboard
app.include_router(dashboard.router)