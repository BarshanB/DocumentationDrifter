# serves the v1 API under /system, routes only wrap analyze() and the run store

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse, Response

from GitHub_Connector import runs
from GitHub_Connector.analysis import analyze
from GitHub_Connector.schemas import (
    AnalysisError,
    AnalysisRequest,
    AnalysisResult,
    ErrorBody,
    ErrorCode,
)

# maps every contract error code to its HTTP status, the one table all failures go through
STATUS_FOR = {
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.REPOSITORY_NOT_FOUND: 404,
    ErrorCode.COMMIT_NOT_FOUND: 404,
    ErrorCode.TIMEOUT: 500,
    ErrorCode.WRITE_FAILED: 500,
}

_ERRORS = {400: {"model": ErrorBody}, 404: {"model": ErrorBody}, 500: {"model": ErrorBody}}

app = FastAPI(
    title="DocumentationDrifter",
    openapi_url="/system/openapi.json",
    docs_url="/system/docs",
    redoc_url=None,
)
router = APIRouter(prefix="/system")


def _json(data: bytes, status: int = 200) -> Response:
    # returns bytes as they are, so GET serves the saved run unchanged
    return Response(content=data, status_code=status, media_type="application/json")


@app.exception_handler(AnalysisError)
def _analysis_error(_, exc: AnalysisError) -> JSONResponse:
    # turns a failed analysis into its status and an ErrorBody
    return JSONResponse(status_code=STATUS_FOR[exc.code], content=exc.body().model_dump(mode="json"))


@router.post("/analyze", response_model=AnalysisResult, responses=_ERRORS)
def post_analyze(request: AnalysisRequest) -> Response:
    # runs one analysis and returns the bytes that were saved
    return _json(runs.dump(analyze(request)))


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult, responses={404: {}})
def get_analysis(analysis_id: str) -> Response:
    # serves a saved run byte for byte
    data = runs.load(analysis_id)
    if data is None:
        return JSONResponse(status_code=404, content={"detail": "Analysis not found"})
    return _json(data)


@router.get("/health")
def health() -> dict[str, str]:
    # answers the warm-up call, does no git work
    return {"status": "ok", "storage": "local"}


app.include_router(router)
