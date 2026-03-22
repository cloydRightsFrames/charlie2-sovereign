from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/cvrcc", tags=["CVRCC"])

SIGNAL_WEIGHTS = {
    "government_id": 35,
    "biometric_photo": 20,
    "pin_pattern": 15,
    "voice_match": 15,
    "location_history": 10,
    "partial_password": 10,
    "partial_email": 8,
    "touch_pressure": 7,
}

RECOVERY_THRESHOLD = 85


class SignalInput(BaseModel):
    session_id: Optional[str] = None
    government_id: Optional[bool] = False
    biometric_photo: Optional[bool] = False
    pin_pattern: Optional[bool] = False
    voice_match: Optional[bool] = False
    location_history: Optional[bool] = False
    partial_password: Optional[bool] = False
    partial_email: Optional[bool] = False
    touch_pressure: Optional[bool] = False


class ScoreResult(BaseModel):
    session_id: str
    timestamp: str
    signals_matched: list[str]
    signals_failed: list[str]
    total_score: int
    max_possible: int
    confidence_pct: float
    authorized: bool
    audit_branch: str
    verdict: str


def calculate_score(signals: SignalInput) -> ScoreResult:
    session_id = signals.session_id or str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"

    matched = []
    failed = []
    total = 0

    for signal, weight in SIGNAL_WEIGHTS.items():
        value = getattr(signals, signal, False)
        if value:
            matched.append(signal)
            total += weight
        else:
            failed.append(signal)

    max_possible = sum(SIGNAL_WEIGHTS.values())
    confidence_pct = round((total / max_possible) * 100, 2)
    authorized = confidence_pct >= RECOVERY_THRESHOLD

    if authorized:
        audit_branch = "Executive"
        verdict = "RECOVERY AUTHORIZED"
    elif confidence_pct >= 50:
        audit_branch = "Legislative"
        verdict = "PARTIAL MATCH — ADDITIONAL SIGNALS REQUIRED"
    else:
        audit_branch = "Judicial"
        verdict = "DENIED — INSUFFICIENT IDENTITY CONFIDENCE"

    return ScoreResult(
        session_id=session_id,
        timestamp=timestamp,
        signals_matched=matched,
        signals_failed=failed,
        total_score=total,
        max_possible=max_possible,
        confidence_pct=confidence_pct,
        authorized=authorized,
        audit_branch=audit_branch,
        verdict=verdict,
    )


@router.post("/score", response_model=ScoreResult)
def score_recovery_attempt(signals: SignalInput):
    return calculate_score(signals)


@router.get("/signals")
def list_signals():
    return {
        "signals": SIGNAL_WEIGHTS,
        "threshold": RECOVERY_THRESHOLD,
        "max_possible": sum(SIGNAL_WEIGHTS.values()),
    }


@router.get("/health")
def health():
    return {
        "status": "online",
        "module": "CVRCC Confidence Engine",
        "version": "1.0.0",
    }
