import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional
from websocket.websocket_handler import websocket_handler
from websocket.connection_manager import connection_manager
from websocket.broadcast_service import broadcast_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT token for authentication")
):
    """Main WebSocket endpoint for real-time communication"""
    await websocket_handler.handle_websocket(websocket, token)

@router.get("/connections/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = connection_manager.get_connection_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get connection stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connection statistics")

@router.get("/connections/user/{user_id}")
async def get_user_connections(user_id: str):
    """Get connection information for a specific user"""
    try:
        connections = connection_manager.get_user_connections(user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "connections": connections,
            "connection_count": len(connections)
        }
    except Exception as e:
        logger.error(f"Failed to get user connections for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user connections")

@router.get("/channels/{channel}/subscribers")
async def get_channel_subscribers(channel: str):
    """Get subscribers for a specific channel"""
    try:
        subscribers = connection_manager.get_channel_subscribers(channel)
        return {
            "status": "success",
            "channel": channel,
            "subscribers": subscribers,
            "subscriber_count": len(subscribers)
        }
    except Exception as e:
        logger.error(f"Failed to get channel subscribers for {channel}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channel subscribers")

@router.get("/rooms/{room_id}/members")
async def get_room_members(room_id: str):
    """Get members of a specific room"""
    try:
        members = connection_manager.get_room_members(room_id)
        return {
            "status": "success",
            "room_id": room_id,
            "members": members,
            "member_count": len(members)
        }
    except Exception as e:
        logger.error(f"Failed to get room members for {room_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve room members")

@router.post("/broadcast/quote")
async def broadcast_quote_update(quote_data: dict):
    """Broadcast a quote update to all subscribers"""
    try:
        symbol = quote_data.get("symbol")
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        await broadcast_service.broadcast_quote_update(symbol, quote_data)
        
        return {
            "status": "success",
            "message": f"Quote update for {symbol} broadcasted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to broadcast quote update: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast quote update")

@router.post("/broadcast/order/{user_id}")
async def broadcast_order_update(user_id: str, order_data: dict):
    """Broadcast an order update to a specific user"""
    try:
        await broadcast_service.broadcast_order_update(user_id, order_data)
        
        return {
            "status": "success",
            "message": f"Order update for user {user_id} broadcasted"
        }
    except Exception as e:
        logger.error(f"Failed to broadcast order update: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast order update")

@router.post("/broadcast/portfolio/{user_id}")
async def broadcast_portfolio_update(user_id: str, portfolio_data: dict):
    """Broadcast a portfolio update to a specific user"""
    try:
        await broadcast_service.broadcast_portfolio_update(user_id, portfolio_data)
        
        return {
            "status": "success",
            "message": f"Portfolio update for user {user_id} broadcasted"
        }
    except Exception as e:
        logger.error(f"Failed to broadcast portfolio update: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast portfolio update")

@router.post("/broadcast/prediction")
async def broadcast_prediction_update(prediction_data: dict):
    """Broadcast a prediction update to all subscribers"""
    try:
        symbol = prediction_data.get("symbol")
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        await broadcast_service.broadcast_prediction_update(symbol, prediction_data)
        
        return {
            "status": "success",
            "message": f"Prediction update for {symbol} broadcasted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to broadcast prediction update: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast prediction update")

@router.post("/broadcast/news")
async def broadcast_news_update(news_data: dict):
    """Broadcast a news update to all subscribers"""
    try:
        symbols = news_data.get("symbols", [])
        
        await broadcast_service.broadcast_news_update(news_data, symbols)
        
        return {
            "status": "success",
            "message": "News update broadcasted"
        }
    except Exception as e:
        logger.error(f"Failed to broadcast news update: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast news update")

@router.post("/broadcast/alert/{user_id}")
async def broadcast_alert(user_id: str, alert_data: dict):
    """Broadcast an alert to a specific user"""
    try:
        await broadcast_service.broadcast_alert(user_id, alert_data)
        
        return {
            "status": "success",
            "message": f"Alert for user {user_id} broadcasted"
        }
    except Exception as e:
        logger.error(f"Failed to broadcast alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast alert")

@router.post("/broadcast/system")
async def broadcast_system_notification(notification_data: dict):
    """Broadcast a system notification to all connections"""
    try:
        await broadcast_service.broadcast_system_notification(notification_data)
        
        return {
            "status": "success",
            "message": "System notification broadcasted"
        }
    except Exception as e:
        logger.error(f"Failed to broadcast system notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast system notification")

@router.post("/broadcast/room/{room_id}")
async def broadcast_to_room(room_id: str, message_data: dict):
    """Broadcast a message to all members of a room"""
    try:
        await broadcast_service.broadcast_to_room(room_id, message_data)
        
        return {
            "status": "success",
            "message": f"Message broadcasted to room {room_id}"
        }
    except Exception as e:
        logger.error(f"Failed to broadcast to room: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast to room")

@router.get("/health")
async def websocket_health_check():
    """Health check for WebSocket service"""
    try:
        stats = connection_manager.get_connection_stats()
        return {
            "status": "healthy",
            "service": "websocket",
            "connections": stats["total_connections"],
            "channels": stats["active_channels"],
            "rooms": stats["active_rooms"]
        }
    except Exception as e:
        logger.error(f"WebSocket health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="WebSocket service unhealthy")