from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.shyft import ShyftTraceRead
from app.services.shyft_inspection_service import inspect_shyft

router = APIRouter()

def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.get("/debug/shyfts/{shyft_id}", response_model=ShyftTraceRead)
def get_shyft_trace(
    shyft_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ShyftTraceRead:
    _require_user(current_user)
    trace = inspect_shyft(db, shyft_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Shyft not found")
    return trace
