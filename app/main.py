"""
TRACR FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Configure CORS for local development (dashboard at :5173, sample app at :3000)
  - Mount the API router from app.api.routes

Sub-Task 1: app starts and serves auto-docs at /docs.
Routes are registered but not yet implemented (stubs live in app/api/routes.py).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes

app = FastAPI(
    title="TRACR",
    description=(
        "Developer-focused application maintenance and debugging tool. "
        "Collects user behavior events and surfaces behavioral intelligence "
        "through a developer dashboard."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the React dashboard (:5173) and the sample app (:3000)
# to call the API without browser CORS errors.
# For MVP / local development only: do not use allow_origins=["*"] in prod.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:3000",
    "https://git-gud-uxb8.vercel.app",
    ],ow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
app.include_router(routes.router)
