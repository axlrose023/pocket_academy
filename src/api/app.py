from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import api_router
from api.rate_limit import RateLimiter
from config import Config, get_config
from database.engine import engine
from dependencies import get_async_container


def create_app(config: Config | None = None) -> FastAPI:
    resolved_config = config or get_config()

    container = get_async_container(config=resolved_config)
    rate_limiter = RateLimiter.from_config(
        redis=resolved_config.redis,
        config=resolved_config.rate_limit,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await rate_limiter.close()
            await container.close()
            await engine.dispose()

    application = FastAPI(
        title="Pocket Academy API",
        version="0.1.0",
        docs_url="/docs" if resolved_config.bot.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.config = resolved_config

    @application.middleware("http")
    async def rate_limit(request: Request, call_next):
        limit, scope, identifier = _rate_limit_subject(request, resolved_config)
        if limit is not None:
            is_allowed = await rate_limiter.allow(
                scope=scope,
                identifier=identifier,
                limit=limit,
            )
            if not is_allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={
                        "Retry-After": str(resolved_config.rate_limit.window_seconds)
                    },
                )
        return await call_next(request)

    application.include_router(api_router, prefix="/api")
    application.mount(
        "/app",
        StaticFiles(directory=resolved_config.root_path / "webapp", html=True),
        name="webapp",
    )
    application.mount(
        "/admin",
        StaticFiles(directory=resolved_config.root_path / "admin", html=True),
        name="admin",
    )
    setup_dishka(container=container, app=application)
    return application


app = create_app()


def _rate_limit_subject(
    request: Request,
    config: Config,
) -> tuple[int | None, str, str]:
    path = request.url.path
    if path.startswith("/api/integrations/"):
        credential = request.headers.get(
            "X-Webhook-Secret"
        ) or request.query_params.get("token", "")
        return (
            config.rate_limit.webhook_requests_per_window,
            "webhook",
            credential or _client_identifier(request),
        )
    init_data = request.headers.get("X-Telegram-Init-Data")
    if path.startswith("/api/") and init_data:
        return (
            config.rate_limit.webapp_requests_per_window,
            "telegram-webapp",
            init_data,
        )
    return None, "", ""


def _client_identifier(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"
