from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.signal import SignalTraceRead
from app.services.signal_inspection_service import inspect_signal

router = APIRouter()


@router.get("/debug/signals/{signal_id}", response_model=SignalTraceRead)
def get_signal_trace(signal_id: int, db: Session = Depends(get_db)) -> SignalTraceRead:
    trace = inspect_signal(db, signal_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return trace
