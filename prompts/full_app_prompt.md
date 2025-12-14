You are acting as a senior backend engineer reviewing and completing a FastAPI backend for a Fixed Asset Verification system. Carefully read the entire existing codebase before making any changes. Do not assume anything is already implemented unless it is clearly enforced in code and covered by tests. Your goal is to ensure the backend fully and correctly implements the complete verification flow, with audit safety and role-based enforcement.

Cross-check the existing code against every task in the backend task list below. If a task is fully implemented and correct, leave it unchanged. If a task is partially implemented, fix and complete it. If a task is missing, implement it fully, including database models, schemas, endpoints, services, permission checks, and tests. If implementing a missing task requires changes to existing database models, make those changes safely, provide migrations, update dependent code, and update tests. Never remove audit history, never delete verification records, and never bypass cycle locking or role checks.

Reuse existing project patterns and structure. Do not rewrite code unnecessarily. All business rules must be enforced server-side. If behavior is ambiguous, choose the safest audit-compliant implementation.

After completing the work, ensure all tests pass and the system is consistent, cycle-centric, and production-ready.

Backend Task List (Authoritative)
Foundation & Infrastructure

Project structure with api, core, models, schemas, services, repositories, db, tests

Environment-based configuration (local/dev/prod)

Database URL composition

Email configuration

File storage configuration (local/S3-ready)

Authentication & Authorization

User model with roles (ADMIN, AUDITOR, OWNER, VIEWER)

Password hashing and login

JWT authentication

Token expiry handling

Role-based access enforcement

Asset ownership enforcement

Read vs write permission separation

Asset Master Data

Asset ORM model

Unique asset_code constraint

Owner foreign key

Soft delete support

Asset listing APIs (role-filtered)

Asset retrieval by ID

Manual asset search support

Asset Register Upload

Excel upload endpoint

File and schema validation

Merge logic by asset_code

Idempotent imports

Transaction safety

Auto-create asset owners

Assign OWNER role

Default password generation

Force password change on first login

Verification Cycle Management

VerificationCycle ORM model

Status enum: DRAFT, ACTIVE, LOCKED

Create cycle

Activate cycle

Lock cycle

Unlock cycle

List cycles

Get active cycle

Enforce valid lifecycle transitions

Prevent edits when LOCKED

Notifications

Email notification on cycle start

Admin notification on cycle lock

Async email sending

Mock email backend for dev/tests

Asset Verification Core

AssetVerification ORM model

FK to Asset

FK to VerificationCycle

Unique constraint (asset_id, cycle_id)

Source enum: SELF, AUDITOR, OVERRIDDEN

Verification status/condition

Geo-coordinates

Verified by and timestamp

Full audit trail preservation

Self Verification (Asset Owner)

Self-verification endpoint

Active cycle enforcement

Asset ownership enforcement

Prevent duplicate verification

Block when cycle is LOCKED

Capture status, condition, remarks, photos, geo-tag

Auditor Direct Verification

Auditor verification endpoint

Active cycle enforcement

Prevent duplicate verification

Barcode/manual asset lookup

Missing asset handling

Override Workflow

Override endpoint

Auditor-only access

Active cycle required

Override reason mandatory

Preserve original verification

Record override metadata

Photo & File Handling

File upload endpoint

File type validation

Storage abstraction

Verification linkage

Read-only access after cycle lock

Editing & Re-verification Rules

Allow edits only when cycle ACTIVE

Block edits when cycle LOCKED

Admin/Auditor edit scope enforcement

Optional change history

Dashboards & Aggregates

Total assets

Verified count

Pending count

Self verified count

Auditor verified count

Overridden count

Not found count

Dashboard summary endpoint

Owner-wise stats

Category-wise stats

Cycle-wise stats

Reporting & Exports

Cycle-based report endpoint

Owner and source filters

Excel export

CSV export

Column consistency with asset register

Historical Data Access

View past cycles

Read-only access for locked cycles

Historical verification visibility

Data Integrity & Safety

Database transactions

Foreign key enforcement

Unique constraints

Soft delete enforcement

No destructive deletes on audit tables

Error Handling & Validation

Centralized exception handling

Business-rule-specific errors

Consistent HTTP status codes

Logging & Audit

Action logging for verification

Action logging for overrides

Action logging for lock/unlock

Actor and timestamp capture

Separation of debug vs audit logs

Testing

Unit tests for:

Cycle state transitions

Permission enforcement

Override logic

Duplicate prevention

Integration tests for:

End-to-end verification flow

Lock enforcement

Role-based access

Performance & Scalability

Proper indexing

Pagination

Large asset list handling

Safe bulk operations

Operational Readiness

Health check endpoint

Database migrations

Seed data for development

Admin bootstrap user

Documentation

OpenAPI completeness

State machine documentation

Role capability matrix

API usage examples

Ensure that every item above is either already correctly implemented or fully implemented by you. Do not leave placeholders or TODOs. The final backend must be cycle-centric, audit-safe, and compliant with the complete fixed asset verification flow.