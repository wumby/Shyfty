from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.team import TeamDetail, TeamRead
from app.services.team_service import get_team_detail, list_teams

router = APIRouter()


@router.get("/teams", response_model=list[TeamRead])
def get_teams(db: Session = Depends(get_db)) -> list[TeamRead]:
    return list_teams(db)


@router.get("/teams/{team_id}", response_model=TeamDetail)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> TeamDetail:
    team = get_team_detail(db, team_id=team_id, current_user_id=current_user.id if current_user else None)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")
    return team
