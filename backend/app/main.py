from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, comments, debug, health, players, reactions, signals, teams
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(title="Shyfty API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(signals.router, prefix="/api", tags=["signals"])
    app.include_router(reactions.router, prefix="/api", tags=["reactions"])
    app.include_router(comments.router, prefix="/api", tags=["comments"])
    app.include_router(players.router, prefix="/api", tags=["players"])
    app.include_router(teams.router, prefix="/api", tags=["teams"])
    app.include_router(debug.router, prefix="/api", tags=["debug"])

    return app


app = create_app()
