from fastapi import FastAPI
from app.api.auth import router as auth_router


app = FastAPI(title="JWT Auth FastApi")

app.include_router(auth_router, prefix="/auth", tags=["auth"])