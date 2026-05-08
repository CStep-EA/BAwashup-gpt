"""
Bower Ag CowCare Tool — FastAPI Backend
Production AI expert system for dairy industry sales reps.
Governance-first: pricing comes from DB, never from LLM memory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="Bower Ag CowCare API",
    description="Expert system for dairy cow care — governance-first, mobile-first.",
    version=os.getenv("APP_VERSION", "0.0.1"),
)

# CORS — allow all origins for development. Production will restrict to Vercel URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production (Sprint 13)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Basic health check — confirms the API is running."""
    return {
        "status": "ok",
        "service": "bowerag-cowcare-api",
        "version": os.getenv("APP_VERSION", "0.0.1"),
    }


@app.get("/governance/health")
async def governance_health():
    """
    Governance engine health — placeholder until Sprint 3.
    Will return product/pricing/sellability counts from DB.
    """
    return {
        "status": "not_yet_implemented",
        "sprint": 0,
        "message": "Governance engine will be built in Sprint 3. "
        "This endpoint will confirm DB connectivity and data counts.",
    }
