"""Check all tables in the database"""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres:1234567@localhost:5432/fixed_asset_test_db"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("=" * 60)
    print("DATABASE CONTENTS")
    print("=" * 60)

    # Check Assets
    result = conn.execute(text("SELECT COUNT(*) FROM assets"))
    print(f"\nAssets: {result.scalar()}")

    result = conn.execute(text("SELECT asset_code, name, is_active FROM assets ORDER BY asset_code"))
    for row in result:
        status = "ACTIVE" if row[2] else "INACTIVE"
        print(f"  {row[0]}: {row[1]} ({status})")

    # Check Verification Cycles
    result = conn.execute(text("SELECT COUNT(*) FROM verification_cycles"))
    print(f"\nVerification Cycles: {result.scalar()}")

    result = conn.execute(text("SELECT id, tag, status, locked_at FROM verification_cycles ORDER BY created_at"))
    for row in result:
        locked = "LOCKED" if row[3] else "ACTIVE"
        print(f"  {row[0]}. {row[1]} - {row[2]}")

    # Check Asset Verifications
    result = conn.execute(text("SELECT COUNT(*) FROM asset_verifications"))
    print(f"\nAsset Verifications: {result.scalar()}")

    result = conn.execute(text("""
        SELECT
            av.id,
            a.asset_code,
            vc.tag,
            av.source,
            av.status,
            av.condition,
            av.performed_by
        FROM asset_verifications av
        JOIN assets a ON av.asset_id = a.id
        JOIN verification_cycles vc ON av.cycle_id = vc.id
        ORDER BY vc.created_at, a.asset_code
        LIMIT 10
    """))

    print("\nSample Verifications (first 10):")
    for row in result:
        print(f"  {row[0]}. {row[1]} in {row[2]}: {row[4]} ({row[5] or 'N/A'}) by {row[6] or 'N/A'}")

    # Summary by cycle
    print("\nVerifications by Cycle:")
    result = conn.execute(text("""
        SELECT
            vc.tag,
            vc.status,
            COUNT(av.id) as verification_count,
            COUNT(CASE WHEN av.status = 'VERIFIED' THEN 1 END) as verified_count,
            COUNT(CASE WHEN av.status = 'DISCREPANCY' THEN 1 END) as discrepancy_count,
            COUNT(CASE WHEN av.status = 'NOT_FOUND' THEN 1 END) as not_found_count,
            COUNT(CASE WHEN av.status = 'NEW_ASSET' THEN 1 END) as new_asset_count
        FROM verification_cycles vc
        LEFT JOIN asset_verifications av ON vc.id = av.cycle_id
        GROUP BY vc.id, vc.tag, vc.status
        ORDER BY vc.created_at
    """))

    for row in result:
        print(f"  {row[0]} ({row[1]}): {row[2]} total")
        print(f"    - Verified: {row[3]}, Discrepancies: {row[4]}, Not Found: {row[5]}, New: {row[6]}")

print("\n" + "=" * 60)
