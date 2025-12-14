import pytest


@pytest.mark.anyio
async def test_create_and_list_cycle(async_client, admin_headers):
    payload = {"tag": "TEST-CYCLE-1"}
    resp = await async_client.post("/api/v1/cycles", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["tag"] == "TEST-CYCLE-1"
    cycle_id = data["id"]

    resp = await async_client.get("/api/v1/cycles", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert any(item["id"] == cycle_id for item in items)


@pytest.mark.anyio
async def test_lookup_asset_not_found(async_client, admin_headers):
    """Test looking up an asset that doesn't exist"""
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-LOOKUP"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Try to lookup a non-existent asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=NOPE&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found"] is True

    # Verify we can lookup an existing asset from CSV
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST001&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found"] is False
    assert body["asset"]["asset_code"] == "AST001"
    assert "Laptop" in body["asset"]["name"]


@pytest.mark.anyio
async def test_search_and_new_asset_flow(async_client, admin_headers):
    """Test searching for assets and creating new ones"""
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-SEARCH"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Search for "lap" should find "Dell Laptop" from seeded data
    resp = await async_client.get("/api/v1/verification/assets/search?q=lap", headers=admin_headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert isinstance(results, list)
    assert len(results) > 0, "Should find at least one laptop in seeded data"

    # Verify we found the Dell Laptop
    laptop_found = any("Laptop" in r["name"] for r in results)
    assert laptop_found, "Should find a laptop in search results"

    # Test creating a new asset (requires AUDITOR or ADMIN role)
    new_payload = {
        "asset_code": "TEST-NEW-001",
        "name": "Test New Asset",
        "cycle_id": cycle_id,
        "performed_by": "test-runner",
        "source": "AUDITOR",
        "status": "NEW_ASSET",
        "photos": ["s3://dummy/key1.jpg"],
        "location_lat": 12.34,
        "location_lng": 56.78,
        "notes": "seeded during test"
    }
    resp = await async_client.post("/api/v1/verification/assets/new", json=new_payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["asset_code"] == "TEST-NEW-001"
    assert "verification_id" in data

    # Verify the new asset can be looked up
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=TEST-NEW-001&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found"] is False
    assert body["already_verified"] is True


@pytest.mark.anyio
async def test_duplicate_detection(async_client, admin_headers):
    """Test that duplicate verifications are detected and handled correctly"""
    # Create a cycle
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-DUP"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Get an existing asset (AST001 from seed)
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST001&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    asset_id = resp.json()["asset"]["id"]

    # Create first verification
    payload = {
        "performed_by": "tester",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD",
        "notes": "First verification"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload,
        headers=admin_headers
    )
    assert resp.status_code == 201, resp.text

    # Try to create duplicate (should get 200 with duplicate info)
    payload2 = {
        "performed_by": "tester2",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD",
        "notes": "Attempted duplicate"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload2,
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["duplicate"] is True
    assert "existing_verification" in data

    # Force create with allow_duplicate=true
    payload3 = {
        "performed_by": "tester3",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD",
        "notes": "Forced duplicate",
        "allow_duplicate": True
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload3,
        headers=admin_headers
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.anyio
async def test_override_flow(async_client, admin_headers):
    """Test creating verification overrides"""
    # Create a cycle
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-OVERRIDE"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Get an existing asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST002&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    asset_id = resp.json()["asset"]["id"]

    # Create initial verification
    payload = {
        "performed_by": "original-tester",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD",
        "notes": "Original verification"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload,
        headers=admin_headers
    )
    assert resp.status_code == 201
    original_id = resp.json()["id"]

    # Create override (requires AUDITOR or ADMIN)
    override_payload = {
        "performed_by": "manager",
        "source": "OVERRIDDEN",
        "status": "DISCREPANCY",
        "condition": "DAMAGED",
        "notes": "Found damage upon review",
        "override_reason": "Inspector missed visible damage during initial verification"
    }
    resp = await async_client.post(
        f"/api/v1/verification/{original_id}/override",
        json=override_payload,
        headers=admin_headers
    )
    assert resp.status_code == 201, resp.text
    override_data = resp.json()
    assert override_data["source"] == "OVERRIDDEN"
    assert override_data["override_of_verification_id"] == original_id

    # Verify effective is the override
    resp = await async_client.get(f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["effective_verification"]["id"] == override_data["id"]
    assert len(detail["history"]) == 2


@pytest.mark.anyio
async def test_cycle_lock_enforcement(async_client, admin_headers):
    """Test that locked cycles reject modifications"""
    # Create a cycle
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-LOCK"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Get an asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST003&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    asset_id = resp.json()["asset"]["id"]

    # Create verification before lock
    payload = {
        "performed_by": "tester",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload,
        headers=admin_headers
    )
    assert resp.status_code == 201

    # Lock the cycle
    resp = await async_client.post(f"/api/v1/cycles/{cycle_id}/lock", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "LOCKED"

    # Try to create another verification (should fail with 409)
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST004&cycle_id={cycle_id}", headers=admin_headers)
    asset2_id = resp.json()["asset"]["id"]

    payload2 = {
        "performed_by": "tester2",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset2_id}/cycles/{cycle_id}",
        json=payload2,
        headers=admin_headers
    )
    assert resp.status_code == 409, "Should reject verification in locked cycle"

    # Unlock the cycle
    resp = await async_client.post(f"/api/v1/cycles/{cycle_id}/unlock", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    # Now verification should work
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset2_id}/cycles/{cycle_id}",
        json=payload2,
        headers=admin_headers
    )
    assert resp.status_code == 201


@pytest.mark.anyio
async def test_pending_assets(async_client, admin_headers):
    """Test listing assets without verification in a cycle"""
    # Create a cycle
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-PENDING"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Initially all assets should be pending
    resp = await async_client.get(f"/api/v1/verification/pending?cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cycle_id"] == cycle_id
    initial_count = data["pending_count"]
    assert initial_count > 0, "Should have pending assets from seed data"

    # Verify one asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST004&cycle_id={cycle_id}", headers=admin_headers)
    asset_id = resp.json()["asset"]["id"]

    payload = {
        "performed_by": "tester",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload,
        headers=admin_headers
    )
    assert resp.status_code == 201

    # Check pending count decreased
    resp = await async_client.get(f"/api/v1/verification/pending?cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    new_count = resp.json()["pending_count"]
    assert new_count == initial_count - 1


@pytest.mark.anyio
async def test_asset_cycle_detail_history(async_client, admin_headers):
    """Test getting asset-cycle detail with history"""
    # Create a cycle
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-CYCLE-HISTORY"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Get an asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST005&cycle_id={cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    asset_id = resp.json()["asset"]["id"]

    # Check empty history initially
    resp = await async_client.get(f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["effective_verification"] is None
    assert data["history"] == []

    # Create first verification
    payload1 = {
        "performed_by": "tester1",
        "source": "SELF",
        "status": "VERIFIED",
        "condition": "GOOD"
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload1,
        headers=admin_headers
    )
    assert resp.status_code == 201

    # Create second verification (forced duplicate)
    payload2 = {
        "performed_by": "tester2",
        "source": "AUDITOR",
        "status": "DISCREPANCY",
        "condition": "DAMAGED",
        "allow_duplicate": True
    }
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload2,
        headers=admin_headers
    )
    assert resp.status_code == 201
    v2_id = resp.json()["id"]

    # Check history has both
    resp = await async_client.get(f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["history"]) == 2
    # Latest (v2) should be effective since no override
    assert data["effective_verification"]["id"] == v2_id


@pytest.mark.anyio
async def test_integration_full_workflow(async_client, admin_headers):
    """
    Integration test: create cycle, seed assets, verify, override,
    lock attempt, verify counts.
    """
    # 1. Create cycle
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-INTEGRATION"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # 2. Check initial pending count
    resp = await async_client.get(f"/api/v1/verification/pending?cycle_id={cycle_id}", headers=admin_headers)
    initial_pending = resp.json()["pending_count"]

    # 3. Lookup and verify first asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST006&cycle_id={cycle_id}", headers=admin_headers)
    asset1_id = resp.json()["asset"]["id"]

    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset1_id}/cycles/{cycle_id}",
        json={"source": "SELF", "status": "VERIFIED", "condition": "GOOD"},
        headers=admin_headers
    )
    assert resp.status_code == 201
    v1_id = resp.json()["id"]

    # 4. Create override for first verification
    resp = await async_client.post(
        f"/api/v1/verification/{v1_id}/override",
        json={
            "source": "OVERRIDDEN",
            "status": "NEEDS_REPAIR",
            "condition": "NEEDS_REPAIR",
            "override_reason": "Found issues on secondary inspection"
        },
        headers=admin_headers
    )
    assert resp.status_code == 201
    override_id = resp.json()["id"]

    # 5. Verify second asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST007&cycle_id={cycle_id}", headers=admin_headers)
    asset2_id = resp.json()["asset"]["id"]

    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset2_id}/cycles/{cycle_id}",
        json={"source": "SELF", "status": "NOT_FOUND"},
        headers=admin_headers
    )
    assert resp.status_code == 201

    # 6. Verify pending count decreased by 2
    resp = await async_client.get(f"/api/v1/verification/pending?cycle_id={cycle_id}", headers=admin_headers)
    new_pending = resp.json()["pending_count"]
    assert new_pending == initial_pending - 2

    # 7. Verify effective for asset1 is the override
    resp = await async_client.get(f"/api/v1/verification/assets/{asset1_id}/cycles/{cycle_id}", headers=admin_headers)
    detail = resp.json()
    assert detail["effective_verification"]["id"] == override_id
    assert detail["effective_verification"]["source"] == "OVERRIDDEN"
    assert len(detail["history"]) == 2


@pytest.mark.anyio
async def test_dashboard_endpoints(async_client, admin_headers):
    """Test dashboard aggregate endpoints"""
    # Create a cycle for dashboard testing
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-DASHBOARD"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Test overview endpoint
    resp = await async_client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert resp.status_code == 200
    overview = resp.json()
    assert "total_assets" in overview
    assert "active_assets" in overview
    assert "total_cycles" in overview

    # Test cycle-specific dashboard
    resp = await async_client.get(f"/api/v1/dashboard/cycles/{cycle_id}", headers=admin_headers)
    assert resp.status_code == 200
    dashboard = resp.json()
    assert dashboard["cycle_id"] == cycle_id
    assert "total_assets" in dashboard
    assert "verified_count" in dashboard
    assert "pending_count" in dashboard
    assert "status_breakdown" in dashboard
    assert "condition_breakdown" in dashboard
    assert "source_breakdown" in dashboard

    # Test cycle stats endpoint
    resp = await async_client.get(f"/api/v1/dashboard/cycles/{cycle_id}/stats", headers=admin_headers)
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["cycle_id"] == cycle_id
    assert "self_verified_count" in stats
    assert "auditor_verified_count" in stats


@pytest.mark.anyio
async def test_role_based_access(async_client, admin_headers, auditor_headers, owner_headers):
    """Test role-based access control"""
    # Create a cycle (admin only)
    resp = await async_client.post("/api/v1/cycles", json={"tag": "TEST-RBAC"}, headers=admin_headers)
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Auditor should not be able to create cycles
    resp = await async_client.post("/api/v1/cycles", json={"tag": "AUDITOR-CYCLE"}, headers=auditor_headers)
    assert resp.status_code == 403

    # Owner should not be able to create cycles
    resp = await async_client.post("/api/v1/cycles", json={"tag": "OWNER-CYCLE"}, headers=owner_headers)
    assert resp.status_code == 403

    # All roles can view cycles
    resp = await async_client.get("/api/v1/cycles", headers=auditor_headers)
    assert resp.status_code == 200

    resp = await async_client.get("/api/v1/cycles", headers=owner_headers)
    assert resp.status_code == 200

    # Get an asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST008&cycle_id={cycle_id}", headers=admin_headers)
    asset_id = resp.json()["asset"]["id"]

    # Owner can create verifications
    payload = {"source": "SELF", "status": "VERIFIED", "condition": "GOOD"}
    resp = await async_client.post(
        f"/api/v1/verification/assets/{asset_id}/cycles/{cycle_id}",
        json=payload,
        headers=owner_headers
    )
    assert resp.status_code == 201
    verification_id = resp.json()["id"]

    # Owner cannot override (requires AUDITOR or ADMIN)
    override_payload = {
        "source": "OVERRIDDEN",
        "status": "DISCREPANCY",
        "override_reason": "Test override"
    }
    resp = await async_client.post(
        f"/api/v1/verification/{verification_id}/override",
        json=override_payload,
        headers=owner_headers
    )
    assert resp.status_code == 403

    # Auditor can override
    resp = await async_client.post(
        f"/api/v1/verification/{verification_id}/override",
        json=override_payload,
        headers=auditor_headers
    )
    assert resp.status_code == 201
