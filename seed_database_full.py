"""Script to seed the database with comprehensive sample data including cycles and verifications"""
import csv
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models and base
from db_base import Base
from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification

# Database URL - update this to match your actual database
DATABASE_URL = "postgresql+psycopg2://postgres:1234567@localhost:5432/fixed_asset_test_db"

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables created successfully")
    return engine

def seed_all_data(engine):
    """Seed all tables with sample data"""
    csv_path = Path("tests/sample_assets.csv")

    if not csv_path.exists():
        csv_path = Path("data/sample_assets.csv")

    if not csv_path.exists():
        print(f"ERROR: CSV file not found")
        return

    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Check if data already exists
        existing_assets = session.query(Asset).count()
        existing_cycles = session.query(VerificationCycle).count()
        existing_verifications = session.query(AssetVerification).count()

        if existing_assets > 0 or existing_cycles > 0 or existing_verifications > 0:
            print(f"Database already has data:")
            print(f"  - Assets: {existing_assets}")
            print(f"  - Cycles: {existing_cycles}")
            print(f"  - Verifications: {existing_verifications}")
            response = input("Do you want to clear and re-seed? (y/n): ")
            if response.lower() == 'y':
                session.query(AssetVerification).delete()
                session.query(VerificationCycle).delete()
                session.query(Asset).delete()
                session.commit()
                print("[OK] Cleared existing data")
            else:
                print("Skipping seed")
                return

        print("\n" + "="*60)
        print("STEP 1: Seeding Assets")
        print("="*60)

        # Seed assets from CSV
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            assets = []
            for row in reader:
                asset = Asset(
                    asset_code=row['asset_code'],
                    name=row['asset_name'],
                    is_active=True
                )
                session.add(asset)
                assets.append(asset)
                print(f"  Added: {asset.asset_code} - {asset.name}")

        session.commit()
        print(f"[OK] Seeded {len(assets)} assets")

        # Reload assets to get their IDs
        assets = session.query(Asset).all()

        print("\n" + "="*60)
        print("STEP 2: Creating Verification Cycles")
        print("="*60)

        # Create 3 verification cycles
        cycles = []
        cycle_data = [
            {"tag": "Q1-2024", "status": "LOCKED", "locked_at": datetime.now() - timedelta(days=90)},
            {"tag": "Q2-2024", "status": "LOCKED", "locked_at": datetime.now() - timedelta(days=30)},
            {"tag": "Q3-2024", "status": "ACTIVE", "locked_at": None},
        ]

        for data in cycle_data:
            cycle = VerificationCycle(
                tag=data["tag"],
                status=data["status"],
                created_at=data.get("locked_at", datetime.now()) - timedelta(days=7) if data.get("locked_at") else datetime.now(),
                locked_at=data["locked_at"]
            )
            session.add(cycle)
            cycles.append(cycle)
            print(f"  Created cycle: {cycle.tag} ({cycle.status})")

        session.commit()
        print(f"[OK] Created {len(cycles)} verification cycles")

        # Reload cycles to get their IDs
        cycles = session.query(VerificationCycle).all()

        print("\n" + "="*60)
        print("STEP 3: Creating Asset Verifications")
        print("="*60)

        # Create verifications for different scenarios
        verifications = []

        # Scenario 1: Q1-2024 - All assets verified
        print(f"\n  Cycle: {cycles[0].tag}")
        for i, asset in enumerate(assets[:8]):  # First 8 assets
            verification = AssetVerification(
                asset_id=asset.id,
                cycle_id=cycles[0].id,
                performed_by="john.doe",
                source="SELF",
                status="VERIFIED",
                condition="GOOD" if i % 3 != 0 else "NEEDS_REPAIR",
                location_lat=40.7128 + (i * 0.01),
                location_lng=-74.0060 + (i * 0.01),
                notes=f"Verified during Q1 audit" if i % 2 == 0 else None,
                created_at=cycles[0].created_at,
                verified_at=cycles[0].locked_at
            )
            session.add(verification)
            verifications.append(verification)
            print(f"    - {asset.asset_code}: VERIFIED ({verification.condition})")

        # Scenario 2: Q2-2024 - Mixed statuses
        print(f"\n  Cycle: {cycles[1].tag}")
        statuses = ["VERIFIED", "VERIFIED", "DISCREPANCY", "NOT_FOUND", "VERIFIED", "VERIFIED", "VERIFIED", "DISCREPANCY"]
        conditions = ["GOOD", "GOOD", "DAMAGED", None, "GOOD", "NEEDS_REPAIR", "GOOD", "DAMAGED"]

        for i, asset in enumerate(assets[:8]):
            verification = AssetVerification(
                asset_id=asset.id,
                cycle_id=cycles[1].id,
                performed_by="auditor.smith" if i % 2 == 0 else "jane.doe",
                source="AUDITOR" if i % 2 == 0 else "SELF",
                status=statuses[i],
                condition=conditions[i],
                location_lat=40.7128 + (i * 0.01),
                location_lng=-74.0060 + (i * 0.01),
                photos="photo1.jpg,photo2.jpg" if i % 3 == 0 else None,
                notes=f"Issue noted: needs attention" if statuses[i] == "DISCREPANCY" else None,
                created_at=cycles[1].created_at + timedelta(days=i),
                verified_at=cycles[1].locked_at - timedelta(days=8-i) if statuses[i] == "VERIFIED" else None
            )
            session.add(verification)
            verifications.append(verification)
            print(f"    - {asset.asset_code}: {verification.status} (by {verification.performed_by})")

        # Scenario 3: Q3-2024 (Active) - Partial verifications + New asset
        print(f"\n  Cycle: {cycles[2].tag}")
        for i, asset in enumerate(assets[:5]):  # Only first 5 assets verified so far
            verification = AssetVerification(
                asset_id=asset.id,
                cycle_id=cycles[2].id,
                performed_by="current.user",
                source="SELF",
                status="VERIFIED",
                condition="GOOD",
                location_lat=40.7128 + (i * 0.01),
                location_lng=-74.0060 + (i * 0.01),
                created_at=datetime.now() - timedelta(days=5-i),
                verified_at=datetime.now() - timedelta(days=5-i)
            )
            session.add(verification)
            verifications.append(verification)
            print(f"    - {asset.asset_code}: VERIFIED")

        # Add a new asset discovered during Q3 cycle
        new_asset = Asset(
            asset_code="AST011",
            name="New Scanner Found",
            is_active=True
        )
        session.add(new_asset)
        session.flush()  # Get the ID

        new_asset_verification = AssetVerification(
            asset_id=new_asset.id,
            cycle_id=cycles[2].id,
            performed_by="auditor.smith",
            source="AUDITOR",
            status="NEW_ASSET",
            condition="GOOD",
            location_lat=40.7200,
            location_lng=-74.0100,
            notes="Found in storage room, not in inventory",
            photos="new_asset_photo.jpg",
            created_at=datetime.now() - timedelta(days=2),
            verified_at=datetime.now() - timedelta(days=2)
        )
        session.add(new_asset_verification)
        verifications.append(new_asset_verification)
        print(f"    - {new_asset.asset_code}: NEW_ASSET discovered")

        session.commit()
        print(f"\n[OK] Created {len(verifications)} asset verifications")

        # Summary
        print("\n" + "="*60)
        print("DATABASE SUMMARY")
        print("="*60)
        total_assets = session.query(Asset).count()
        total_cycles = session.query(VerificationCycle).count()
        total_verifications = session.query(AssetVerification).count()

        print(f"Total Assets: {total_assets}")
        print(f"Total Verification Cycles: {total_cycles}")
        print(f"Total Verifications: {total_verifications}")

        # Show cycle details
        print("\nCycle Details:")
        for cycle in session.query(VerificationCycle).all():
            verification_count = session.query(AssetVerification).filter_by(cycle_id=cycle.id).count()
            print(f"  {cycle.tag} ({cycle.status}): {verification_count} verifications")

if __name__ == "__main__":
    print("=" * 60)
    print("COMPREHENSIVE DATABASE SEEDING SCRIPT")
    print("=" * 60)
    print(f"Database: {DATABASE_URL}")
    print()

    try:
        engine = create_tables()
        seed_all_data(engine)
        print("\n" + "=" * 60)
        print("[OK] Database setup complete!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
