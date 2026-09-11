from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes import api_router
from config import Config, get_config
from database.engine import engine
from dependencies import get_async_container


def create_app(config: Config | None = None) -> FastAPI:
    resolved_config = config or get_config()

    container = get_async_container(config=resolved_config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
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
    application.include_router(api_router, prefix="/api")
    application.mount(
        "/app",
        StaticFiles(directory=resolved_config.root_path / "webapp", html=True),
        name="webapp",
    )
    setup_dishka(container=container, app=application)
    return application


app = create_app()
