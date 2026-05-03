from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.signal import SignalTraceRead
from app.services.signal_inspection_service import inspect_signal

router = APIRouter()

def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.get("/debug/signals/{signal_id}", response_model=SignalTraceRead)
def get_signal_trace(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> SignalTraceRead:
    _require_user(current_user)
    trace = inspect_signal(db, signal_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return trace
