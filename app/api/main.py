from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.tickets import router as tickets_router
from app.api.endpoints.users import router as user_router

app = FastAPI(
    openapi_url=f"/api/v1/servicedesk/openapi.json",
    docs_url=f"/api/v1/servicedesk/docs",
    title=f"ServiceDesk",
)

app.include_router(user_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
