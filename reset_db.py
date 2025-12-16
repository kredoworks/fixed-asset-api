# reset_db.py
"""
Database reset utility - drops all tables and recreates them fresh.

Usage:
    poetry run python reset_db.py           # Reset only
    poetry run python reset_db.py --seed    # Reset + seed mock data
"""
import sys
import argparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from config import settings
from db_base import Base

# Import all models to register them with Base.metadata
import db_models  # noqa: F401


def get_sync_url(async_url: str) -> str:
    """Convert async database URL to sync URL for psycopg2."""
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


def reset_database():
    """Drop all tables and recreate them."""
    sync_url = get_sync_url(settings.DATABASE_URL)

    print("=" * 60)
    print("DATABASE RESET UTILITY")
    print("=" * 60)
    print(f"\nConnecting to: {sync_url.split('@')[1] if '@' in sync_url else sync_url}")

    conn = psycopg2.connect(sync_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        # Get list of all tables
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]

        if tables:
            print(f"\nFound {len(tables)} tables: {', '.join(tables)}")
            print("\nDropping all tables...")

            # Drop all tables with CASCADE
            for table in tables:
                cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                print(f"  - Dropped: {table}")
        else:
            print("\nNo existing tables found.")

        print("\n" + "-" * 60)
        print("Creating fresh tables from SQLAlchemy models...")
        print("-" * 60)

        # Create tables using SQLAlchemy
        from sqlalchemy import create_engine
        sync_engine = create_engine(sync_url)
        Base.metadata.create_all(bind=sync_engine)

        # List created tables
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        new_tables = [row[0] for row in cur.fetchall()]

        print(f"\nCreated {len(new_tables)} tables:")
        for table in new_tables:
            cur.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            print(f"\n  {table}:")
            for col_name, col_type in columns:
                print(f"    - {col_name}: {col_type}")

        print("\n" + "=" * 60)
        print("DATABASE RESET COMPLETE!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        return False

    finally:
        cur.close()
        conn.close()


def seed_data():
    """Run the seed_mock_data script."""
    print("\n" + "=" * 60)
    print("SEEDING DATABASE WITH MOCK DATA...")
    print("=" * 60 + "\n")

    # Import and run the seeder
    from seed_mock_data import seed_database
    seed_database()


def main():
    parser = argparse.ArgumentParser(
        description="Reset database - drop all tables and recreate fresh"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Also seed the database with mock data after reset"
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only seed data (skip table reset)"
    )

    args = parser.parse_args()

    if args.seed_only:
        seed_data()
        return

    success = reset_database()

    if success and args.seed:
        seed_data()
    elif success:
        print("\nTo seed mock data, run:")
        print("  poetry run python reset_db.py --seed")
        print("  OR")
        print("  poetry run python seed_mock_data.py")


if __name__ == "__main__":
    main()
