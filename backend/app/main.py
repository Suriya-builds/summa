"""Summa API. Run with: uvicorn app.main:app --reload"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import settings
from .db import init_db
from .routers import account, analytics, assistant, auth, budgets, messages, scam, transactions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("summa")


def _warm_models() -> None:
    """Train the two small classifiers at start-up so the first request is not slow."""
    from .services import categorizer, scam_detector

    try:
        scam_detector.text_model.get()
        categorizer.merchant_model.get()
        log.info("models ready: scam %s, merchant %s", scam_detector.text_model.metrics.get("held_out_f1"),
                 categorizer.merchant_model.metrics.get("held_out_accuracy"))
    except Exception:  # pragma: no cover - logged, and retried lazily on first use
        log.exception("model warm-up failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    threading.Thread(target=_warm_models, daemon=True).start()
    log.info("Summa started. LLM features %s.", "enabled" if settings.llm_enabled else "disabled (no ANTHROPIC_API_KEY)")
    yield


app = FastAPI(
    title="Summa API",
    version="1.0.0",
    description="Turns bank and UPI SMS into a ledger, a budget, scam warnings and grounded answers.",
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def security(request: Request, call_next):
    # Reject state-changing requests that a browser sent from another site.
    if request.method in _UNSAFE_METHODS and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin:
            origin_host = urlsplit(origin).netloc.lower()
            allowed = {request.headers.get("host", "").lower()} | {urlsplit(o).netloc.lower() for o in settings.cors_origins}
            if origin_host not in allowed:
                return JSONResponse({"detail": "Cross-site request blocked."}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    elif not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        response.headers.setdefault("Content-Security-Policy", CSP)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return one readable sentence instead of FastAPI's nested error list."""
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
        message = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
        parts.append(f"{field}: {message}" if field else message)
    return JSONResponse({"detail": "; ".join(parts) or "Invalid request."}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)


for module in (auth, messages, transactions, analytics, budgets, scam, assistant, account):
    app.include_router(module.router)


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def api_not_found(rest: str):
    raise HTTPException(status_code=404, detail="Not found.")


# --- built frontend (single-page app) ---------------------------------------
_DIST = settings.frontend_dist


@app.get("/{path:path}", include_in_schema=False)
async def spa(path: str):
    if not _DIST.is_dir():
        return JSONResponse(
            {"detail": "The frontend has not been built. Run 'npm run build' in frontend/, or use the Vite dev server."},
            status_code=404,
        )
    candidate = (_DIST / path).resolve()
    if path and candidate.is_file() and _DIST.resolve() in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(_DIST / "index.html", headers={"Cache-Control": "no-cache"})
