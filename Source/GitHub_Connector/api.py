# serves the v1 API under /system, routes only wrap analyze() and the run store

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from GitHub_Connector import course, runs
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
    docs_url=None,  # serves only the contract's routes, no docs pages
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


@app.exception_handler(RequestValidationError)
def _bad_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    # answers FastAPI's own validation failures as 400, never 422, in the error shape of the route's family
    if request.url.path.startswith("/system/test/"):
        return course.course_error(400, course.describe(exc.errors()[0]))
    err = AnalysisError(ErrorCode.INVALID_REQUEST, _describe(exc.errors()[0]))
    return _analysis_error(None, err)


def _describe(error: dict) -> str:
    # words the first validation error the way a caller can act on
    loc = [part for part in error.get("loc", ()) if part != "body"]
    field = loc[0] if loc and isinstance(loc[0], str) else None
    if field is None or error.get("type") == "json_invalid":
        return "request body must be a JSON object"
    missing = error.get("type") == "missing" or error.get("input", ...) is None
    if missing and field in ("repository", "commit_id"):
        return f"{field} is required"
    return f"{field} has the wrong type"


@router.post("/analyze", response_model=AnalysisResult, responses=_ERRORS)
def post_analyze(request: AnalysisRequest) -> Response:
    # runs one analysis and returns the bytes that were saved
    return _json(runs.dump(analyze(request)))


@router.get("/analysis/{analysis_id:path}", response_model=AnalysisResult, responses={404: {}})
def get_analysis(analysis_id: str) -> Response:
    # serves a saved run byte for byte, any unknown or malformed id gets the same 404
    data = runs.load(analysis_id)
    if data is None:
        # matches the reference service's body for a run that doesn't exist (probed 2026-10-17)
        message = f"analysis {analysis_id} does not exist"
        return JSONResponse(status_code=404, content={"code": "ANALYSIS_NOT_FOUND", "message": message})
    return _json(data)


@router.get("/health")
def health() -> dict[str, str]:
    # answers the warm-up call, does no git work
    return {"status": "ok", "storage": "local"}


router.include_router(course.router)
app.include_router(router)
