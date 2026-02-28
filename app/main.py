from fastapi import FastAPI
from app.database import engine, Base
from app.routes import applications, score, dashboard


app = FastAPI(
    title="AI Credit Approval System",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

app.include_router(applications.router)
app.include_router(score.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "API running"}