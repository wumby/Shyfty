from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.signal import IngestStatusRead
from app.services.scheduler import get_ingest_state, run_ingest_once

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.get("/ingest/status", response_model=IngestStatusRead)
def get_ingest_status() -> IngestStatusRead:
    return IngestStatusRead(**get_ingest_state())


@router.post("/ingest/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingest(
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    _require_user(current_user)
    state = get_ingest_state()
    if state["status"] == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingest already running.")
    background_tasks.add_task(run_ingest_once)
    return {"message": "Ingest triggered."}
