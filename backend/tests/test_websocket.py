import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import WebSocket

from websocket.connection_manager import ConnectionManager, connection_manager
from websocket.websocket_handler import WebSocketHandler
from websocket.broadcast_service import BroadcastService
from websocket.message_types import WebSocketMessage, MessageType

class TestConnectionManager:
    """Test cases for WebSocket Connection Manager"""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """Test successful WebSocket connection"""
        connection_id = "test_connection_1"
        user_id = "test_user_1"
        
        success = await manager.connect(mock_websocket, connection_id, user_id)
        
        assert success
        assert connection_id in manager.active_connections
        assert user_id in manager.user_connections
        assert connection_id in manager.user_connections[user_id]
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_anonymous(self, manager, mock_websocket):
        """Test anonymous WebSocket connection"""
        connection_id = "test_connection_2"
        
        success = await manager.connect(mock_websocket, connection_id)
        
        assert success
        assert connection_id in manager.active_connections
        assert connection_id in manager.connection_metadata

    def test_disconnect(self, manager, mock_websocket):
        """Test WebSocket disconnection"""
        connection_id = "test_connection_3"
        user_id = "test_user_3"
        
        # First connect
        asyncio.run(manager.connect(mock_websocket, connection_id, user_id))
        
        # Then disconnect
        manager.disconnect(connection_id)
        
        assert connection_id not in manager.active_connections
        assert user_id not in manager.user_connections or connection_id not in manager.user_connections.get(user_id, set())

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self, manager, mock_websocket):
        """Test sending personal message"""
        connection_id = "test_connection_4"
        
        await manager.connect(mock_websocket, connection_id)
        
        message = {"type": "test", "data": "hello"}
        success = await manager.send_personal_message(connection_id, message)
        
        assert success
        mock_websocket.send_text.assert_called_once_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_send_personal_message_invalid_connection(self, manager):
        """Test sending message to invalid connection"""
        message = {"type": "test", "data": "hello"}
        success = await manager.send_personal_message("invalid_connection", message)
        
        assert not success

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """Test sending message to user"""
        connection_id = "test_connection_5"
        user_id = "test_user_5"
        
        await manager.connect(mock_websocket, connection_id, user_id)
        
        message = {"type": "test", "data": "hello"}
        count = await manager.send_to_user(user_id, message)
        
        assert count == 1
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_to_channel(self, manager, mock_websocket):
        """Test channel subscription"""
        connection_id = "test_connection_6"
        channel = "market_data.AAPL"
        
        await manager.connect(mock_websocket, connection_id)
        
        success = await manager.subscribe_to_channel(connection_id, channel)
        
        assert success
        assert channel in manager.channel_subscriptions
        assert connection_id in manager.channel_subscriptions[channel]

    @pytest.mark.asyncio
    async def test_unsubscribe_from_channel(self, manager, mock_websocket):
        """Test channel unsubscription"""
        connection_id = "test_connection_7"
        channel = "market_data.AAPL"
        
        await manager.connect(mock_websocket, connection_id)
        await manager.subscribe_to_channel(connection_id, channel)
        
        success = await manager.unsubscribe_from_channel(connection_id, channel)
        
        assert success
        assert channel not in manager.channel_subscriptions or connection_id not in manager.channel_subscriptions.get(channel, set())

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager, mock_websocket):
        """Test broadcasting to channel"""
        connection_id = "test_connection_8"
        channel = "market_data.AAPL"
        
        await manager.connect(mock_websocket, connection_id)
        await manager.subscribe_to_channel(connection_id, channel)
        
        message = {"type": "quote_update", "symbol": "AAPL", "price": 150.0}
        count = await manager.broadcast_to_channel(channel, message)
        
        assert count == 1
        mock_websocket.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_join_room(self, manager, mock_websocket):
        """Test joining a room"""
        connection_id = "test_connection_9"
        room_id = "watchlist_123"
        
        await manager.connect(mock_websocket, connection_id)
        
        success = await manager.join_room(connection_id, room_id)
        
        assert success
        assert room_id in manager.room_subscriptions
        assert connection_id in manager.room_subscriptions[room_id]

    @pytest.mark.asyncio
    async def test_leave_room(self, manager, mock_websocket):
        """Test leaving a room"""
        connection_id = "test_connection_10"
        room_id = "watchlist_123"
        
        await manager.connect(mock_websocket, connection_id)
        await manager.join_room(connection_id, room_id)
        
        success = await manager.leave_room(connection_id, room_id)
        
        assert success
        assert room_id not in manager.room_subscriptions or connection_id not in manager.room_subscriptions.get(room_id, set())

    def test_get_connection_stats(self, manager, mock_websocket):
        """Test getting connection statistics"""
        connection_id = "test_connection_11"
        
        asyncio.run(manager.connect(mock_websocket, connection_id))
        
        stats = manager.get_connection_stats()
        
        assert "total_connections" in stats
        assert "authenticated_users" in stats
        assert "active_channels" in stats
        assert "active_rooms" in stats
        assert stats["total_connections"] >= 1

class TestWebSocketHandler:
    """Test cases for WebSocket Handler"""

    @pytest.fixture
    def handler(self):
        return WebSocketHandler()

    @pytest.fixture
    def mock_websocket(self):
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, handler):
        """Test handling ping message"""
        message = WebSocketMessage(
            type="ping",
            data={"timestamp": 1234567890},
            connection_id="test_conn",
            user_id="test_user"
        )
        
        with patch.object(connection_manager, 'send_personal_message') as mock_send:
            mock_send.return_value = True
            await handler._handle_ping(message)
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, handler):
        """Test handling subscribe message"""
        message = WebSocketMessage(
            type="subscribe",
            data={"channel": "market_data.AAPL"},
            connection_id="test_conn"
        )
        
        with patch.object(connection_manager, 'subscribe_to_channel') as mock_subscribe:
            mock_subscribe.return_value = True
            await handler._handle_subscribe(message)
            mock_subscribe.assert_called_once_with("test_conn", "market_data.AAPL")

    @pytest.mark.asyncio
    async def test_handle_get_quote_message(self, handler):
        """Test handling get quote message"""
        message = WebSocketMessage(
            type="get_quote",
            data={"symbol": "AAPL", "request_id": "req_123"},
            connection_id="test_conn"
        )
        
        with patch.object(connection_manager, 'send_personal_message') as mock_send:
            mock_send.return_value = True
            await handler._handle_get_quote(message)
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_place_order_authenticated(self, handler):
        """Test handling place order message with authentication"""
        message = WebSocketMessage(
            type="place_order",
            data={
                "order": {
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "market",
                    "quantity": 100
                },
                "request_id": "req_124"
            },
            connection_id="test_conn",
            user_id="test_user"
        )
        
        with patch.object(connection_manager, 'send_personal_message') as mock_send:
            mock_send.return_value = True
            await handler._handle_place_order(message)
            mock_send.assert_called()

    @pytest.mark.asyncio
    async def test_handle_place_order_unauthenticated(self, handler):
        """Test handling place order message without authentication"""
        message = WebSocketMessage(
            type="place_order",
            data={
                "order": {
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "market",
                    "quantity": 100
                }
            },
            connection_id="test_conn",
            user_id=None
        )
        
        with patch.object(handler, '_send_error') as mock_error:
            await handler._handle_place_order(message)
            mock_error.assert_called_once_with("test_conn", "Authentication required for trading")

class TestBroadcastService:
    """Test cases for Broadcast Service"""

    @pytest.fixture
    def broadcast_service(self):
        return BroadcastService()

    @pytest.mark.asyncio
    async def test_broadcast_quote_update(self, broadcast_service):
        """Test broadcasting quote update"""
        symbol = "AAPL"
        quote_data = {
            "price": 150.25,
            "change": 2.50,
            "change_percent": 1.69,
            "volume": 1000000
        }
        
        with patch.object(connection_manager, 'broadcast_to_channel') as mock_broadcast:
            mock_broadcast.return_value = 5
            await broadcast_service.broadcast_quote_update(symbol, quote_data)
            
            # Should broadcast to both market_data and quotes channels
            assert mock_broadcast.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_order_update(self, broadcast_service):
        """Test broadcasting order update"""
        user_id = "test_user"
        order_data = {
            "order_id": "order_123",
            "status": "filled",
            "symbol": "AAPL"
        }
        
        with patch.object(connection_manager, 'send_to_user') as mock_send_user, \
             patch.object(connection_manager, 'broadcast_to_channel') as mock_broadcast:
            mock_send_user.return_value = 2
            mock_broadcast.return_value = 1
            
            await broadcast_service.broadcast_order_update(user_id, order_data)
            
            mock_send_user.assert_called_once()
            mock_broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_news_update(self, broadcast_service):
        """Test broadcasting news update"""
        news_data = {
            "headline": "Test News",
            "summary": "Test summary",
            "source": "Test Source"
        }
        symbols = ["AAPL", "MSFT"]
        
        with patch.object(connection_manager, 'broadcast_to_channel') as mock_broadcast:
            mock_broadcast.return_value = 3
            
            await broadcast_service.broadcast_news_update(news_data, symbols)
            
            # Should broadcast to general + symbol-specific channels
            assert mock_broadcast.call_count == 3

    @pytest.mark.asyncio
    async def test_broadcast_system_notification(self, broadcast_service):
        """Test broadcasting system notification"""
        notification_data = {
            "title": "System Maintenance",
            "message": "Scheduled maintenance in 1 hour",
            "severity": "warning"
        }
        
        with patch.object(connection_manager, 'broadcast_to_channel') as mock_broadcast:
            mock_broadcast.return_value = 10
            
            await broadcast_service.broadcast_system_notification(notification_data)
            
            mock_broadcast.assert_called_once_with("system.announcements", pytest.any(dict))

class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality"""

    def test_websocket_endpoint_exists(self, client: TestClient):
        """Test that WebSocket endpoint exists"""
        # Note: TestClient doesn't support WebSocket testing directly
        # This test just verifies the endpoint is registered
        response = client.get("/v1/ws/connections/stats")
        assert response.status_code in [200, 401]  # Either success or auth required

    def test_websocket_stats_endpoint(self, client: TestClient):
        """Test WebSocket stats endpoint"""
        response = client.get("/v1/ws/connections/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "data" in data

    def test_websocket_health_endpoint(self, client: TestClient):
        """Test WebSocket health endpoint"""
        response = client.get("/v1/ws/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "websocket"

    def test_broadcast_quote_endpoint(self, client: TestClient, auth_headers):
        """Test broadcast quote endpoint"""
        quote_data = {
            "symbol": "AAPL",
            "price": 150.25,
            "change": 2.50,
            "change_percent": 1.69
        }
        
        response = client.post("/v1/ws/broadcast/quote", json=quote_data, headers=auth_headers)
        assert response.status_code in [200, 401]  # Either success or auth required