from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.classifier import TicketClassifier, get_classifier

router = APIRouter(tags=["ops"])


@router.get("/health")
def health():
    # liveness: the process is up
    return {"status": "ok"}


@router.get("/ready")
def ready(
    db: Session = Depends(get_db),
    classifier: TicketClassifier = Depends(get_classifier),
):
    # readiness: the db answers and the model is loaded
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database not reachable") from None
    if not classifier.ready:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ready"}


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
