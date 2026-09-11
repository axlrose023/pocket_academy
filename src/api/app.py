from fastapi import FastAPI

from api.routes import api_router
from config import Config, get_config


def create_app(config: Config | None = None) -> FastAPI:
    resolved_config = config or get_config()
    application = FastAPI(
        title="Pocket Academy API",
        version="0.1.0",
        docs_url="/docs" if resolved_config.bot.debug else None,
        redoc_url=None,
    )
    application.state.config = resolved_config
    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
