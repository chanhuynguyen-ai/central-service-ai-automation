from fastapi import APIRouter

from app.api.routes import (
    analytics,
    assistant,
    auth,
    automation,
    catalog,
    drafts,
    integrations,
    requests,
    workflows,
)

api_router = APIRouter()
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflow and approvals"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# Static /requests/drafts routes must precede the legacy /requests/{request_id}.
api_router.include_router(drafts.router, prefix="/requests/drafts", tags=["Request drafts"])
api_router.include_router(requests.router, prefix="/requests", tags=["Service requests"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["Request catalog"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["AI assistant"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automation monitoring"])
api_router.include_router(
    integrations.router,
    prefix="/integrations/power-platform",
    tags=["Power Platform integration"],
)
