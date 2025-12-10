import os
import csv
import pytest
from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification

@pytest.mark.anyio
async def test_create_and_list_cycle(async_client):
    payload = {"tag": "TEST-CYCLE-1"}
    resp = await async_client.post("/api/v1/cycles", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["tag"] == "TEST-CYCLE-1"
    cycle_id = data["id"]

    resp = await async_client.get("/api/v1/cycles")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert any(item["id"] == cycle_id for item in items)

@pytest.mark.anyio
async def test_lookup_asset_not_found(async_client):
    """Test looking up an asset that doesn't exist"""
    resp = await async_client.post("/api/v1/cycles", json={"tag":"TEST-CYCLE-LOOKUP"})
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Try to lookup a non-existent asset
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=NOPE&cycle_id={cycle_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found"] is True

    # Verify we can lookup an existing asset from CSV
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=AST001&cycle_id={cycle_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found"] is False
    assert body["asset"]["asset_code"] == "AST001"
    assert "Laptop" in body["asset"]["name"]

@pytest.mark.anyio
async def test_search_and_new_asset_flow(async_client):
    """Test searching for assets and creating new ones"""
    resp = await async_client.post("/api/v1/cycles", json={"tag":"TEST-CYCLE-SEARCH"})
    assert resp.status_code == 201
    cycle_id = resp.json()["id"]

    # Search for "lap" should find "Dell Laptop" from seeded data
    resp = await async_client.get("/api/v1/verification/assets/search?q=lap")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert isinstance(results, list)
    assert len(results) > 0, "Should find at least one laptop in seeded data"

    # Verify we found the Dell Laptop
    laptop_found = any("Laptop" in r["name"] for r in results)
    assert laptop_found, "Should find a laptop in search results"

    # Test creating a new asset
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
    resp = await async_client.post("/api/v1/verification/assets/new", json=new_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["asset_code"] == "TEST-NEW-001"
    assert "verification_id" in data

    # Verify the new asset can be looked up
    resp = await async_client.get(f"/api/v1/verification/assets/lookup?asset_code=TEST-NEW-001&cycle_id={cycle_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found"] is False
    assert body["already_verified"] is True
