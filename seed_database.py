"""Script to manually seed the database with sample data"""
import asyncio
import csv
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models and base
from db_base import Base
from db_models.asset import Asset

# Database URL - update this to match your actual database
DATABASE_URL = "postgresql+psycopg2://postgres:1234567@localhost:5432/fixed_asset_test_db"

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables created successfully")
    return engine

def seed_assets(engine):
    """Seed assets from CSV file"""
    csv_path = Path("tests/sample_assets.csv")

    if not csv_path.exists():
        csv_path = Path("data/sample_assets.csv")

    if not csv_path.exists():
        print(f"ERROR: CSV file not found at {csv_path}")
        return

    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Check if assets already exist
        existing_count = session.query(Asset).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} assets")
            response = input("Do you want to clear and re-seed? (y/n): ")
            if response.lower() == 'y':
                session.query(Asset).delete()
                session.commit()
                print("[OK] Cleared existing assets")
            else:
                print("Skipping seed")
                return

        # Read and insert assets from CSV
        print(f"Reading assets from {csv_path}...")
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                asset = Asset(
                    asset_code=row['asset_code'],
                    name=row['asset_name'],  # CSV uses 'asset_name' but DB uses 'name'
                    is_active=True
                )
                session.add(asset)
                count += 1
                print(f"  Added: {asset.asset_code} - {asset.name}")

        session.commit()
        print(f"\n[OK] Successfully seeded {count} assets into the database")

        # Verify
        total = session.query(Asset).count()
        print(f"[OK] Total assets in database: {total}")

        # Show sample
        print("\nFirst 5 assets in database:")
        for asset in session.query(Asset).limit(5):
            print(f"  {asset.id}: {asset.asset_code} - {asset.name}")

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE SEEDING SCRIPT")
    print("=" * 60)
    print(f"Database: {DATABASE_URL}")
    print()

    try:
        engine = create_tables()
        seed_assets(engine)
        print("\n" + "=" * 60)
        print("[OK] Database setup complete!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
