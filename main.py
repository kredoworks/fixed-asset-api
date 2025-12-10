from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.cycles.views import router as cycles_router
from api.verification.views import router as verification_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup/shutdown logic if needed
    yield


app = FastAPI(
    title="Fixed Asset API",
    lifespan=lifespan,
)

app.include_router(cycles_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
