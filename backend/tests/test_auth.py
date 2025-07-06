import pytest
from fastapi import status
from fastapi.testclient import TestClient

class TestAuthentication:
    """Test cases for authentication endpoints"""

    def test_register_user_success(self, client: TestClient, test_user_data):
        """Test successful user registration"""
        response = client.post("/v1/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["first_name"] == test_user_data["first_name"]
        assert data["user"]["last_name"] == test_user_data["last_name"]
        assert "password" not in data["user"]

    def test_register_user_duplicate_email(self, client: TestClient, test_user_data, test_user):
        """Test registration with duplicate email"""
        response = client.post("/v1/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already registered" in data["detail"].lower()

    def test_register_user_invalid_email(self, client: TestClient, test_user_data):
        """Test registration with invalid email"""
        test_user_data["email"] = "invalid-email"
        response = client.post("/v1/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_weak_password(self, client: TestClient, test_user_data):
        """Test registration with weak password"""
        test_user_data["password"] = "123"
        response = client.post("/v1/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_success(self, client: TestClient, test_user, test_user_data):
        """Test successful login"""
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["id"] == str(test_user.id)
        assert data["tokens"]["access_token"]
        assert data["tokens"]["refresh_token"]

    def test_login_invalid_email(self, client: TestClient):
        """Test login with invalid email"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        response = client.post("/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_password(self, client: TestClient, test_user, test_user_data):
        """Test login with invalid password"""
        login_data = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client: TestClient, test_user, test_user_data, db_session):
        """Test login with inactive user"""
        # Deactivate user
        test_user.is_active = False
        db_session.commit()
        
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self, client: TestClient, test_user):
        """Test successful token refresh"""
        from services.auth_service import create_refresh_token
        
        refresh_token = create_refresh_token(data={"sub": str(test_user.id)})
        response = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self, client: TestClient):
        """Test token refresh with invalid token"""
        response = client.post("/v1/auth/refresh", json={"refresh_token": "invalid_token"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_success(self, client: TestClient, test_user, auth_headers):
        """Test getting current user information"""
        response = client.get("/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert "password" not in data

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication"""
        response = client.get("/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_success(self, client: TestClient, auth_headers):
        """Test successful logout"""
        response = client.post("/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Successfully logged out"

    def test_change_password_success(self, client: TestClient, test_user, auth_headers, test_user_data):
        """Test successful password change"""
        change_data = {
            "current_password": test_user_data["password"],
            "new_password": "newpassword123"
        }
        response = client.post("/v1/auth/change-password", json=change_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_current(self, client: TestClient, auth_headers):
        """Test password change with wrong current password"""
        change_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        response = client.post("/v1/auth/change-password", json=change_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_forgot_password_success(self, client: TestClient, test_user):
        """Test forgot password request"""
        response = client.post("/v1/auth/forgot-password", json={"email": test_user.email})
        
        assert response.status_code == status.HTTP_200_OK

    def test_forgot_password_nonexistent_user(self, client: TestClient):
        """Test forgot password with nonexistent user"""
        response = client.post("/v1/auth/forgot-password", json={"email": "nonexistent@example.com"})
        
        # Should still return 200 for security reasons
        assert response.status_code == status.HTTP_200_OK