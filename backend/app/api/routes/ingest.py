from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.shyft import IngestStatusRead
from app.services.scheduler import get_ingest_state, run_ingest_once
from app.services.sync_service import get_default_sync_sources

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def _require_admin(user: Optional[User]) -> User:
    user = _require_user(user)
    admin_emails = {email.lower() for email in settings.admin_emails}
    if user.email.lower() not in admin_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


@router.get("/ingest/status", response_model=IngestStatusRead)
def get_ingest_status(current_user: Optional[User] = Depends(get_current_user)) -> IngestStatusRead:
    _require_admin(current_user)
    return IngestStatusRead(**get_ingest_state())


@router.post("/ingest/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingest(
    background_tasks: BackgroundTasks,
    mode: Literal["bootstrap", "incremental"] = Query(default="incremental"),
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    _require_user(current_user)
    state = get_ingest_state()
    if state["status"] == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingest already running.")
    background_tasks.add_task(run_ingest_once, mode, get_default_sync_sources())
    return {"message": f"{mode.capitalize()} sync triggered."}
