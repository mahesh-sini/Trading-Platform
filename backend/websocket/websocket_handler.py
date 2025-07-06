import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.orm import Session
from services.database import get_db
from services.auth_service import verify_token
from .connection_manager import connection_manager
from .message_types import MessageType, WebSocketMessage

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handles WebSocket message processing and routing"""
    
    def __init__(self):
        self.message_handlers = {
            MessageType.SUBSCRIBE: self._handle_subscribe,
            MessageType.UNSUBSCRIBE: self._handle_unsubscribe,
            MessageType.JOIN_ROOM: self._handle_join_room,
            MessageType.LEAVE_ROOM: self._handle_leave_room,
            MessageType.PING: self._handle_ping,
            MessageType.GET_QUOTE: self._handle_get_quote,
            MessageType.PLACE_ORDER: self._handle_place_order,
            MessageType.CANCEL_ORDER: self._handle_cancel_order,
            MessageType.GET_PORTFOLIO: self._handle_get_portfolio,
        }
    
    async def handle_websocket(self, websocket: WebSocket, token: Optional[str] = None):
        """Main WebSocket connection handler"""
        connection_id = str(uuid.uuid4())
        user_id = None
        
        # Authenticate user if token provided
        if token:
            try:
                db = next(get_db())
                payload = verify_token(token)
                user_id = payload.get("sub")
            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {str(e)}")
                await websocket.close(code=4001, reason="Authentication failed")
                return
        
        # Establish connection
        connected = await connection_manager.connect(websocket, connection_id, user_id)
        if not connected:
            await websocket.close(code=4000, reason="Connection failed")
            return
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    message = WebSocketMessage(**message_data)
                    
                    # Add connection metadata
                    message.connection_id = connection_id
                    message.user_id = user_id
                    message.timestamp = datetime.now()
                    
                    # Process message
                    await self._process_message(message)
                    
                except json.JSONDecodeError:
                    await self._send_error(connection_id, "Invalid JSON format")
                except ValueError as e:
                    await self._send_error(connection_id, f"Invalid message format: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing message from {connection_id}: {str(e)}")
                    await self._send_error(connection_id, "Message processing failed")
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket {connection_id} disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket {connection_id} error: {str(e)}")
        finally:
            connection_manager.disconnect(connection_id)
    
    async def _process_message(self, message: WebSocketMessage):
        """Process incoming WebSocket message"""
        try:
            message_type = MessageType(message.type)
            
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(message)
            else:
                await self._send_error(message.connection_id, f"Unknown message type: {message.type}")
                
        except ValueError:
            await self._send_error(message.connection_id, f"Invalid message type: {message.type}")
        except Exception as e:
            logger.error(f"Error in message handler: {str(e)}")
            await self._send_error(message.connection_id, "Message handler error")
    
    async def _handle_subscribe(self, message: WebSocketMessage):
        """Handle channel subscription"""
        channel = message.data.get("channel")
        if not channel:
            await self._send_error(message.connection_id, "Channel name required")
            return
        
        success = await connection_manager.subscribe_to_channel(message.connection_id, channel)
        if success:
            # Start data feed for this channel if needed
            await self._start_channel_feed(channel)
        
    async def _handle_unsubscribe(self, message: WebSocketMessage):
        """Handle channel unsubscription"""
        channel = message.data.get("channel")
        if not channel:
            await self._send_error(message.connection_id, "Channel name required")
            return
        
        await connection_manager.unsubscribe_from_channel(message.connection_id, channel)
    
    async def _handle_join_room(self, message: WebSocketMessage):
        """Handle room joining"""
        room_id = message.data.get("room_id")
        if not room_id:
            await self._send_error(message.connection_id, "Room ID required")
            return
        
        await connection_manager.join_room(message.connection_id, room_id)
    
    async def _handle_leave_room(self, message: WebSocketMessage):
        """Handle room leaving"""
        room_id = message.data.get("room_id")
        if not room_id:
            await self._send_error(message.connection_id, "Room ID required")
            return
        
        await connection_manager.leave_room(message.connection_id, room_id)
    
    async def _handle_ping(self, message: WebSocketMessage):
        """Handle ping message"""
        await connection_manager.send_personal_message(message.connection_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "request_id": message.data.get("request_id")
        })
    
    async def _handle_get_quote(self, message: WebSocketMessage):
        """Handle quote request"""
        symbol = message.data.get("symbol")
        if not symbol:
            await self._send_error(message.connection_id, "Symbol required")
            return
        
        try:
            # Get quote from data service
            # This would integrate with the data service
            response = {
                "type": "quote_response",
                "symbol": symbol,
                "data": {
                    "price": 150.25,  # Placeholder data
                    "change": 2.50,
                    "change_percent": 1.69,
                    "volume": 1000000,
                    "timestamp": datetime.now().isoformat()
                },
                "request_id": message.data.get("request_id")
            }
            
            await connection_manager.send_personal_message(message.connection_id, response)
            
        except Exception as e:
            await self._send_error(message.connection_id, f"Failed to get quote: {str(e)}")
    
    async def _handle_place_order(self, message: WebSocketMessage):
        """Handle order placement"""
        if not message.user_id:
            await self._send_error(message.connection_id, "Authentication required for trading")
            return
        
        order_data = message.data.get("order")
        if not order_data:
            await self._send_error(message.connection_id, "Order data required")
            return
        
        try:
            # Validate order data
            required_fields = ["symbol", "side", "type", "quantity"]
            for field in required_fields:
                if field not in order_data:
                    await self._send_error(message.connection_id, f"Missing field: {field}")
                    return
            
            # Place order through trading service
            # This would integrate with the trading service
            response = {
                "type": "order_response",
                "order_id": str(uuid.uuid4()),
                "status": "placed",
                "data": order_data,
                "request_id": message.data.get("request_id")
            }
            
            await connection_manager.send_personal_message(message.connection_id, response)
            
            # Broadcast to user's other connections
            await connection_manager.send_to_user(message.user_id, {
                "type": "order_update",
                "order_id": response["order_id"],
                "status": "placed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            await self._send_error(message.connection_id, f"Failed to place order: {str(e)}")
    
    async def _handle_cancel_order(self, message: WebSocketMessage):
        """Handle order cancellation"""
        if not message.user_id:
            await self._send_error(message.connection_id, "Authentication required for trading")
            return
        
        order_id = message.data.get("order_id")
        if not order_id:
            await self._send_error(message.connection_id, "Order ID required")
            return
        
        try:
            # Cancel order through trading service
            # This would integrate with the trading service
            response = {
                "type": "cancel_response",
                "order_id": order_id,
                "status": "cancelled",
                "request_id": message.data.get("request_id")
            }
            
            await connection_manager.send_personal_message(message.connection_id, response)
            
            # Broadcast to user's other connections
            await connection_manager.send_to_user(message.user_id, {
                "type": "order_update",
                "order_id": order_id,
                "status": "cancelled",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            await self._send_error(message.connection_id, f"Failed to cancel order: {str(e)}")
    
    async def _handle_get_portfolio(self, message: WebSocketMessage):
        """Handle portfolio request"""
        if not message.user_id:
            await self._send_error(message.connection_id, "Authentication required")
            return
        
        try:
            # Get portfolio from database
            # This would integrate with the portfolio service
            response = {
                "type": "portfolio_response",
                "data": {
                    "total_value": 125430.50,
                    "day_change": 2450.30,
                    "day_change_percent": 1.99,
                    "positions": [],
                    "timestamp": datetime.now().isoformat()
                },
                "request_id": message.data.get("request_id")
            }
            
            await connection_manager.send_personal_message(message.connection_id, response)
            
        except Exception as e:
            await self._send_error(message.connection_id, f"Failed to get portfolio: {str(e)}")
    
    async def _send_error(self, connection_id: str, error_message: str):
        """Send error message to connection"""
        await connection_manager.send_personal_message(connection_id, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _start_channel_feed(self, channel: str):
        """Start data feed for a channel if not already running"""
        # This would start real-time data feeds based on channel type
        # For example: market_data.AAPL, news.general, etc.
        pass

# Global WebSocket handler instance
websocket_handler = WebSocketHandler()