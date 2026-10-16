from fastapi import FastAPI, Request

from app.routes.auth import router as auth_router
from app.routes.matches import router as matches_router
from app.routes.predictions import router as predictions_router
from app.routes.sports import router as sports_router

app = FastAPI(
    title="Sports Match Prediction API",
    description="Backend API for the CPSC 491 sports match-prediction application.",
    version="0.1.0",
)

app.include_router(sports_router)
app.include_router(auth_router)
app.include_router(matches_router)
app.include_router(predictions_router)


@app.get("/health")
def health_check(request: Request):
    return {"status": "ok", "data_mode": getattr(request.app.state, "data_mode", "database")}
