import os
import csv
import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

# Import the app and DB helpers from your project. Adjust module paths if needed.
from main import app as fastapi_app
import db as project_db
import db_models  # ensure models are imported
from db_models.asset import Asset

# TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:1234567@localhost:5432/fixed_asset_test_db"

if not TEST_DATABASE_URL:
    raise RuntimeError("Please set TEST_DATABASE_URL (or DATABASE_URL) environment variable to run tests.")

def get_sync_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return url

sync_url = get_sync_url(TEST_DATABASE_URL)

# Use an async engine for app interactions
engine = create_async_engine(
    TEST_DATABASE_URL,
    future=True,
    echo=False,
    poolclass=NullPool  # Disable connection pooling for tests
)
AsyncSessionTest = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    # Create/drop tables for tests (Destructive - use a dedicated test DB)
    from db_base import Base
    from sqlalchemy import create_engine

    sync_engine = create_engine(sync_url)
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    yield
    Base.metadata.drop_all(bind=sync_engine)

@pytest.fixture
async def db_session():
    async with AsyncSessionTest() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="session", autouse=True)
def seed_assets(prepare_db):
    """Seed sample assets from CSV into the test database"""
    csv_path = Path(__file__).parent / "sample_assets.csv"

    if not csv_path.exists():
        print(f"Warning: {csv_path} not found, skipping seed")
        return

    # Use synchronous SQLAlchemy for session-scoped fixture
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_engine = create_engine(sync_url)
    Session = sessionmaker(bind=sync_engine)

    with Session() as session:
        # Read and insert assets from CSV
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                asset = Asset(
                    asset_code=row['asset_code'],
                    name=row['asset_name'],  # CSV uses 'asset_name' but DB uses 'name'
                    is_active=True
                )
                session.add(asset)

        session.commit()
        print(f"Seeded {session.query(Asset).count()} assets from {csv_path}")

@pytest.fixture
async def async_client():
    # Override the get_session dependency to create a fresh session for each request
    async def override_get_session():
        async with AsyncSessionTest() as session:
            yield session

    fastapi_app.dependency_overrides[project_db.get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://testserver") as ac:
        yield ac

    # Clean up
    fastapi_app.dependency_overrides.clear()
