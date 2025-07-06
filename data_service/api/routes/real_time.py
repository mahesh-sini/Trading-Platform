from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.market_data_service import market_data_service
from services.data_ingestion import data_ingestion_service
import logging
import json
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class SubscriptionRequest(BaseModel):
    symbols: List[str]
    
class SubscriptionResponse(BaseModel):
    symbol: str
    status: str
    message: str

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscriptions: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await market_data_service.add_websocket_connection(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from symbol subscriptions
        for symbol, connections in self.symbol_subscriptions.items():
            if websocket in connections:
                connections.remove(websocket)
        
        logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket: {str(e)}")
            self.disconnect(websocket)
            
    async def broadcast_to_symbol(self, symbol: str, message: str):
        if symbol in self.symbol_subscriptions:
            disconnected_connections = []
            for connection in self.symbol_subscriptions[symbol]:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected_connections.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected_connections:
                self.symbol_subscriptions[symbol].remove(connection)
                
    async def subscribe_to_symbol(self, websocket: WebSocket, symbol: str):
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = []
        
        if websocket not in self.symbol_subscriptions[symbol]:
            self.symbol_subscriptions[symbol].append(websocket)
            await market_data_service.subscribe_to_symbol(symbol)
            logger.info(f"WebSocket subscribed to {symbol}")
            
    async def unsubscribe_from_symbol(self, websocket: WebSocket, symbol: str):
        if symbol in self.symbol_subscriptions and websocket in self.symbol_subscriptions[symbol]:
            self.symbol_subscriptions[symbol].remove(websocket)
            
            # If no more connections for this symbol, unsubscribe from market data service
            if not self.symbol_subscriptions[symbol]:
                await market_data_service.unsubscribe_from_symbol(symbol)
                del self.symbol_subscriptions[symbol]
                
            logger.info(f"WebSocket unsubscribed from {symbol}")

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "subscribe":
                symbols = message.get("symbols", [])
                for symbol in symbols:
                    symbol = symbol.upper()
                    await manager.subscribe_to_symbol(websocket, symbol)
                    
                    # Send initial quote
                    quote = await market_data_service.get_quote(symbol)
                    if quote:
                        response = {
                            "type": "quote",
                            "symbol": symbol,
                            "data": {
                                "price": quote.price,
                                "change": quote.change,
                                "change_percent": quote.change_percent,
                                "volume": quote.volume,
                                "timestamp": quote.timestamp.isoformat()
                            }
                        }
                        await manager.send_personal_message(json.dumps(response), websocket)
                
                # Send subscription confirmation
                confirmation = {
                    "type": "subscription_confirmed",
                    "symbols": symbols
                }
                await manager.send_personal_message(json.dumps(confirmation), websocket)
                
            elif message_type == "unsubscribe":
                symbols = message.get("symbols", [])
                for symbol in symbols:
                    symbol = symbol.upper()
                    await manager.unsubscribe_from_symbol(websocket, symbol)
                
                # Send unsubscription confirmation
                confirmation = {
                    "type": "unsubscription_confirmed",
                    "symbols": symbols
                }
                await manager.send_personal_message(json.dumps(confirmation), websocket)
                
            elif message_type == "ping":
                pong_response = {
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                }
                await manager.send_personal_message(json.dumps(pong_response), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

@router.post("/subscribe")
async def subscribe_to_symbols(request: SubscriptionRequest):
    """Subscribe to real-time updates for multiple symbols"""
    try:
        responses = []
        
        for symbol in request.symbols:
            symbol = symbol.upper()
            try:
                await market_data_service.subscribe_to_symbol(symbol)
                responses.append(SubscriptionResponse(
                    symbol=symbol,
                    status="subscribed",
                    message=f"Successfully subscribed to {symbol}"
                ))
            except Exception as e:
                logger.error(f"Failed to subscribe to {symbol}: {str(e)}")
                responses.append(SubscriptionResponse(
                    symbol=symbol,
                    status="failed",
                    message=f"Failed to subscribe to {symbol}: {str(e)}"
                ))
        
        return {
            "subscriptions": responses,
            "total": len(responses),
            "successful": len([r for r in responses if r.status == "subscribed"])
        }
        
    except Exception as e:
        logger.error(f"Subscription request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription request failed"
        )

@router.delete("/subscribe")
async def unsubscribe_from_symbols(request: SubscriptionRequest):
    """Unsubscribe from real-time updates for multiple symbols"""
    try:
        responses = []
        
        for symbol in request.symbols:
            symbol = symbol.upper()
            try:
                await market_data_service.unsubscribe_from_symbol(symbol)
                responses.append(SubscriptionResponse(
                    symbol=symbol,
                    status="unsubscribed",
                    message=f"Successfully unsubscribed from {symbol}"
                ))
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {symbol}: {str(e)}")
                responses.append(SubscriptionResponse(
                    symbol=symbol,
                    status="failed",
                    message=f"Failed to unsubscribe from {symbol}: {str(e)}"
                ))
        
        return {
            "unsubscriptions": responses,
            "total": len(responses),
            "successful": len([r for r in responses if r.status == "unsubscribed"])
        }
        
    except Exception as e:
        logger.error(f"Unsubscription request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unsubscription request failed"
        )

@router.get("/subscriptions")
async def get_active_subscriptions():
    """Get list of active subscriptions"""
    try:
        subscriptions = list(market_data_service.subscriptions)
        websocket_connections = len(market_data_service.websocket_connections)
        
        return {
            "subscriptions": subscriptions,
            "total_subscriptions": len(subscriptions),
            "websocket_connections": websocket_connections,
            "connection_subscriptions": dict(manager.symbol_subscriptions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get active subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active subscriptions"
        )

@router.get("/stream/{symbol}")
async def get_real_time_stream_info(symbol: str):
    """Get information about real-time stream for a symbol"""
    try:
        symbol = symbol.upper()
        
        # Check if symbol is subscribed
        is_subscribed = symbol in market_data_service.subscriptions
        
        # Get latest quote
        quote = await market_data_service.get_quote(symbol)
        
        # Get connection count for this symbol
        connection_count = len(manager.symbol_subscriptions.get(symbol, []))
        
        return {
            "symbol": symbol,
            "is_subscribed": is_subscribed,
            "connection_count": connection_count,
            "latest_quote": {
                "price": quote.price if quote else None,
                "change": quote.change if quote else None,
                "change_percent": quote.change_percent if quote else None,
                "timestamp": quote.timestamp.isoformat() if quote else None
            } if quote else None,
            "websocket_endpoint": "/v1/real-time/ws"
        }
        
    except Exception as e:
        logger.error(f"Failed to get stream info for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stream information"
        )

@router.get("/connections/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics"""
    try:
        total_connections = len(manager.active_connections)
        symbol_subscriptions = {
            symbol: len(connections) 
            for symbol, connections in manager.symbol_subscriptions.items()
        }
        
        return {
            "total_connections": total_connections,
            "symbol_subscriptions": symbol_subscriptions,
            "total_symbol_subscriptions": len(manager.symbol_subscriptions),
            "service_subscriptions": len(market_data_service.subscriptions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get connection stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection statistics"
        )

@router.post("/test-broadcast/{symbol}")
async def test_broadcast_message(symbol: str, message: str = "Test message"):
    """Test broadcasting a message to all subscribers of a symbol"""
    try:
        symbol = symbol.upper()
        
        test_message = {
            "type": "test_message",
            "symbol": symbol,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await manager.broadcast_to_symbol(symbol, json.dumps(test_message))
        
        return {
            "symbol": symbol,
            "message": "Test message broadcasted",
            "connections_notified": len(manager.symbol_subscriptions.get(symbol, []))
        }
        
    except Exception as e:
        logger.error(f"Failed to broadcast test message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast test message"
        )