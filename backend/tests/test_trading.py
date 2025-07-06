import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestTrading:
    """Test cases for trading endpoints"""

    def test_place_order_success(self, client: TestClient, auth_headers, sample_order_data, mock_broker_api):
        """Test successful order placement"""
        response = client.post("/v1/trading/orders", json=sample_order_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "order_id" in data
        assert data["symbol"] == sample_order_data["symbol"]
        assert data["side"] == sample_order_data["side"]
        assert data["type"] == sample_order_data["type"]
        assert data["quantity"] == sample_order_data["quantity"]

    def test_place_order_unauthorized(self, client: TestClient, sample_order_data):
        """Test order placement without authentication"""
        response = client.post("/v1/trading/orders", json=sample_order_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_place_order_invalid_symbol(self, client: TestClient, auth_headers, sample_order_data):
        """Test order placement with invalid symbol"""
        sample_order_data["symbol"] = ""
        response = client.post("/v1/trading/orders", json=sample_order_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_place_order_invalid_quantity(self, client: TestClient, auth_headers, sample_order_data):
        """Test order placement with invalid quantity"""
        sample_order_data["quantity"] = 0
        response = client.post("/v1/trading/orders", json=sample_order_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_place_order_broker_error(self, client: TestClient, auth_headers, sample_order_data):
        """Test order placement when broker returns error"""
        with patch('services.broker_service.AlpacaBroker.place_order') as mock_place_order:
            mock_place_order.side_effect = Exception("Broker error")
            
            response = client.post("/v1/trading/orders", json=sample_order_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_get_orders_success(self, client: TestClient, auth_headers):
        """Test getting user orders"""
        response = client.get("/v1/trading/orders", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["orders"], list)
        assert "total" in data

    def test_get_orders_with_filters(self, client: TestClient, auth_headers):
        """Test getting orders with filters"""
        params = {
            "symbol": "AAPL",
            "status": "filled",
            "limit": 10
        }
        response = client.get("/v1/trading/orders", params=params, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK

    def test_get_order_by_id_success(self, client: TestClient, auth_headers, test_user, db_session):
        """Test getting specific order by ID"""
        from models.order import Order
        
        # Create test order
        order = Order(
            user_id=test_user.id,
            symbol="AAPL",
            side="buy",
            type="market",
            quantity=100,
            status="filled"
        )
        db_session.add(order)
        db_session.commit()
        
        response = client.get(f"/v1/trading/orders/{order.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(order.id)

    def test_get_order_by_id_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent order"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/v1/trading/orders/{fake_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_order_success(self, client: TestClient, auth_headers, test_user, db_session, mock_broker_api):
        """Test successful order cancellation"""
        from models.order import Order
        
        # Create test order
        order = Order(
            user_id=test_user.id,
            symbol="AAPL",
            side="buy",
            type="limit",
            quantity=100,
            price=150.0,
            status="pending"
        )
        db_session.add(order)
        db_session.commit()
        
        response = client.delete(f"/v1/trading/orders/{order.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_order_already_filled(self, client: TestClient, auth_headers, test_user, db_session):
        """Test cancelling already filled order"""
        from models.order import Order
        
        # Create filled order
        order = Order(
            user_id=test_user.id,
            symbol="AAPL",
            side="buy",
            type="market",
            quantity=100,
            status="filled"
        )
        db_session.add(order)
        db_session.commit()
        
        response = client.delete(f"/v1/trading/orders/{order.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_positions_success(self, client: TestClient, auth_headers):
        """Test getting user positions"""
        response = client.get("/v1/trading/positions", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["positions"], list)
        assert "total" in data

    def test_get_position_by_symbol_success(self, client: TestClient, auth_headers, test_user, db_session):
        """Test getting position for specific symbol"""
        from models.position import Position
        
        # Create test position
        position = Position(
            user_id=test_user.id,
            symbol="AAPL",
            quantity=100,
            average_price=150.0
        )
        db_session.add(position)
        db_session.commit()
        
        response = client.get(f"/v1/trading/positions/AAPL", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["symbol"] == "AAPL"

    def test_get_position_not_found(self, client: TestClient, auth_headers):
        """Test getting position for non-existent symbol"""
        response = client.get("/v1/trading/positions/NONEXISTENT", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_close_position_success(self, client: TestClient, auth_headers, test_user, db_session, mock_broker_api):
        """Test closing a position"""
        from models.position import Position
        
        # Create test position
        position = Position(
            user_id=test_user.id,
            symbol="AAPL",
            quantity=100,
            average_price=150.0
        )
        db_session.add(position)
        db_session.commit()
        
        response = client.post(f"/v1/trading/positions/AAPL/close", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK

    def test_get_account_info_success(self, client: TestClient, auth_headers, mock_broker_api):
        """Test getting account information"""
        response = client.get("/v1/trading/account", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cash" in data
        assert "portfolio_value" in data
        assert "buying_power" in data

    def test_get_trading_history_success(self, client: TestClient, auth_headers):
        """Test getting trading history"""
        response = client.get("/v1/trading/history", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["trades"], list)

    def test_get_trading_performance_success(self, client: TestClient, auth_headers):
        """Test getting trading performance metrics"""
        response = client.get("/v1/trading/performance", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_return" in data
        assert "win_rate" in data
        assert "sharpe_ratio" in data

    def test_risk_check_order_success(self, client: TestClient, auth_headers, sample_order_data):
        """Test risk checking an order"""
        response = client.post("/v1/trading/risk-check", json=sample_order_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "risk_score" in data
        assert "recommendations" in data

    def test_risk_check_high_risk_order(self, client: TestClient, auth_headers, sample_order_data):
        """Test risk checking a high-risk order"""
        # Make order very large
        sample_order_data["quantity"] = 100000
        
        response = client.post("/v1/trading/risk-check", json=sample_order_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["risk_score"] > 0.5  # Should be high risk