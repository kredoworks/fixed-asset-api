# Fixed Asset API

A FastAPI-based REST API for managing fixed asset verification cycles, tracking asset conditions, and handling asset discovery during audits.

## Requirements

- Python 3.12+
- Poetry (dependency manager)
- PostgreSQL 12+

## Setup

### 1. Install dependencies

```bash
poetry install
```

This will create a virtual environment and install all required packages.

### 2. Configure Database

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/your_database_name
DEBUG=True
```

For testing, the tests use a separate database configured in `tests/conftest.py`:
```
TEST_DATABASE_URL=postgresql+asyncpg://postgres:1234567@localhost:5432/fixed_asset_test_db
```

### 3. Seed the Database (Optional)

You can populate your database with sample data using the helper scripts:

#### Option A: Seed All Tables (Recommended)
```bash
poetry run python seed_database_full.py
```

This creates:
- **11 Assets** (from sample_assets.csv + 1 new asset)
- **3 Verification Cycles** (Q1-2024, Q2-2024, Q3-2024)
- **22 Asset Verifications** with realistic scenarios

#### Option B: Seed Only Assets
```bash
poetry run python seed_database.py
```

This creates only the 10 assets from `tests/sample_assets.csv`.

### 4. Run the Development Server

```bash
poetry run uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000` with auto-reload enabled.

### 5. Access the API

- **API documentation**: `http://127.0.0.1:8000/docs` (Swagger UI)
- **Alternative docs**: `http://127.0.0.1:8000/redoc` (ReDoc)

## Project Structure

```
fixed-asset-api/
├── main.py                      # FastAPI application entry point
├── config.py                    # Settings and configuration
├── db.py                        # Database session management
├── db_base.py                   # SQLAlchemy Base
├── db_models/                   # Database models (ORM)
│   ├── asset.py                 # Asset model
│   ├── verification_cycle.py   # Verification cycle model
│   └── asset_verification.py   # Asset verification model
├── api/                         # API endpoints
│   ├── cycles/                  # Verification cycle endpoints
│   │   ├── views.py             # Cycle API routes
│   │   ├── models.py            # Cycle Pydantic models
│   │   └── db_manager.py        # Cycle database operations
│   └── verification/            # Asset verification endpoints
│       ├── views.py             # Verification API routes
│       ├── models.py            # Verification Pydantic models
│       └── db_manager.py        # Verification database operations
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── test_endpoints.py        # API endpoint tests
│   └── sample_assets.csv        # Sample data for testing
├── data/                        # Data files
│   └── sample_assets.csv        # Sample assets
├── seed_database.py             # Helper: Seed assets only
├── seed_database_full.py        # Helper: Seed all tables
├── check_db.py                  # Helper: Check database connection
├── check_all_tables.py          # Helper: View all database data
├── pytest.ini                   # Pytest configuration
├── pyproject.toml               # Poetry configuration
└── README.md                    # This file
```

## API Endpoints

### Verification Cycles

- `POST /api/v1/cycles` - Create a new verification cycle
- `GET /api/v1/cycles` - List all verification cycles
- `GET /api/v1/cycles/{cycle_id}` - Get cycle details
- `POST /api/v1/cycles/{cycle_id}/lock` - Lock a cycle

### Asset Verification

- `GET /api/v1/verification/assets/lookup` - Lookup an asset by code
- `GET /api/v1/verification/assets/search` - Search assets by query
- `POST /api/v1/verification/assets/new` - Register a new asset discovered during audit

## Helper Scripts

The project includes several helper scripts to make development and testing easier:

### 1. `seed_database_full.py` - Comprehensive Database Seeding

**Purpose**: Populates all tables with realistic test data including assets, verification cycles, and verifications.

**Usage**:
```bash
poetry run python seed_database_full.py
```

**What it creates**:
- **11 Assets**: AST001-AST010 from CSV, plus AST011 (new asset discovered)
- **3 Verification Cycles**:
  - Q1-2024: LOCKED cycle with 8 complete verifications
  - Q2-2024: LOCKED cycle with mixed statuses (verified, discrepancies, not found)
  - Q3-2024: ACTIVE cycle with 6 partial verifications
- **22 Asset Verifications**: Various statuses, conditions, and sources

**Scenarios included**:
- Verified assets (GOOD, NEEDS_REPAIR, DAMAGED conditions)
- Assets with discrepancies
- Assets not found during verification
- New assets discovered during audits
- Self-reported vs auditor-verified
- Historical vs current cycle data

**When to use**:
- Setting up a development environment
- Manual testing of the full application
- Demonstrating the system with realistic data

---

### 2. `seed_database.py` - Basic Asset Seeding

**Purpose**: Populates only the assets table with sample data from CSV.

**Usage**:
```bash
poetry run python seed_database.py
```

**What it creates**:
- **10 Assets** from `tests/sample_assets.csv`

**When to use**:
- When you only need asset data without cycles or verifications
- Quick setup for testing asset-related endpoints

---

### 3. `check_all_tables.py` - Database Inspector

**Purpose**: Displays all data in your database in a readable format.

**Usage**:
```bash
poetry run python check_all_tables.py
```

**What it shows**:
- Total count of assets, cycles, and verifications
- All assets with their codes and names
- All verification cycles with their status
- Sample verifications with details
- Statistics by cycle (verified, discrepancies, not found, new assets)

**When to use**:
- Verifying that seeding worked correctly
- Checking current database state
- Debugging data issues
- Understanding what data exists before manual testing

---

### 4. `check_db.py` - Database Connection Tester

**Purpose**: Tests database connectivity and shows basic information.

**Usage**:
```bash
poetry run python check_db.py
```

**What it checks**:
- Async database connection
- Sync database connection
- Tables that exist
- Sample asset data

**When to use**:
- Verifying database connection after setup
- Troubleshooting connection issues
- Confirming database is accessible

---

### 5. `quick_check.py` - Quick Asset Counter

**Purpose**: Quickly check how many assets are in the database.

**Usage**:
```bash
poetry run python quick_check.py
```

**When to use**:
- Quick verification after operations
- Simple health check

## Development

### Testing

Run all tests:
```bash
poetry run pytest tests/ -v
```

Run specific test:
```bash
poetry run pytest tests/test_endpoints.py::test_create_and_list_cycle -v
```

**Important**: Tests automatically clean up after themselves. They:
1. Drop all tables before tests
2. Create fresh tables
3. Seed sample data from CSV
4. Run tests
5. Drop all tables after tests (cleanup)

This means your database will be **empty after tests run**. This is correct behavior to ensure test isolation. If you want persistent data for development, run the seed scripts after testing.

### Database Migrations

For production, use Alembic for database migrations:

```bash
# Initialize Alembic (first time only)
poetry run alembic init alembic

# Create migration
poetry run alembic revision --autogenerate -m "description"

# Apply migration
poetry run alembic upgrade head
```

Currently, the seed scripts use `Base.metadata.create_all()` for development convenience.

## Data Models

### Asset
- `id`: Primary key
- `asset_code`: Unique asset identifier (e.g., "AST001")
- `name`: Asset name/description
- `is_active`: Whether asset is active

### VerificationCycle
- `id`: Primary key
- `tag`: Cycle identifier (e.g., "Q1-2024")
- `status`: ACTIVE or LOCKED
- `created_at`: When cycle was created
- `locked_at`: When cycle was locked (if applicable)

### AssetVerification
- `id`: Primary key
- `asset_id`: Foreign key to Asset
- `cycle_id`: Foreign key to VerificationCycle
- `performed_by`: User who performed verification
- `source`: SELF, AUDITOR, or OVERRIDDEN
- `status`: VERIFIED, DISCREPANCY, NOT_FOUND, or NEW_ASSET
- `condition`: GOOD, NEEDS_REPAIR, or DAMAGED
- `location_lat/lng`: GPS coordinates (optional)
- `photos`: Photo references (optional)
- `notes`: Additional notes (optional)
- `created_at`: When verification was created
- `verified_at`: When verification was completed

## Dependencies

### Core
- **fastapi**: Web framework for building APIs
- **uvicorn**: ASGI server for running FastAPI
- **sqlmodel**: SQL database ORM with Pydantic integration
- **asyncpg**: Async PostgreSQL driver
- **psycopg2-binary**: Sync PostgreSQL driver (for scripts)
- **pydantic-settings**: Settings management
- **python-dotenv**: Environment variable loading

### Development
- **pytest**: Testing framework
- **pytest-asyncio**: Async testing support
- **httpx**: HTTP client for testing

## Environment Variables

Create a `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Debug mode
DEBUG=True
```

## Common Workflows

### Starting Fresh Development
```bash
# 1. Install dependencies
poetry install

# 2. Create database
createdb fixed_asset_db

# 3. Seed with full data
poetry run python seed_database_full.py

# 4. Start server
poetry run uvicorn main:app --reload

# 5. Open browser to http://localhost:8000/docs
```

### Running Tests
```bash
# Run tests (will clean up after)
poetry run pytest tests/ -v

# If you want data for manual testing after tests
poetry run python seed_database_full.py
```

### Checking Database State
```bash
# View all data
poetry run python check_all_tables.py

# Quick asset count
poetry run python quick_check.py
```

### Resetting Database
```bash
# Drop and recreate (PostgreSQL)
dropdb fixed_asset_db && createdb fixed_asset_db

# Seed fresh data
poetry run python seed_database_full.py
```

## License

MIT
