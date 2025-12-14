# Fixed Asset Verification - Mock Data & Testing Guide

## Overview

The `seed_mock_data.py` module populates the database following the **natural user journey** of the Fixed Asset Verification system. This creates realistic test data that mirrors how the application would be used in production.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION DATA FLOW                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: USERS                                                          │
│  ─────────────────                                                      │
│  Admin creates system → Adds Auditors → Adds Asset Owners → Viewers     │
│                                                                         │
│  STEP 2: ASSETS                                                         │
│  ─────────────────                                                      │
│  Register organization's fixed assets with owner assignments            │
│                                                                         │
│  STEP 3: CYCLES                                                         │
│  ─────────────────                                                      │
│  Admin creates quarterly verification cycles (Q4-2024, Q1-2025, etc.)   │
│                                                                         │
│  STEP 4: VERIFICATIONS                                                  │
│  ─────────────────                                                      │
│  Owners verify their assets → Auditors verify unassigned assets         │
│                                                                         │
│  STEP 5: OVERRIDES                                                      │
│  ─────────────────                                                      │
│  Auditors/Admins correct mistakes (repair completed, asset found, etc.) │
│                                                                         │
│  STEP 6: CYCLE LOCK                                                     │
│  ─────────────────                                                      │
│  Admin locks completed cycles → No further modifications allowed        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# 1. Ensure database is running and tables exist
poetry run alembic upgrade head

# 2. Run the seeder
poetry run python seed_mock_data.py

# 3. Start the server
poetry run uvicorn main:app --reload
```

---

## Test Credentials

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| **ADMIN** | `admin@company.com` | `admin123` | Full access, create cycles, lock/unlock |
| **AUDITOR** | `john.auditor@company.com` | `auditor123` | Verify any asset, override verifications |
| **AUDITOR** | `sarah.auditor@company.com` | `auditor123` | Verify any asset, override verifications |
| **OWNER** | `mike.developer@company.com` | `owner123` | Verify own assigned assets |
| **OWNER** | `lisa.manager@company.com` | `owner123` | Verify own assigned assets |
| **OWNER** | `david.designer@company.com` | `owner123` | Verify own assigned assets |
| **VIEWER** | `viewer@company.com` | `viewer123` | Read-only access |

---

## Data Created

### Users (7 total)

| Role | User | Can Create Cycles | Can Verify | Can Override |
|------|------|-------------------|------------|--------------|
| ADMIN | System Administrator | ✅ | ✅ | ✅ |
| AUDITOR | John Smith (Lead) | ❌ | ✅ Any asset | ✅ |
| AUDITOR | Sarah Johnson | ❌ | ✅ Any asset | ✅ |
| OWNER | Mike Chen (Developer) | ❌ | ✅ Own assets | ❌ |
| OWNER | Lisa Park (Manager) | ❌ | ✅ Own assets | ❌ |
| OWNER | David Kim (Designer) | ❌ | ✅ Own assets | ❌ |
| VIEWER | Report Viewer | ❌ | ❌ | ❌ |

### Assets (16 total)

| Code | Name | Owner | Status |
|------|------|-------|--------|
| **IT Equipment** |
| IT-LAP-001 | Dell Latitude 5520 Laptop | Mike Chen | Active |
| IT-LAP-002 | MacBook Pro 14-inch M3 | Lisa Park | Active |
| IT-LAP-003 | HP EliteBook 840 G8 | David Kim | Active |
| IT-DSK-001 | Dell OptiPlex 7090 Desktop | Unassigned | Active |
| IT-MON-001 | Dell UltraSharp 27" Monitor | Mike Chen | Active |
| IT-MON-002 | LG 32" 4K Display | Lisa Park | Active |
| IT-PRN-001 | HP LaserJet Pro MFP | Unassigned | Active |
| **Office Furniture** |
| OF-DSK-001 | Standing Desk - Adjustable | Unassigned | Active |
| OF-DSK-002 | Executive Office Desk | Unassigned | Active |
| OF-CHR-001 | Herman Miller Aeron Chair | Mike Chen | Active |
| OF-CHR-002 | Steelcase Leap Chair | Lisa Park | Active |
| OF-CAB-001 | 4-Drawer Filing Cabinet | Unassigned | Active |
| **Mobile Devices** |
| MB-PHN-001 | iPhone 15 Pro | Lisa Park | Active |
| MB-TAB-001 | iPad Pro 12.9" | David Kim | Active |
| **Retired** |
| IT-LAP-OLD | Dell Latitude E5470 | - | Retired |
| **Discovered** |
| AV-PRJ-001 | Epson PowerLite Projector | - | Active |

### Verification Cycles (3 total)

| Tag | Status | Description |
|-----|--------|-------------|
| Q4-2024 | 🔒 LOCKED | Historical - all assets verified successfully |
| Q1-2025 | 🔒 LOCKED | Issues found, 2 overrides applied |
| Q2-2025 | 🟢 ACTIVE | In progress - 6 verified, 9 pending |

### Verification Summary

| Cycle | Verified | Discrepancy | Not Found | Overrides | Pending |
|-------|----------|-------------|-----------|-----------|---------|
| Q4-2024 | 14 | 0 | 0 | 0 | 0 |
| Q1-2025 | 10 | 2 | 2 | 2 | 0 |
| Q2-2025 | 5 | 1 | 0 | 0 | 9 |

---

## Testing Scenarios

### 1. Authentication Flow

```bash
# Login as Admin
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@company.com&password=admin123"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# Use token in subsequent requests
TOKEN="<paste_access_token_here>"
```

### 2. View Dashboard (Any authenticated user)

```bash
# Get overview stats
curl "http://localhost:8000/api/v1/dashboard/overview" \
  -H "Authorization: Bearer $TOKEN"

# Get active cycle dashboard
curl "http://localhost:8000/api/v1/dashboard/active" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Asset Lookup & Search

```bash
# Lookup specific asset by code
curl "http://localhost:8000/api/v1/verification/assets/lookup?asset_code=IT-LAP-001&cycle_id=3" \
  -H "Authorization: Bearer $TOKEN"

# Search assets by name
curl "http://localhost:8000/api/v1/verification/assets/search?q=laptop" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. View Pending Assets (Active Cycle)

```bash
# Get assets not yet verified in Q2-2025
curl "http://localhost:8000/api/v1/verification/pending?cycle_id=3" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 9 pending assets
```

### 5. Create Verification (Owner/Auditor/Admin)

```bash
# Owner verifies their own asset
curl -X POST "http://localhost:8000/api/v1/verification/assets/4/cycles/3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "SELF",
    "status": "VERIFIED",
    "condition": "GOOD",
    "notes": "Asset in good condition"
  }'
```

### 6. Duplicate Detection

```bash
# Try to verify already-verified asset (returns duplicate warning)
curl -X POST "http://localhost:8000/api/v1/verification/assets/1/cycles/3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "SELF", "status": "VERIFIED", "condition": "GOOD"}'

# Response: {"duplicate": true, "existing_verification": {...}}

# Force duplicate if needed
curl -X POST "http://localhost:8000/api/v1/verification/assets/1/cycles/3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "AUDITOR", "status": "DISCREPANCY", "allow_duplicate": true}'
```

### 7. Override Verification (Auditor/Admin only)

```bash
# Get verification history (shows original + override)
curl "http://localhost:8000/api/v1/verification/assets/3/cycles/2" \
  -H "Authorization: Bearer $TOKEN"

# Create new override
curl -X POST "http://localhost:8000/api/v1/verification/5/override" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "OVERRIDDEN",
    "status": "VERIFIED",
    "condition": "GOOD",
    "override_reason": "Issue has been resolved"
  }'
```

### 8. Cycle Management (Admin only)

```bash
# List all cycles
curl "http://localhost:8000/api/v1/cycles" \
  -H "Authorization: Bearer $TOKEN"

# Get active cycle
curl "http://localhost:8000/api/v1/cycles/active" \
  -H "Authorization: Bearer $TOKEN"

# Lock a cycle (prevents further modifications)
curl -X POST "http://localhost:8000/api/v1/cycles/3/lock" \
  -H "Authorization: Bearer $TOKEN"

# Unlock a cycle
curl -X POST "http://localhost:8000/api/v1/cycles/3/unlock" \
  -H "Authorization: Bearer $TOKEN"

# Create new cycle
curl -X POST "http://localhost:8000/api/v1/cycles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag": "Q3-2025"}'
```

### 9. Discover New Asset (Auditor/Admin)

```bash
curl -X POST "http://localhost:8000/api/v1/verification/assets/new" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_code": "IT-NEW-001",
    "name": "Newly Discovered Printer",
    "cycle_id": 3,
    "source": "AUDITOR",
    "status": "NEW_ASSET",
    "notes": "Found untracked printer in storage"
  }'
```

### 10. Role-Based Access Control Tests

```bash
# Login as OWNER
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -d "username=mike.developer@company.com&password=owner123"

OWNER_TOKEN="<paste_token>"

# Owner CAN verify assets
curl -X POST "http://localhost:8000/api/v1/verification/assets/5/cycles/3" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "SELF", "status": "VERIFIED", "condition": "GOOD"}'
# Expected: 201 Created

# Owner CANNOT create cycles
curl -X POST "http://localhost:8000/api/v1/cycles" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag": "OWNER-CYCLE"}'
# Expected: 403 Forbidden

# Owner CANNOT override
curl -X POST "http://localhost:8000/api/v1/verification/1/override" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "OVERRIDDEN", "status": "VERIFIED", "override_reason": "test"}'
# Expected: 403 Forbidden
```

---

## Cycle Lock Enforcement

When a cycle is LOCKED:

```bash
# Attempting to verify in locked cycle (Q1-2025, id=2)
curl -X POST "http://localhost:8000/api/v1/verification/assets/1/cycles/2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "SELF", "status": "VERIFIED"}'

# Expected: 409 Conflict
# {"detail": "Cycle is locked. No further edits allowed."}
```

---

## Re-seeding

To reset and re-seed the database:

```bash
poetry run python seed_mock_data.py
```

This will:
1. Clear all existing data (users, assets, cycles, verifications)
2. Re-insert fresh mock data following the natural flow
3. Display summary with test credentials and endpoints

---

## Troubleshooting

### Tables don't exist
```bash
poetry run alembic upgrade head
```

### Connection error
Check `.env.local` for correct `DATABASE_URL`:
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
```

### Authentication fails
Ensure you're using the correct credentials from the Test Credentials table above.

### 403 Forbidden
Check that your user role has permission for the action:
- **ADMIN**: Full access
- **AUDITOR**: Verify + Override
- **OWNER**: Verify own assets only
- **VIEWER**: Read-only

---

## API Endpoints Summary

| Method | Endpoint | Auth Required | Role |
|--------|----------|---------------|------|
| POST | `/api/v1/auth/login` | No | - |
| GET | `/api/v1/auth/me` | Yes | Any |
| GET | `/api/v1/cycles` | Yes | Any |
| POST | `/api/v1/cycles` | Yes | ADMIN |
| POST | `/api/v1/cycles/{id}/lock` | Yes | ADMIN |
| POST | `/api/v1/cycles/{id}/unlock` | Yes | ADMIN |
| GET | `/api/v1/dashboard/overview` | Yes | Any |
| GET | `/api/v1/dashboard/cycles/{id}` | Yes | Any |
| GET | `/api/v1/verification/assets/lookup` | Yes | Any |
| GET | `/api/v1/verification/assets/search` | Yes | Any |
| GET | `/api/v1/verification/pending` | Yes | Any |
| POST | `/api/v1/verification/assets/{id}/cycles/{id}` | Yes | ADMIN/AUDITOR/OWNER |
| POST | `/api/v1/verification/{id}/override` | Yes | ADMIN/AUDITOR |
| POST | `/api/v1/verification/assets/new` | Yes | ADMIN/AUDITOR |
