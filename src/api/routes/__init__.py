from fastapi import APIRouter

from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.integrations import router as integrations_router
from api.routes.profile import router as profile_router
from api.routes.products import router as products_router
from api.routes.signals import router as signals_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(integrations_router)
api_router.include_router(profile_router)
api_router.include_router(products_router)
api_router.include_router(signals_router)
