from fastapi import APIRouter

from app.api.routes import analytics, assistant, auth, automation, integrations, requests

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(requests.router, prefix="/requests", tags=["Service requests"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["AI assistant"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automation monitoring"])
api_router.include_router(
    integrations.router,
    prefix="/integrations/power-platform",
    tags=["Power Platform integration"],
)
