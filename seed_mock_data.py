"""
Seed Mock Data for Fixed Asset Verification API
================================================
Following the natural data flow of the application:

1. USERS - Admin creates the system, adds auditors and asset owners
2. ASSETS - Organization's fixed assets are registered
3. CYCLES - Admin creates verification cycles (quarterly)
4. VERIFICATIONS - Users verify assets they're responsible for
5. OVERRIDES - Auditors/Admins correct verification mistakes
6. CYCLE LOCK - Admin locks completed cycles

Run: poetry run python seed_mock_data.py
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from config import settings
from core.security import get_password_hash


def get_sync_db_url():
    """Convert async URL to sync URL for psycopg2"""
    url = str(settings.DATABASE_URL)
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql")
    return url


# =============================================================================
# STEP 1: USERS - The people who will use the system
# =============================================================================
# Flow: System admin is created first, then adds other users

USERS = [
    # System Administrator - has full access
    {
        "email": "admin@company.com",
        "password": "admin123",
        "full_name": "System Administrator",
        "role": "ADMIN",
        "is_active": True,
    },
    # Auditors - can verify any asset and override verifications
    {
        "email": "john.auditor@company.com",
        "password": "auditor123",
        "full_name": "John Smith (Lead Auditor)",
        "role": "AUDITOR",
        "is_active": True,
    },
    {
        "email": "sarah.auditor@company.com",
        "password": "auditor123",
        "full_name": "Sarah Johnson (Auditor)",
        "role": "AUDITOR",
        "is_active": True,
    },
    # Asset Owners - can verify their own assigned assets
    {
        "email": "mike.developer@company.com",
        "password": "owner123",
        "full_name": "Mike Chen (Developer)",
        "role": "OWNER",
        "is_active": True,
    },
    {
        "email": "lisa.manager@company.com",
        "password": "owner123",
        "full_name": "Lisa Park (Manager)",
        "role": "OWNER",
        "is_active": True,
    },
    {
        "email": "david.designer@company.com",
        "password": "owner123",
        "full_name": "David Kim (Designer)",
        "role": "OWNER",
        "is_active": True,
    },
    # Viewer - can only view, cannot verify
    {
        "email": "viewer@company.com",
        "password": "viewer123",
        "full_name": "Report Viewer",
        "role": "VIEWER",
        "is_active": True,
    },
]


# =============================================================================
# STEP 2: ASSETS - Fixed assets owned by the organization
# =============================================================================
# These are the physical items that need to be verified each cycle
# owner_id will be set after users are created

ASSETS = [
    # IT Equipment - Laptops (assigned to specific employees)
    {"asset_code": "IT-LAP-001", "name": "Dell Latitude 5520 Laptop", "owner_email": "mike.developer@company.com", "is_active": True},
    {"asset_code": "IT-LAP-002", "name": "MacBook Pro 14-inch M3", "owner_email": "lisa.manager@company.com", "is_active": True},
    {"asset_code": "IT-LAP-003", "name": "HP EliteBook 840 G8", "owner_email": "david.designer@company.com", "is_active": True},

    # IT Equipment - Shared/Unassigned
    {"asset_code": "IT-DSK-001", "name": "Dell OptiPlex 7090 Desktop", "owner_email": None, "is_active": True},
    {"asset_code": "IT-MON-001", "name": "Dell UltraSharp 27\" Monitor", "owner_email": "mike.developer@company.com", "is_active": True},
    {"asset_code": "IT-MON-002", "name": "LG 32\" 4K Display", "owner_email": "lisa.manager@company.com", "is_active": True},
    {"asset_code": "IT-PRN-001", "name": "HP LaserJet Pro MFP", "owner_email": None, "is_active": True},

    # Office Furniture
    {"asset_code": "OF-DSK-001", "name": "Standing Desk - Adjustable", "owner_email": None, "is_active": True},
    {"asset_code": "OF-DSK-002", "name": "Executive Office Desk", "owner_email": None, "is_active": True},
    {"asset_code": "OF-CHR-001", "name": "Herman Miller Aeron Chair", "owner_email": "mike.developer@company.com", "is_active": True},
    {"asset_code": "OF-CHR-002", "name": "Steelcase Leap Chair", "owner_email": "lisa.manager@company.com", "is_active": True},
    {"asset_code": "OF-CAB-001", "name": "4-Drawer Filing Cabinet", "owner_email": None, "is_active": True},

    # Mobile Devices
    {"asset_code": "MB-PHN-001", "name": "iPhone 15 Pro", "owner_email": "lisa.manager@company.com", "is_active": True},
    {"asset_code": "MB-TAB-001", "name": "iPad Pro 12.9\"", "owner_email": "david.designer@company.com", "is_active": True},

    # Retired Asset (no longer in use)
    {"asset_code": "IT-LAP-OLD", "name": "Dell Latitude E5470 (Retired)", "owner_email": None, "is_active": False},
]


# =============================================================================
# STEP 3: CYCLES - Admin creates verification cycles
# =============================================================================
# Quarterly verification cycles created by admin

CYCLES = [
    {
        "tag": "Q4-2024",
        "status": "LOCKED",  # Completed and locked
        "created_days_ago": 120,
        "locked_days_ago": 90,
    },
    {
        "tag": "Q1-2025",
        "status": "LOCKED",  # Completed and locked
        "created_days_ago": 60,
        "locked_days_ago": 30,
    },
    {
        "tag": "Q2-2025",
        "status": "ACTIVE",  # Currently active - users are verifying
        "created_days_ago": 7,
        "locked_days_ago": None,
    },
]


def seed_database():
    """Main seeding function following natural data flow"""
    db_url = get_sync_db_url()
    print("=" * 60)
    print("FIXED ASSET VERIFICATION - MOCK DATA SEEDER")
    print("=" * 60)
    print(f"\nConnecting to database...")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    now = datetime.now()

    try:
        # Check tables exist
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")
        if not cur.fetchone()[0]:
            print("[ERROR] Tables do not exist. Run migrations first:")
            print("  poetry run alembic upgrade head")
            return False

        # =================================================================
        # CLEAR EXISTING DATA
        # =================================================================
        print("\n[CLEAR] Removing existing data...")
        cur.execute("DELETE FROM asset_verifications")
        cur.execute("DELETE FROM verification_cycles")
        cur.execute("DELETE FROM assets")
        cur.execute("DELETE FROM users")
        conn.commit()
        print("         All tables cleared.")

        # =================================================================
        # STEP 1: CREATE USERS
        # =================================================================
        print("\n" + "=" * 60)
        print("STEP 1: USERS - Creating system users")
        print("=" * 60)

        user_ids = {}  # email -> id mapping

        for user in USERS:
            hashed_pw = get_password_hash(user["password"])
            cur.execute(
                """
                INSERT INTO users (email, hashed_password, full_name, role, is_active, must_change_password)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user["email"], hashed_pw, user["full_name"], user["role"], user["is_active"], False)
            )
            user_id = cur.fetchone()[0]
            user_ids[user["email"]] = user_id
            role_badge = f"[{user['role']}]"
            print(f"  + {role_badge:10} {user['full_name']} ({user['email']}) -> id={user_id}")

        conn.commit()
        print(f"\n  Created {len(USERS)} users.")

        # =================================================================
        # STEP 2: REGISTER ASSETS
        # =================================================================
        print("\n" + "=" * 60)
        print("STEP 2: ASSETS - Registering organization assets")
        print("=" * 60)

        asset_ids = {}  # asset_code -> id mapping

        for asset in ASSETS:
            owner_id = user_ids.get(asset["owner_email"]) if asset["owner_email"] else None
            cur.execute(
                """
                INSERT INTO assets (asset_code, name, owner_id, is_active)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (asset["asset_code"], asset["name"], owner_id, asset["is_active"])
            )
            asset_id = cur.fetchone()[0]
            asset_ids[asset["asset_code"]] = asset_id

            owner_name = asset["owner_email"].split("@")[0] if asset["owner_email"] else "unassigned"
            status = "ACTIVE" if asset["is_active"] else "RETIRED"
            print(f"  + {asset['asset_code']:12} {asset['name'][:35]:35} [{status}] owner={owner_name}")

        conn.commit()
        print(f"\n  Registered {len(ASSETS)} assets.")

        # =================================================================
        # STEP 3: CREATE VERIFICATION CYCLES (Admin action)
        # =================================================================
        print("\n" + "=" * 60)
        print("STEP 3: CYCLES - Admin creates verification cycles")
        print("=" * 60)

        cycle_ids = {}  # tag -> id mapping

        for cycle in CYCLES:
            created_at = now - timedelta(days=cycle["created_days_ago"])
            locked_at = now - timedelta(days=cycle["locked_days_ago"]) if cycle["locked_days_ago"] else None

            cur.execute(
                """
                INSERT INTO verification_cycles (tag, status, created_at, locked_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (cycle["tag"], cycle["status"], created_at, locked_at)
            )
            cycle_id = cur.fetchone()[0]
            cycle_ids[cycle["tag"]] = cycle_id

            status_icon = "🔒" if cycle["status"] == "LOCKED" else "🟢"
            print(f"  {status_icon} {cycle['tag']} [{cycle['status']}] -> id={cycle_id}")

        conn.commit()
        print(f"\n  Created {len(CYCLES)} verification cycles.")

        # =================================================================
        # STEP 4: VERIFICATIONS - Users verify their assets
        # =================================================================
        print("\n" + "=" * 60)
        print("STEP 4: VERIFICATIONS - Users verify assets")
        print("=" * 60)

        verification_count = 0

        # --- Q4-2024: All assets verified successfully (historical) ---
        print("\n  [Q4-2024] Historical cycle - all assets verified:")
        q4_id = cycle_ids["Q4-2024"]
        q4_time = now - timedelta(days=100)

        for i, (code, aid) in enumerate(asset_ids.items()):
            if code == "IT-LAP-OLD":  # Skip retired
                continue

            # Owners verify their own, auditors verify unassigned
            asset = next(a for a in ASSETS if a["asset_code"] == code)
            if asset["owner_email"]:
                verifier_id = user_ids[asset["owner_email"]]
                source = "SELF"
            else:
                verifier_id = user_ids["john.auditor@company.com"]
                source = "AUDITOR"

            cur.execute(
                """
                INSERT INTO asset_verifications
                (asset_id, cycle_id, performed_by, source, status, condition,
                 photos, notes, created_at, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (aid, q4_id, str(verifier_id), source, "VERIFIED", "GOOD",
                 json.dumps([f"q4/{code}.jpg"]), "Q4-2024 verification complete",
                 q4_time + timedelta(hours=i), q4_time + timedelta(hours=i))
            )
            verification_count += 1

        conn.commit()
        print(f"    ✓ 14 assets verified by owners and auditors")

        # --- Q1-2025: Mixed results with issues found ---
        print("\n  [Q1-2025] Previous cycle - some issues found:")
        q1_id = cycle_ids["Q1-2025"]
        q1_time = now - timedelta(days=45)

        q1_scenarios = [
            # (asset_code, verifier_email, status, condition, notes)
            ("IT-LAP-001", "mike.developer@company.com", "VERIFIED", "GOOD", "Working fine"),
            ("IT-LAP-002", "lisa.manager@company.com", "VERIFIED", "GOOD", "No issues"),
            ("IT-LAP-003", "david.designer@company.com", "DISCREPANCY", "DAMAGED", "Screen cracked!"),  # Will be overridden
            ("IT-DSK-001", "john.auditor@company.com", "VERIFIED", "NEEDS_REPAIR", "Fan noise, needs service"),
            ("IT-MON-001", "mike.developer@company.com", "VERIFIED", "GOOD", "OK"),
            ("IT-MON-002", "lisa.manager@company.com", "NOT_FOUND", None, "Cannot locate monitor"),  # Will be overridden
            ("IT-PRN-001", "sarah.auditor@company.com", "VERIFIED", "GOOD", "Functioning"),
            ("OF-DSK-001", "john.auditor@company.com", "VERIFIED", "GOOD", "OK"),
            ("OF-DSK-002", "sarah.auditor@company.com", "DISCREPANCY", "DAMAGED", "Surface scratched"),
            ("OF-CHR-001", "mike.developer@company.com", "VERIFIED", "GOOD", "Comfortable"),
            ("OF-CHR-002", "lisa.manager@company.com", "VERIFIED", "GOOD", "OK"),
            ("OF-CAB-001", "john.auditor@company.com", "NOT_FOUND", None, "Moved? Cannot find"),
            ("MB-PHN-001", "lisa.manager@company.com", "VERIFIED", "GOOD", "OK"),
            ("MB-TAB-001", "david.designer@company.com", "VERIFIED", "GOOD", "OK"),
        ]

        q1_verification_ids = {}  # asset_code -> verification_id for overrides

        for i, (code, email, status, condition, notes) in enumerate(q1_scenarios):
            aid = asset_ids[code]
            verifier_id = user_ids[email]
            source = "SELF" if "OWNER" in next(u["role"] for u in USERS if u["email"] == email) else "AUDITOR"

            cur.execute(
                """
                INSERT INTO asset_verifications
                (asset_id, cycle_id, performed_by, source, status, condition,
                 photos, notes, created_at, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (aid, q1_id, str(verifier_id), source, status, condition,
                 json.dumps([f"q1/{code}.jpg"]) if status != "NOT_FOUND" else None, notes,
                 q1_time + timedelta(hours=i), q1_time + timedelta(hours=i))
            )
            vid = cur.fetchone()[0]
            q1_verification_ids[code] = vid
            verification_count += 1

            if status in ("DISCREPANCY", "NOT_FOUND"):
                print(f"    ⚠ {code}: {status} - {notes}")

        conn.commit()
        print(f"    ✓ 14 verifications (2 discrepancies, 2 not found)")

        # =================================================================
        # STEP 5: OVERRIDES - Auditors correct issues
        # =================================================================
        print("\n" + "=" * 60)
        print("STEP 5: OVERRIDES - Auditors/Admins correct verifications")
        print("=" * 60)

        # Override 1: IT-LAP-003 was marked DISCREPANCY (damaged screen)
        # Auditor overrides after laptop was repaired
        original_id = q1_verification_ids["IT-LAP-003"]
        cur.execute(
            """
            INSERT INTO asset_verifications
            (asset_id, cycle_id, performed_by, source, status, condition,
             photos, notes, override_of_verification_id, override_reason,
             created_at, verified_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (asset_ids["IT-LAP-003"], q1_id, str(user_ids["john.auditor@company.com"]),
             "OVERRIDDEN", "VERIFIED", "GOOD",
             json.dumps(["q1/IT-LAP-003_repaired.jpg"]),
             "Laptop screen replaced by IT department",
             original_id,
             "Screen was repaired. Asset is now in good condition.",
             q1_time + timedelta(days=5), q1_time + timedelta(days=5))
        )
        verification_count += 1
        print(f"  ✓ IT-LAP-003: DISCREPANCY → VERIFIED (screen repaired)")

        # Override 2: IT-MON-002 was NOT_FOUND but later located
        original_id = q1_verification_ids["IT-MON-002"]
        cur.execute(
            """
            INSERT INTO asset_verifications
            (asset_id, cycle_id, performed_by, source, status, condition,
             photos, notes, override_of_verification_id, override_reason,
             created_at, verified_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (asset_ids["IT-MON-002"], q1_id, str(user_ids["sarah.auditor@company.com"]),
             "OVERRIDDEN", "VERIFIED", "GOOD",
             json.dumps(["q1/IT-MON-002_found.jpg"]),
             "Found in storage room B-12 during renovation",
             original_id,
             "Monitor was temporarily moved during office renovation.",
             q1_time + timedelta(days=7), q1_time + timedelta(days=7))
        )
        verification_count += 1
        print(f"  ✓ IT-MON-002: NOT_FOUND → VERIFIED (found in storage)")

        conn.commit()

        # --- Q2-2025: Currently active - partial verifications ---
        print("\n  [Q2-2025] Current active cycle - in progress:")
        q2_id = cycle_ids["Q2-2025"]
        q2_time = now - timedelta(days=3)

        # Only some assets verified so far
        q2_verified = [
            ("IT-LAP-001", "mike.developer@company.com", "VERIFIED", "GOOD", "All good"),
            ("IT-LAP-002", "lisa.manager@company.com", "VERIFIED", "GOOD", "No issues"),
            ("IT-MON-001", "mike.developer@company.com", "VERIFIED", "GOOD", "OK"),
            ("OF-CHR-001", "mike.developer@company.com", "VERIFIED", "GOOD", "Still comfortable"),
            ("MB-PHN-001", "lisa.manager@company.com", "DISCREPANCY", "DAMAGED", "Screen cracked after drop"),
        ]

        for i, (code, email, status, condition, notes) in enumerate(q2_verified):
            aid = asset_ids[code]
            verifier_id = user_ids[email]

            cur.execute(
                """
                INSERT INTO asset_verifications
                (asset_id, cycle_id, performed_by, source, status, condition,
                 photos, notes, created_at, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (aid, q2_id, str(verifier_id), "SELF", status, condition,
                 json.dumps([f"q2/{code}.jpg"]), notes,
                 q2_time + timedelta(hours=i), q2_time + timedelta(hours=i))
            )
            verification_count += 1

        # NEW ASSET discovered during Q2-2025 verification
        cur.execute(
            """
            INSERT INTO assets (asset_code, name, owner_id, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            ("AV-PRJ-001", "Epson PowerLite Projector (Discovered)", None, True)
        )
        new_asset_id = cur.fetchone()[0]
        asset_ids["AV-PRJ-001"] = new_asset_id

        cur.execute(
            """
            INSERT INTO asset_verifications
            (asset_id, cycle_id, performed_by, source, status, condition,
             photos, notes, created_at, verified_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (new_asset_id, q2_id, str(user_ids["john.auditor@company.com"]),
             "AUDITOR", "NEW_ASSET", "GOOD",
             json.dumps(["q2/AV-PRJ-001_discovery.jpg"]),
             "Found untracked projector in Conference Room B",
             q2_time + timedelta(hours=10), q2_time + timedelta(hours=10))
        )
        verification_count += 1

        conn.commit()
        print(f"    ✓ 5 assets verified, 1 discrepancy reported")
        print(f"    ✓ 1 new asset discovered (AV-PRJ-001)")
        print(f"    ⏳ 9 assets still pending verification")

        # =================================================================
        # SUMMARY
        # =================================================================
        print("\n" + "=" * 60)
        print("SEED COMPLETE - SUMMARY")
        print("=" * 60)

        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM assets")
        asset_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM verification_cycles")
        cycle_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM asset_verifications")
        total_verifications = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM asset_verifications WHERE source = 'OVERRIDDEN'")
        override_count = cur.fetchone()[0]

        print(f"""
  Users:         {user_count}
  Assets:        {asset_count}
  Cycles:        {cycle_count}
  Verifications: {total_verifications}
  Overrides:     {override_count}
        """)

        # Pending count for active cycle
        cur.execute("""
            SELECT COUNT(*) FROM assets a
            WHERE a.is_active = true
            AND NOT EXISTS (
                SELECT 1 FROM asset_verifications av
                WHERE av.asset_id = a.id AND av.cycle_id = %s
            )
        """, (q2_id,))
        pending = cur.fetchone()[0]
        print(f"  Pending in Q2-2025: {pending} assets")

        # Test credentials
        print("\n" + "=" * 60)
        print("TEST CREDENTIALS")
        print("=" * 60)
        print("""
  ADMIN:   admin@company.com / admin123
  AUDITOR: john.auditor@company.com / auditor123
  OWNER:   mike.developer@company.com / owner123
  VIEWER:  viewer@company.com / viewer123
        """)

        # Test endpoints
        print("=" * 60)
        print("TEST ENDPOINTS")
        print("=" * 60)
        print(f"""
  # Login as admin
  curl -X POST "http://localhost:8000/api/v1/auth/login" \\
    -d "username=admin@company.com&password=admin123"

  # Get pending assets (Q2-2025, id={q2_id})
  curl "http://localhost:8000/api/v1/verification/pending?cycle_id={q2_id}" \\
    -H "Authorization: Bearer <token>"

  # Dashboard for active cycle
  curl "http://localhost:8000/api/v1/dashboard/cycles/{q2_id}" \\
    -H "Authorization: Bearer <token>"
        """)

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    success = seed_database()
    if success:
        print("\n[OK] Database seeded successfully!")
        sys.exit(0)
    else:
        print("\n[FAILED] Seeding failed.")
        sys.exit(1)
