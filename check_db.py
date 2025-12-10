"""Quick script to check database contents"""
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:1234567@localhost:5432/fixed_asset_test_db"
SYNC_URL = "postgresql+psycopg2://postgres:1234567@localhost:5432/fixed_asset_test_db"

async def check_async():
    """Check database using async connection"""
    print("Checking database with async connection...")
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # Check if tables exist
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        print(f"\nTables found: {[t[0] for t in tables]}")

        # Check assets count
        result = await conn.execute(text("SELECT COUNT(*) FROM assets"))
        count = result.scalar()
        print(f"\nAssets count: {count}")

        # Show some assets
        if count > 0:
            result = await conn.execute(text("SELECT asset_code, name FROM assets LIMIT 5"))
            assets = result.fetchall()
            print("\nFirst 5 assets:")
            for asset in assets:
                print(f"  - {asset[0]}: {asset[1]}")

    await engine.dispose()

def check_sync():
    """Check database using sync connection"""
    print("\nChecking database with sync connection...")
    engine = create_engine(SYNC_URL, echo=False)

    with engine.begin() as conn:
        # Check assets count
        result = conn.execute(text("SELECT COUNT(*) FROM assets"))
        count = result.scalar()
        print(f"\nAssets count (sync): {count}")

        # Show some assets
        if count > 0:
            result = conn.execute(text("SELECT asset_code, name FROM assets LIMIT 5"))
            assets = result.fetchall()
            print("\nFirst 5 assets:")
            for asset in assets:
                print(f"  - {asset[0]}: {asset[1]}")

if __name__ == "__main__":
    try:
        asyncio.run(check_async())
    except Exception as e:
        print(f"Async check failed: {e}")

    try:
        check_sync()
    except Exception as e:
        print(f"Sync check failed: {e}")
