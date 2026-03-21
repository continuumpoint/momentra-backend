from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from src.api.v1 import api_router
from src.config.settings import get_settings
from src.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

# ─── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logger.info("Starting %s v%s [%s]", s.APP_NAME, s.APP_VERSION, s.ENVIRONMENT)
    logger.info("CORS allowed origins: %s", s.ALLOWED_ORIGINS)
    yield
    logger.info("Shutting down %s", s.APP_NAME)


# ─── Build app ────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    s = get_settings()

    application = FastAPI(
        title=s.APP_NAME,
        version=s.APP_VERSION,
        docs_url="/docs" if s.DEBUG else None,
        redoc_url="/redoc" if s.DEBUG else None,
        lifespan=lifespan,
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS — must be added BEFORE routes
    application.add_middleware(
        CORSMiddleware,
        allow_origins=s.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # ─── Global error handlers ────────────────────────────────────────────────
    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        messages = [
            f"{' -> '.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "; ".join(messages)},
        )

    @application.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    # ─── Routes ───────────────────────────────────────────────────────────────
    application.include_router(api_router)

    @application.get("/health", tags=["health"])
    def health_check():
        return {"status": "ok", "version": s.APP_VERSION}

    return application


app = create_app()
