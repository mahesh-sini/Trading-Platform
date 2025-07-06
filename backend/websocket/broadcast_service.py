import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .connection_manager import connection_manager
from .message_types import (
    MessageType, QuoteUpdateMessage, OrderUpdateMessage, 
    PortfolioUpdateMessage, PredictionUpdateMessage, AlertMessage
)

logger = logging.getLogger(__name__)

class BroadcastService:
    """Service for broadcasting real-time updates to WebSocket connections"""
    
    def __init__(self):
        self.is_running = False
        
    async def start(self):
        """Start the broadcast service"""
        self.is_running = True
        logger.info("Broadcast service started")
        
        # Start background tasks
        asyncio.create_task(self._market_data_broadcaster())
        asyncio.create_task(self._order_status_broadcaster())
        asyncio.create_task(self._portfolio_broadcaster())
    
    async def stop(self):
        """Stop the broadcast service"""
        self.is_running = False
        logger.info("Broadcast service stopped")
    
    async def broadcast_quote_update(self, symbol: str, quote_data: Dict[str, Any]):
        """Broadcast quote update to all subscribers"""
        try:
            message = {
                "type": MessageType.QUOTE_UPDATE.value,
                "symbol": symbol,
                "data": quote_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to market data channel
            channel = f"market_data.{symbol}"
            count = await connection_manager.broadcast_to_channel(channel, message)
            
            # Also broadcast to general quotes channel
            quotes_channel = f"quotes.{symbol}"
            count += await connection_manager.broadcast_to_channel(quotes_channel, message)
            
            logger.debug(f"Quote update for {symbol} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast quote update for {symbol}: {str(e)}")
    
    async def broadcast_order_update(self, user_id: str, order_data: Dict[str, Any]):
        """Broadcast order update to user's connections"""
        try:
            message = {
                "type": MessageType.ORDER_UPDATE.value,
                "data": order_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to user's connections
            count = await connection_manager.send_to_user(user_id, message)
            
            # Also send to user's orders channel
            orders_channel = f"orders.{user_id}"
            count += await connection_manager.broadcast_to_channel(orders_channel, message)
            
            logger.debug(f"Order update for user {user_id} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast order update for user {user_id}: {str(e)}")
    
    async def broadcast_portfolio_update(self, user_id: str, portfolio_data: Dict[str, Any]):
        """Broadcast portfolio update to user's connections"""
        try:
            message = {
                "type": MessageType.PORTFOLIO_UPDATE.value,
                "data": portfolio_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to user's connections
            count = await connection_manager.send_to_user(user_id, message)
            
            # Also send to user's portfolio channel
            portfolio_channel = f"portfolio.{user_id}"
            count += await connection_manager.broadcast_to_channel(portfolio_channel, message)
            
            logger.debug(f"Portfolio update for user {user_id} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast portfolio update for user {user_id}: {str(e)}")
    
    async def broadcast_position_update(self, user_id: str, position_data: Dict[str, Any]):
        """Broadcast position update to user's connections"""
        try:
            message = {
                "type": MessageType.POSITION_UPDATE.value,
                "data": position_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to user's connections
            count = await connection_manager.send_to_user(user_id, message)
            
            # Also send to user's positions channel
            positions_channel = f"positions.{user_id}"
            count += await connection_manager.broadcast_to_channel(positions_channel, message)
            
            logger.debug(f"Position update for user {user_id} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast position update for user {user_id}: {str(e)}")
    
    async def broadcast_prediction_update(self, symbol: str, prediction_data: Dict[str, Any]):
        """Broadcast prediction update to all subscribers"""
        try:
            message = {
                "type": MessageType.PREDICTION_UPDATE.value,
                "symbol": symbol,
                "data": prediction_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to predictions channel
            channel = f"predictions.{symbol}"
            count = await connection_manager.broadcast_to_channel(channel, message)
            
            logger.debug(f"Prediction update for {symbol} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast prediction update for {symbol}: {str(e)}")
    
    async def broadcast_news_update(self, news_data: Dict[str, Any], symbols: List[str] = None):
        """Broadcast news update to subscribers"""
        try:
            message = {
                "type": MessageType.NEWS_UPDATE.value,
                "data": news_data,
                "timestamp": datetime.now().isoformat()
            }
            
            total_count = 0
            
            # Broadcast to general news channel
            general_channel = "news.general"
            total_count += await connection_manager.broadcast_to_channel(general_channel, message)
            
            # Broadcast to symbol-specific news channels
            if symbols:
                for symbol in symbols:
                    symbol_channel = f"news.{symbol}"
                    total_count += await connection_manager.broadcast_to_channel(symbol_channel, message)
            
            logger.debug(f"News update sent to {total_count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast news update: {str(e)}")
    
    async def broadcast_alert(self, user_id: str, alert_data: Dict[str, Any]):
        """Broadcast alert to user's connections"""
        try:
            message = {
                "type": MessageType.ALERT.value,
                "data": alert_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to user's connections
            count = await connection_manager.send_to_user(user_id, message)
            
            # Also send to user's alerts channel
            alerts_channel = f"alerts.{user_id}"
            count += await connection_manager.broadcast_to_channel(alerts_channel, message)
            
            logger.debug(f"Alert for user {user_id} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast alert for user {user_id}: {str(e)}")
    
    async def broadcast_system_notification(self, notification_data: Dict[str, Any]):
        """Broadcast system notification to all connections"""
        try:
            message = {
                "type": MessageType.NOTIFICATION.value,
                "data": notification_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to system channel
            channel = "system.announcements"
            count = await connection_manager.broadcast_to_channel(channel, message)
            
            logger.info(f"System notification sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast system notification: {str(e)}")
    
    async def broadcast_to_room(self, room_id: str, message_data: Dict[str, Any]):
        """Broadcast message to all members of a room"""
        try:
            message = {
                "type": "room_message",
                "room_id": room_id,
                "data": message_data,
                "timestamp": datetime.now().isoformat()
            }
            
            count = await connection_manager.broadcast_to_room(room_id, message)
            logger.debug(f"Room message to {room_id} sent to {count} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast to room {room_id}: {str(e)}")
    
    async def _market_data_broadcaster(self):
        """Background task for market data broadcasting"""
        while self.is_running:
            try:
                # This would integrate with the data service to get real-time updates
                # For now, it's a placeholder
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in market data broadcaster: {str(e)}")
                await asyncio.sleep(5)
    
    async def _order_status_broadcaster(self):
        """Background task for order status broadcasting"""
        while self.is_running:
            try:
                # This would check for order status changes and broadcast updates
                # For now, it's a placeholder
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in order status broadcaster: {str(e)}")
                await asyncio.sleep(10)
    
    async def _portfolio_broadcaster(self):
        """Background task for portfolio value broadcasting"""
        while self.is_running:
            try:
                # This would calculate portfolio values and broadcast updates
                # For now, it's a placeholder
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in portfolio broadcaster: {str(e)}")
                await asyncio.sleep(30)

# Global broadcast service instance
broadcast_service = BroadcastService()