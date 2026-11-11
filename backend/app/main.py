import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.authentification.login import router as login_router
from app.api.authentification.register import router as register_router
from app.api.jobs import router as jobs_router
from app.api.admin import router as admin_router

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.limiter import limiter


# Logs de l'application (loggers "app.*") vers la console
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
_app_logger = logging.getLogger("app")
_app_logger.setLevel(settings.LOG_LEVEL.upper())
if not _app_logger.handlers:
    _app_logger.addHandler(_handler)


app = FastAPI(title="JWT Auth FastApi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.state.limiter = limiter
# Format d'erreur unique {"code", "message"}, y compris pour le 429 de slowapi
register_error_handlers(app)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(login_router, prefix="/auth", tags=["authentification"])
app.include_router(register_router, prefix="/auth", tags=["authentification"])
app.include_router(jobs_router,tags=["jobs"])
app.include_router(admin_router,tags=["admin"])
