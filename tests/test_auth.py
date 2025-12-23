import pytest


@pytest.mark.anyio
async def test_login_with_form_data(async_client):
    """Test OAuth2 compatible login endpoint"""
    resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "adminpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_with_json(async_client):
    """Test JSON login endpoint"""
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "admin@test.com", "password": "adminpass"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.anyio
async def test_login_invalid_credentials(async_client):
    """Test login with wrong password"""
    resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]


@pytest.mark.anyio
async def test_login_nonexistent_user(async_client):
    """Test login with non-existent email"""
    resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_refresh_token(async_client):
    """Test token refresh endpoint"""
    # First login to get tokens
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "admin@test.com", "password": "adminpass"}
    )
    assert resp.status_code == 200
    tokens = resp.json()

    # Use refresh token to get new tokens
    resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


@pytest.mark.anyio
async def test_refresh_token_invalid(async_client):
    """Test refresh with invalid token"""
    resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_get_current_user(async_client, admin_headers):
    """Test getting current user profile"""
    resp = await async_client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "ADMIN"
    assert data["full_name"] == "Test Admin"
    assert "id" in data
    assert "is_active" in data


@pytest.mark.anyio
async def test_get_current_user_unauthorized(async_client):
    """Test getting current user without authentication"""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_update_current_user(async_client, admin_headers):
    """Test updating current user profile"""
    resp = await async_client.put(
        "/api/v1/auth/me",
        json={"full_name": "Updated Admin Name"},
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["full_name"] == "Updated Admin Name"


@pytest.mark.anyio
async def test_change_password(async_client):
    """Test changing password"""
    # Login with owner credentials
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "owner@test.com", "password": "ownerpass"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change password
    resp = await async_client.post(
        "/api/v1/auth/me/password",
        json={
            "current_password": "ownerpass",
            "new_password": "newownerpass123"
        },
        headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert "Password changed successfully" in resp.json()["message"]

    # Verify old password no longer works
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "owner@test.com", "password": "ownerpass"}
    )
    assert resp.status_code == 401

    # Verify new password works
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "owner@test.com", "password": "newownerpass123"}
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_change_password_wrong_current(async_client, auditor_headers):
    """Test change password with wrong current password"""
    resp = await async_client.post(
        "/api/v1/auth/me/password",
        json={
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        },
        headers=auditor_headers
    )
    assert resp.status_code == 400
    assert "Current password is incorrect" in resp.json()["detail"]


# Admin User Management Endpoints

@pytest.mark.anyio
async def test_list_users_admin(async_client, admin_headers):
    """Test admin listing all users"""
    resp = await async_client.get("/api/v1/auth/users", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "users" in data
    assert "total" in data
    assert len(data["users"]) >= 3  # admin, auditor, owner from seed


@pytest.mark.anyio
async def test_list_users_non_admin_forbidden(async_client, auditor_headers, owner_headers):
    """Test that non-admins cannot list users"""
    resp = await async_client.get("/api/v1/auth/users", headers=auditor_headers)
    assert resp.status_code == 403

    resp = await async_client.get("/api/v1/auth/users", headers=owner_headers)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_create_user_admin(async_client, admin_headers):
    """Test admin creating a new user"""
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "newuser@test.com",
            "password": "newuserpass123",
            "full_name": "New Test User",
            "role": "VIEWER"
        },
        headers=admin_headers
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New Test User"
    assert data["role"] == "VIEWER"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_create_user_duplicate_email(async_client, admin_headers):
    """Test creating user with existing email"""
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin@test.com",  # Already exists
            "password": "password123",
            "full_name": "Duplicate User",
            "role": "VIEWER"
        },
        headers=admin_headers
    )
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


@pytest.mark.anyio
async def test_get_user_by_id_admin(async_client, admin_headers):
    """Test admin getting user by ID"""
    # First get list to find a user ID
    resp = await async_client.get("/api/v1/auth/users", headers=admin_headers)
    users = resp.json()["users"]
    user_id = users[0]["id"]

    resp = await async_client.get(f"/api/v1/auth/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == user_id


@pytest.mark.anyio
async def test_get_user_not_found(async_client, admin_headers):
    """Test getting non-existent user"""
    resp = await async_client.get("/api/v1/auth/users/99999", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_user_admin(async_client, admin_headers):
    """Test admin updating another user"""
    # Create a user to update
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "updateme@test.com",
            "password": "password123",
            "full_name": "Update Me",
            "role": "VIEWER"
        },
        headers=admin_headers
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Update the user
    resp = await async_client.put(
        f"/api/v1/auth/users/{user_id}",
        json={
            "full_name": "Updated Name",
            "role": "AUDITOR"
        },
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["full_name"] == "Updated Name"
    assert data["role"] == "AUDITOR"


@pytest.mark.anyio
async def test_reset_user_password_admin(async_client, admin_headers):
    """Test admin resetting user password"""
    # Create a user
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "resetme@test.com",
            "password": "oldpassword",
            "full_name": "Reset Me",
            "role": "VIEWER"
        },
        headers=admin_headers
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Reset password
    resp = await async_client.post(
        f"/api/v1/auth/users/{user_id}/reset-password",
        json={"new_password": "newresetpass123"},
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    assert "Password reset successfully" in resp.json()["message"]

    # Verify old password no longer works
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "resetme@test.com", "password": "oldpassword"}
    )
    assert resp.status_code == 401

    # Verify new password works
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "resetme@test.com", "password": "newresetpass123"}
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_deactivate_user_admin(async_client, admin_headers):
    """Test admin deactivating a user"""
    # Create a user
    resp = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "deactivateme@test.com",
            "password": "password123",
            "full_name": "Deactivate Me",
            "role": "VIEWER"
        },
        headers=admin_headers
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Deactivate user
    resp = await async_client.delete(
        f"/api/v1/auth/users/{user_id}",
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    assert "deactivated" in resp.json()["message"]

    # Verify deactivated user cannot login
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "deactivateme@test.com", "password": "password123"}
    )
    assert resp.status_code == 401
    assert "disabled" in resp.json()["detail"]


@pytest.mark.anyio
async def test_admin_cannot_deactivate_self(async_client, admin_headers):
    """Test that admin cannot deactivate themselves"""
    # Get admin user ID
    resp = await async_client.get("/api/v1/auth/me", headers=admin_headers)
    admin_id = resp.json()["id"]

    resp = await async_client.delete(
        f"/api/v1/auth/users/{admin_id}",
        headers=admin_headers
    )
    assert resp.status_code == 400
    assert "Cannot deactivate yourself" in resp.json()["detail"]


@pytest.mark.anyio
async def test_non_admin_cannot_change_role(async_client):
    """Test that non-admin users cannot change their role"""
    # Login as auditor
    resp = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": "auditor@test.com", "password": "auditorpass"}
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to change own role
    resp = await async_client.put(
        "/api/v1/auth/me",
        json={"role": "ADMIN"},
        headers=headers
    )
    assert resp.status_code == 403
    assert "Cannot change role" in resp.json()["detail"]
