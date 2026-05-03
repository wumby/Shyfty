from contextlib import asynccontextmanager
import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, comments, debug, health, ingest, players, profile, reactions, signals, teams
from app.core.config import settings
from app.services.auth_service import SESSION_COOKIE_NAME


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

    @app.middleware("http")
    async def csrf_protection(request: Request, call_next):
        is_api = request.url.path.startswith("/api/")
        method = request.method.upper()
        has_session = request.cookies.get(SESSION_COOKIE_NAME) is not None
        csrf_cookie_name = settings.csrf_cookie_name
        csrf_header_name = settings.csrf_header_name
        csrf_cookie_value = request.cookies.get(csrf_cookie_name)
        csrf_header_value = request.headers.get(csrf_header_name)

        if is_api and method in {"POST", "PUT", "PATCH", "DELETE"} and has_session:
            if not csrf_cookie_value or not csrf_header_value or csrf_cookie_value != csrf_header_value:
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed."})

        response = await call_next(request)

        if is_api and not csrf_cookie_value:
            response.set_cookie(
                key=csrf_cookie_name,
                value=secrets.token_urlsafe(32),
                httponly=False,
                secure=settings.csrf_cookie_secure_effective,
                samesite=settings.csrf_cookie_samesite,
                max_age=settings.csrf_cookie_max_age_seconds,
                path="/",
            )

        return response

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(signals.router, prefix="/api", tags=["signals"])
    app.include_router(reactions.router, prefix="/api", tags=["reactions"])
    app.include_router(comments.router, prefix="/api", tags=["comments"])
    app.include_router(players.router, prefix="/api", tags=["players"])
    app.include_router(teams.router, prefix="/api", tags=["teams"])
    app.include_router(ingest.router, prefix="/api", tags=["ingest"])
    app.include_router(profile.router, prefix="/api", tags=["profile"])
    app.include_router(debug.router, prefix="/api", tags=["debug"])

    return app


app = create_app()
