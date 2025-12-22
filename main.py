import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth.views import router as auth_router
from api.cycles.views import router as cycles_router
from api.dashboard.views import router as dashboard_router
from api.verification.views import router as verification_assets_router
from api.verification.views import verification_router


def get_cors_origins() -> list[str]:
    """Get CORS origins from environment variable or use defaults."""
    cors_env = os.environ.get("CORS_ORIGINS", "")

    # Try to parse as JSON array
    if cors_env:
        try:
            origins = json.loads(cors_env)
            if isinstance(origins, list):
                return origins
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated
            return [o.strip() for o in cors_env.split(",") if o.strip()]

    # Default origins for development and production
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "https://v2.d35yxm4ro02au6.amplifyapp.com",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup/shutdown logic if needed
    yield


app = FastAPI(
    title="Fixed Asset Verification API",
    description="API for managing fixed asset verification cycles and audits",
    version="2.0.0",
    lifespan=lifespan,
)

# Get CORS origins from environment or use defaults
cors_origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication endpoints
app.include_router(auth_router, prefix="/api/v1")

# Business endpoints
app.include_router(cycles_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(verification_assets_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}
