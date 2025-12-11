from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cycles_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
