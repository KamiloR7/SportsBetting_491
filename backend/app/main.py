from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse

from app.routes.auth import router as auth_router
from app.routes.auth_sessions import router as auth_sessions_router
from app.routes.matches import router as matches_router
from app.routes.predictions import router as predictions_router
from app.routes.sports import router as sports_router
from app.routes.ownership_assessment import router as ownership_router

app = FastAPI(
    title="Sports Match Prediction API",
    description="Backend API for the CPSC 491 sports match-prediction application.",
    version="0.1.0",
)

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
    return {"status": "ok", "data_mode": getattr(request.app.state, "data_mode", "database")}
