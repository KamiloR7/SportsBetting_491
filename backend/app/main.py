from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse

from app.routes.ml_insights import router as ml_insights_router
from app.routes.standings import router as standings_router
from app.routes.parlays import router as parlay_router
from app.routes.virtual_betting import router as betting_router
from app.routes.auth import router as auth_router
from app.routes.auth_sessions import router as auth_sessions_router
from app.routes.matches import router as matches_router
from app.routes.predictions import router as predictions_router
from app.routes.sports import router as sports_router
from app.routes.ownership_assessment import router as ownership_router

@asynccontextmanager
async def lifespan(application):
    from app.core.config import settings
    worker = None
    if settings.AUTO_REFRESH_ENABLED:
        from app.database.db import engine
        from app.services.fixture_refresh import FixtureRefreshWorker
        worker = FixtureRefreshWorker(engine,settings.AUTO_REFRESH_INTERVAL_SECONDS)
        application.state.fixture_refresh = worker
        worker.start()
    try:
        yield
    finally:
        if worker: worker.stop()

app = FastAPI(
    lifespan=lifespan,
    title="Sports Match Prediction API",
    description="Backend API for the CPSC 491 sports match-prediction application.",
    version="0.1.0",
)

app.include_router(ml_insights_router)
app.include_router(standings_router)
app.include_router(parlay_router)
app.include_router(betting_router)
app.include_router(sports_router)
app.include_router(auth_router)
app.include_router(auth_sessions_router)
app.include_router(matches_router)
app.include_router(predictions_router)
app.include_router(ownership_router)

@app.exception_handler(RequestValidationError)
async def redact_auth_validation(request: Request, exc: RequestValidationError):
    # FastAPI's default validation response can echo a supplied password/body.
    if request.url.path.startswith("/auth/"):
        return JSONResponse(status_code=422, content={"detail": "Invalid authentication request."})
    return await request_validation_exception_handler(request, exc)


@app.get("/health")
def health_check(request: Request):
    worker = getattr(request.app.state,"fixture_refresh",None)
    return {"status": "ok", "data_mode": getattr(request.app.state, "data_mode", "database"),
            "fixture_refresh":worker.status() if worker else {"enabled":False}}


@app.get("/insights/evaluation")
def evaluation_insights():
    import json
    from pathlib import Path
    from fastapi import HTTPException
    path = Path(__file__).resolve().parents[2] / "build" / "sprint2-models" / "report.json"
    from app.core.config import settings
    if settings.MODEL_ODDS_ENABLED:
        manifest_path = settings.MARKET_MODEL_DIRECTORY / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(503, "Pricing model evaluation is unavailable.")
        manifest = json.loads(manifest_path.read_text())
        return {"target": "sport_aware_match_winner", "pricing_models": True,
                "sports": [{"sport": sport, "accuracy": item["metrics"]["accuracy"],
                            "test_rows": item["metrics"]["test_rows"],
                            "baseline_accuracy": item["metrics"].get("majority_baseline_accuracy"),
                            "classes": item["classes"]} for sport, item in manifest["sports"].items()]}
    if not path.is_file():
        raise HTTPException(503, "No evaluated baseline report is available.")
    report = json.loads(path.read_text())
    return {"target":"home_win_vs_not_home_win", "sports":[{"sport":sport,"accuracy":item["metrics"]["accuracy"],"test_rows":item["metrics"]["test_rows"],"baseline_accuracy":item["metrics"]["training_prevalence_baseline"]["accuracy"]} for sport,item in report["sports"].items()]}
