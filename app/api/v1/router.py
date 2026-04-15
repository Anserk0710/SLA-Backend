from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.public_tickets import router as public_ticket_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.tickets import router as tickets_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.technician import router as technician_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(public_ticket_router)
api_router.include_router(dashboard_router)
api_router.include_router(tickets_router)
api_router.include_router(users_router)
api_router.include_router(technician_router)
api_router.include_router(notifications_router)
api_router.include_router(reports_router)
api_router.include_router(notifications_router)
api_router.include_router(reports_router)