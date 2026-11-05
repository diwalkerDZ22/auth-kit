from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.authentification.login import router as login_router
from app.api.authentification.register import router as register_router


app = FastAPI(title="JWT Auth FastApi")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(login_router, prefix="/auth", tags=["authentification"])
app.include_router(register_router, prefix="/auth", tags=["authentification"])