# Fixed Asset Verification API - Complete Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [Authentication Flow](#authentication-flow)
5. [API Endpoints](#api-endpoints)
6. [Verification Workflow](#verification-workflow)
7. [Role-Based Access Control](#role-based-access-control)
8. [Cycle Lifecycle](#cycle-lifecycle)

---

## System Overview

The Fixed Asset Verification API is a FastAPI-based backend for managing organizational fixed asset verification processes. It enables tracking, verification, and auditing of physical assets through quarterly verification cycles.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FIXED ASSET VERIFICATION SYSTEM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│   │    USERS    │───▶│   ASSETS    │───▶│   CYCLES    │───▶│VERIFICATIONS│  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                   │                  │                  │         │
│         │                   │                  │                  │         │
│   ADMIN/AUDITOR/       IT Equipment      Quarterly           Status:       │
│   OWNER/VIEWER        Office Furniture   Q1/Q2/Q3/Q4      VERIFIED         │
│                       Mobile Devices                      DISCREPANCY      │
│                                                           NOT_FOUND        │
│                                                           NEW_ASSET        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | FastAPI |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy (async) |
| **Authentication** | JWT (python-jose) |
| **Password Hashing** | bcrypt |
| **Async Driver** | asyncpg |
| **Migration** | Alembic |

### Project Structure

```
fixed-asset-api/
├── api/
│   ├── auth/           # Authentication endpoints
│   │   ├── views.py    # Login, refresh, user management
│   │   └── models.py   # Pydantic schemas
│   ├── cycles/         # Verification cycle management
│   │   ├── views.py    # CRUD + lock/unlock
│   │   ├── models.py
│   │   └── db_manager.py
│   ├── verification/   # Asset verification operations
│   │   ├── views.py    # Lookup, verify, override
│   │   ├── models.py
│   │   └── db_manager.py
│   └── dashboard/      # Statistics & aggregates
│       ├── views.py
│       └── models.py
├── db_models/          # SQLAlchemy models
│   ├── user.py
│   ├── asset.py
│   ├── verification_cycle.py
│   └── asset_verification.py
├── core/               # Core utilities
│   ├── security.py     # JWT, password hashing
│   └── deps.py         # Dependency injection
├── alembic/            # Database migrations
├── tests/              # Pytest tests
└── documentation/      # Project documentation
```

---

## Data Models

### Entity Relationship Diagram

```
┌──────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│      USERS       │       │       ASSETS        │       │ VERIFICATION_CYCLES │
├──────────────────┤       ├─────────────────────┤       ├─────────────────────┤
│ id (PK)          │       │ id (PK)             │       │ id (PK)             │
│ email (UNIQUE)   │       │ asset_code (UNIQUE) │       │ tag (UNIQUE)        │
│ hashed_password  │       │ name                │       │ status              │
│ full_name        │       │ is_active           │       │   - DRAFT           │
│ role             │       │ owner_id (FK)       │───┐   │   - ACTIVE          │
│   - ADMIN        │───────│ created_at          │   │   │   - LOCKED          │
│   - AUDITOR      │       │ updated_at          │   │   │ created_at          │
│   - OWNER        │       └─────────────────────┘   │   │ locked_at           │
│   - VIEWER       │                │                │   └─────────────────────┘
│ is_active        │                │                │             │
│ created_at       │                │                │             │
│ last_login_at    │                │                │             │
└──────────────────┘                │                │             │
                                    ▼                │             │
                    ┌───────────────────────────────┐│             │
                    │     ASSET_VERIFICATIONS       ││             │
                    ├───────────────────────────────┤│             │
                    │ id (PK)                       ││             │
                    │ asset_id (FK) ◄───────────────┘│             │
                    │ cycle_id (FK) ◄────────────────┘             │
                    │ performed_by                                 │
                    │ source                                       │
                    │   - SELF                                     │
                    │   - AUDITOR                                  │
                    │   - OVERRIDDEN                               │
                    │ status                                       │
                    │   - VERIFIED                                 │
                    │   - DISCREPANCY                              │
                    │   - NOT_FOUND                                │
                    │   - NEW_ASSET                                │
                    │ condition                                    │
                    │   - GOOD                                     │
                    │   - DAMAGED                                  │
                    │   - NEEDS_REPAIR                             │
                    │ location_lat / location_lng                  │
                    │ photos                                       │
                    │ notes                                        │
                    │ override_of_verification_id (FK self)        │
                    │ override_reason                              │
                    │ created_at                                   │
                    └───────────────────────────────────────────────┘
```

---

## Authentication Flow

### JWT Token Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                                 │
└────────────────────────────────────────────────────────────────────────────┘

   ┌─────────┐                    ┌─────────┐                    ┌──────────┐
   │  CLIENT │                    │   API   │                    │ DATABASE │
   └────┬────┘                    └────┬────┘                    └────┬─────┘
        │                              │                              │
        │  POST /api/v1/auth/login     │                              │
        │  {email, password}           │                              │
        │─────────────────────────────▶│                              │
        │                              │   SELECT user WHERE email    │
        │                              │─────────────────────────────▶│
        │                              │◀─────────────────────────────│
        │                              │                              │
        │                              │ ┌──────────────────────┐     │
        │                              │ │ Verify password with │     │
        │                              │ │ bcrypt.checkpw()     │     │
        │                              │ └──────────────────────┘     │
        │                              │                              │
        │  {access_token,              │                              │
        │   refresh_token}             │                              │
        │◀─────────────────────────────│                              │
        │                              │                              │
        ├──────────────────────────────┼──────────────────────────────┤
        │     SUBSEQUENT REQUESTS      │                              │
        ├──────────────────────────────┼──────────────────────────────┤
        │                              │                              │
        │  GET /api/v1/cycles          │                              │
        │  Authorization: Bearer {jwt} │                              │
        │─────────────────────────────▶│                              │
        │                              │ ┌──────────────────────┐     │
        │                              │ │ Decode JWT           │     │
        │                              │ │ Extract user_id      │     │
        │                              │ │ Verify not expired   │     │
        │                              │ └──────────────────────┘     │
        │                              │                              │
        │                              │   SELECT user WHERE id       │
        │                              │─────────────────────────────▶│
        │                              │◀─────────────────────────────│
        │                              │                              │
        │  {cycles data}               │                              │
        │◀─────────────────────────────│                              │
        │                              │                              │
        ├──────────────────────────────┼──────────────────────────────┤
        │     TOKEN REFRESH            │                              │
        ├──────────────────────────────┼──────────────────────────────┤
        │                              │                              │
        │  POST /api/v1/auth/refresh   │                              │
        │  {refresh_token}             │                              │
        │─────────────────────────────▶│                              │
        │                              │ ┌──────────────────────┐     │
        │                              │ │ Verify refresh token │     │
        │                              │ │ type == "refresh"    │     │
        │                              │ └──────────────────────┘     │
        │                              │                              │
        │  {new_access_token,          │                              │
        │   new_refresh_token}         │                              │
        │◀─────────────────────────────│                              │
```

### Token Configuration

| Token Type | Expiration | Purpose |
|------------|------------|---------|
| Access Token | 24 hours | API authentication |
| Refresh Token | 7 days | Obtain new access token |

---

## API Endpoints

### Authentication Endpoints (`/api/v1/auth`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTH ENDPOINTS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  POST /login          ──▶  OAuth2 form login, returns tokens                │
│  POST /login/json     ──▶  JSON body login, returns tokens                  │
│  POST /refresh        ──▶  Refresh access token                             │
│  GET  /me             ──▶  Get current user profile                         │
│  PUT  /me             ──▶  Update current user profile                      │
│  POST /me/password    ──▶  Change password                                  │
│                                                                             │
│  ────────────────── ADMIN ONLY ──────────────────────────                   │
│                                                                             │
│  GET  /users              ──▶  List all users                               │
│  POST /users              ──▶  Create new user                              │
│  GET  /users/{id}         ──▶  Get user by ID                               │
│  PUT  /users/{id}         ──▶  Update user                                  │
│  POST /users/{id}/reset-password  ──▶  Reset user password                  │
│  DELETE /users/{id}       ──▶  Deactivate user (soft delete)                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cycle Management Endpoints (`/api/v1/cycles`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CYCLE ENDPOINTS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GET  /                ──▶  List all cycles (newest first)      [Any]       │
│  GET  /active          ──▶  Get current active cycle            [Any]       │
│  GET  /{cycle_id}      ──▶  Get specific cycle by ID            [Any]       │
│                                                                             │
│  ────────────────── ADMIN ONLY ──────────────────────────                   │
│                                                                             │
│  POST /                ──▶  Create new cycle with unique tag                │
│  POST /{id}/activate   ──▶  Change DRAFT → ACTIVE                           │
│  POST /{id}/lock       ──▶  Change ACTIVE → LOCKED                          │
│  POST /{id}/unlock     ──▶  Change LOCKED → ACTIVE                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Verification Endpoints (`/api/v1/verification`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       VERIFICATION ENDPOINTS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ─────────────────── ASSET OPERATIONS ──────────────────                    │
│                                                                             │
│  GET  /assets/lookup?asset_code=&cycle_id=                                  │
│       ──▶  Lookup asset by code for verification            [Any]           │
│                                                                             │
│  GET  /assets/search?q=                                                     │
│       ──▶  Search assets by code or name                    [Any]           │
│                                                                             │
│  POST /assets/new                                                           │
│       ──▶  Create new asset + initial verification    [Auditor/Admin]       │
│                                                                             │
│  POST /assets/{asset_id}/cycles/{cycle_id}                                  │
│       ──▶  Create verification for asset in cycle    [Verifier+]            │
│           • Returns 200 + duplicate info if already exists                  │
│           • Returns 201 on success                                          │
│           • Returns 409 if cycle is LOCKED                                  │
│                                                                             │
│  GET  /assets/{asset_id}/cycles/{cycle_id}                                  │
│       ──▶  Get verification history for asset in cycle      [Any]           │
│                                                                             │
│  ─────────────────── VERIFICATION OPERATIONS ───────────                    │
│                                                                             │
│  POST /{verification_id}/override                                           │
│       ──▶  Override existing verification          [Auditor/Admin]          │
│                                                                             │
│  GET  /pending?cycle_id=                                                    │
│       ──▶  List assets without verification in cycle         [Any]          │
│                                                                             │
│  ─────────────────── UPLOADS ───────────────────────────                    │
│                                                                             │
│  POST /assets/uploads/photo                                                 │
│       ──▶  Upload verification photos               [Verifier+]             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dashboard Endpoints (`/api/v1/dashboard`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD ENDPOINTS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GET  /overview                                                             │
│       ──▶  High-level stats: total assets, active cycle, recent cycles      │
│                                                                             │
│  GET  /active                                                               │
│       ──▶  Dashboard for currently active cycle                             │
│                                                                             │
│  GET  /cycles/{cycle_id}                                                    │
│       ──▶  Complete dashboard for specific cycle                            │
│           • Status breakdown (verified, discrepancy, not found)             │
│           • Condition breakdown (good, damaged, needs repair)               │
│           • Source breakdown (self, auditor, overridden)                    │
│                                                                             │
│  GET  /cycles/{cycle_id}/stats                                              │
│       ──▶  Detailed statistics for cycle                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Verification Workflow

### Complete Verification Process Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VERIFICATION WORKFLOW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌──────────────────┐     ┌─────────────────────────────────────────────────┐
│  Scan/Enter      │     │ GET /verification/assets/lookup                 │
│  Asset Code      │────▶│    ?asset_code=IT-LAP-001&cycle_id=3            │
└──────────────────┘     └────────────────────┬────────────────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                         ▼                    ▼                    ▼
               ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
               │  not_found=true │  │ already_verified │  │  Not Verified   │
               │                 │  │     =true        │  │  Yet            │
               └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                        │                    │                    │
                        ▼                    ▼                    ▼
               ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
               │ Create New      │  │ View Existing   │  │ Create New      │
               │ Asset?          │  │ Verification    │  │ Verification    │
               │ (Auditor/Admin) │  │ OR Override     │  │                 │
               └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                        │                    │                    │
                        ▼                    │                    ▼
               ┌─────────────────┐           │           ┌─────────────────┐
               │ POST /assets/new│           │           │ POST /assets/   │
               │                 │           │           │ {id}/cycles/{id}│
               └────────┬────────┘           │           └────────┬────────┘
                        │                    │                    │
                        ▼                    ▼                    ▼
               ┌──────────────────────────────────────────────────────────┐
               │                    VERIFICATION RECORD                   │
               │  ┌───────────────────────────────────────────────────┐   │
               │  │  source: SELF | AUDITOR | OVERRIDDEN              │   │
               │  │  status: VERIFIED | DISCREPANCY | NOT_FOUND       │   │
               │  │  condition: GOOD | DAMAGED | NEEDS_REPAIR         │   │
               │  │  photos: [file_keys]                              │   │
               │  │  location: {lat, lng}                             │   │
               │  │  notes: "..."                                     │   │
               │  └───────────────────────────────────────────────────┘   │
               └──────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │   201 CREATED   │
                                    │   or            │
                                    │   200 DUPLICATE │
                                    └─────────────────┘
```

### Override Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OVERRIDE FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SCENARIO: Asset was marked NOT_FOUND but later discovered                  │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Original        │                                                        │
│  │ Verification    │                                                        │
│  │                 │                                                        │
│  │ status: NOT_FOUND                                                        │
│  │ source: AUDITOR │                                                        │
│  │ id: 42          │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│           │  POST /verification/42/override                                 │
│           │  {                                                              │
│           │    "source": "OVERRIDDEN",                                      │
│           │    "status": "VERIFIED",                                        │
│           │    "condition": "GOOD",                                         │
│           │    "override_reason": "Asset found in storage room B"           │
│           │  }                                                              │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐                                                        │
│  │ Override        │                                                        │
│  │ Verification    │                                                        │
│  │                 │                                                        │
│  │ status: VERIFIED                                                         │
│  │ source: OVERRIDDEN                                                       │
│  │ override_of_verification_id: 42                                          │
│  │ override_reason: "Asset found..."                                        │
│  │ id: 43          │◄──── This becomes the EFFECTIVE verification           │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Role-Based Access Control

### Permission Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ROLE PERMISSION MATRIX                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Action                          │ ADMIN │ AUDITOR │ OWNER │ VIEWER        │
│  ────────────────────────────────┼───────┼─────────┼───────┼────────       │
│  View assets & verifications     │   ✅   │    ✅    │   ✅   │   ✅          │
│  View dashboard & stats          │   ✅   │    ✅    │   ✅   │   ✅          │
│  Search assets                   │   ✅   │    ✅    │   ✅   │   ✅          │
│  ────────────────────────────────┼───────┼─────────┼───────┼────────       │
│  Verify ANY asset                │   ✅   │    ✅    │   ❌   │   ❌          │
│  Verify OWN assigned assets      │   ✅   │    ✅    │   ✅   │   ❌          │
│  Create new assets               │   ✅   │    ✅    │   ❌   │   ❌          │
│  Override verifications          │   ✅   │    ✅    │   ❌   │   ❌          │
│  Upload photos                   │   ✅   │    ✅    │   ✅   │   ❌          │
│  ────────────────────────────────┼───────┼─────────┼───────┼────────       │
│  Create cycles                   │   ✅   │    ❌    │   ❌   │   ❌          │
│  Lock/Unlock cycles              │   ✅   │    ❌    │   ❌   │   ❌          │
│  Manage users                    │   ✅   │    ❌    │   ❌   │   ❌          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dependency Injection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION DEPENDENCY CHAIN                           │
└─────────────────────────────────────────────────────────────────────────────┘

Request with Authorization Header
              │
              ▼
     ┌─────────────────┐
     │ OAuth2Bearer    │  Extracts token from header
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ get_current_user│  Decodes JWT, fetches user from DB
     └────────┬────────┘
              │
              ├───────────────────────────────────────┐
              ▼                                       ▼
     ┌─────────────────┐                    ┌─────────────────┐
     │   CurrentUser   │                    │  AdminUser      │
     │   (Any auth)    │                    │  (ADMIN only)   │
     └────────┬────────┘                    └─────────────────┘
              │
              ├───────────────────┬───────────────────┐
              ▼                   ▼                   ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │   CanVerify     │ │ AuditorOrAdmin  │ │   OwnerOrAbove  │
     │ (Verify perms)  │ │ (Override perms)│ │ (Owner+)        │
     └─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Cycle Lifecycle

### State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CYCLE STATE MACHINE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                              POST /cycles
                                   │
                                   ▼
                         ┌─────────────────┐
                         │     DRAFT       │
                         │                 │
                         │ • Cycle created │
                         │ • No verifs yet │
                         └────────┬────────┘
                                  │
                                  │ POST /{id}/activate
                                  │ (Admin only)
                                  ▼
                         ┌─────────────────┐
                         │     ACTIVE      │◄────────────────┐
                         │                 │                 │
                         │ • Verifications │                 │
                         │   can be added  │                 │
                         │ • Overrides OK  │                 │
                         └────────┬────────┘                 │
                                  │                          │
                                  │ POST /{id}/lock          │
                                  │ (Admin only)             │
                                  ▼                          │
                         ┌─────────────────┐                 │
                         │     LOCKED      │                 │
                         │                 │                 │
                         │ • No new verifs │                 │
                         │ • No overrides  │                 │
                         │ • Read-only     │                 │
                         │ • locked_at set │                 │
                         └────────┬────────┘                 │
                                  │                          │
                                  │ POST /{id}/unlock        │
                                  │ (Admin only)             │
                                  └──────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOCK ENFORCEMENT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  When cycle status == LOCKED:                                               │
│                                                                             │
│  POST /verification/assets/{id}/cycles/{id}  ──▶  409 CONFLICT              │
│  POST /verification/{id}/override            ──▶  409 CONFLICT              │
│  POST /verification/assets/new (for cycle)   ──▶  409 CONFLICT              │
│                                                                             │
│  Message: "Cycle is locked. No further edits allowed."                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| **200** | OK | Successful GET, duplicate detection |
| **201** | Created | New resource created |
| **400** | Bad Request | Invalid input, validation error |
| **401** | Unauthorized | Missing or invalid token |
| **403** | Forbidden | Insufficient permissions |
| **404** | Not Found | Resource doesn't exist |
| **409** | Conflict | Duplicate, cycle locked, etc. |
| **500** | Internal Error | Server-side error |

---

## Quick Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Common Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Example Requests

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@company.com&password=admin123"

# Get active cycle
curl "http://localhost:8000/api/v1/cycles/active" \
  -H "Authorization: Bearer $TOKEN"

# Verify an asset
curl -X POST "http://localhost:8000/api/v1/verification/assets/1/cycles/3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "SELF",
    "status": "VERIFIED",
    "condition": "GOOD",
    "notes": "Asset confirmed in good condition"
  }'

# Get dashboard
curl "http://localhost:8000/api/v1/dashboard/overview" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Related Documentation

- [seed_data.md](seed_data.md) - Mock data and testing guide
- [README.md](README.md) - Project overview and setup
- [v2_report.md](v2_report.md) - Development report
