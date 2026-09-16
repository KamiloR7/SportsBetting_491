from fastapi import FastAPI

from app.routes.sports import router as sports_router

app = FastAPI(
    title="Sports Match Prediction API",
    description="Backend API for the CPSC 491 sports match-prediction application.",
    version="0.1.0",
)

app.include_router(sports_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
