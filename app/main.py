from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.authentification.login import router as login_router
from app.api.authentification.register import router as register_router


app = FastAPI(title="JWT Auth FastApi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(login_router, prefix="/auth", tags=["authentification"])
app.include_router(register_router, prefix="/auth", tags=["authentification"])