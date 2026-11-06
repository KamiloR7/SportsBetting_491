"""Additive prepared-feature endpoint; legacy prediction contracts are unchanged."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.schemas.prepared_predictions import PreparedPredictionRequest, PreparedPredictionResponse
from app.services.prepared_prediction_service import (
    PredictionInterfaceError, PreparedPredictionService, get_prepared_prediction_service,
)


class _StructuredValidationRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                errors = [{"location": list(error["loc"]), "type": error["type"], "message": error["msg"]}
                          for error in exc.errors()]
                return JSONResponse(status_code=422, content={"detail": {
                    "code": "invalid_request", "message": "Request fields or JSON are invalid.", "errors": errors,
                }})
        return handler


router = APIRouter(prefix="/predictions", tags=["predictions"], route_class=_StructuredValidationRoute)


@router.post("/prepared", response_model=PreparedPredictionResponse)
def predict_prepared(
    request: PreparedPredictionRequest,
    service: PreparedPredictionService = Depends(get_prepared_prediction_service),
):
    try:
        return service.predict_prepared(request)
    except PredictionInterfaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
