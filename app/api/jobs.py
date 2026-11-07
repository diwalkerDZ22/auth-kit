from fastapi import APIRouter, Depends

from app.api.auth import require_permission   # adapte le chemin à l'endroit où tu l'as défini

router = APIRouter()


@router.post("/jobs/classify")
def classify_job(user=Depends(require_permission("jobs:classify"))):
    # Route bouchon : sera remplacée par l'appel au modèle de détection
    return {"result": "placeholder", "requested_by": user.username}