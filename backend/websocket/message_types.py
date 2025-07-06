from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class MessageType(Enum):
    """WebSocket message types"""
    # Connection management
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    PING = "ping"
    PONG = "pong"
    
    # Market data
    GET_QUOTE = "get_quote"
    QUOTE_UPDATE = "quote_update"
    MARKET_DATA = "market_data"
    NEWS_UPDATE = "news_update"
    
    # Trading
    PLACE_ORDER = "place_order"
    CANCEL_ORDER = "cancel_order"
    ORDER_UPDATE = "order_update"
    ORDER_RESPONSE = "order_response"
    CANCEL_RESPONSE = "cancel_response"
    
    # Portfolio
    GET_PORTFOLIO = "get_portfolio"
    PORTFOLIO_UPDATE = "portfolio_update"
    PORTFOLIO_RESPONSE = "portfolio_response"
    POSITION_UPDATE = "position_update"
    
    # Predictions
    GET_PREDICTION = "get_prediction"
    PREDICTION_UPDATE = "prediction_update"
    PREDICTION_RESPONSE = "prediction_response"
    
    # Alerts and notifications
    ALERT = "alert"
    NOTIFICATION = "notification"
    
    # Status and responses
    ERROR = "error"
    SUCCESS = "success"
    STATUS = "status"
    
    # Channel management responses
    CHANNEL_SUBSCRIBED = "channel_subscribed"
    CHANNEL_UNSUBSCRIBED = "channel_unsubscribed"
    ROOM_JOINED = "room_joined"
    ROOM_LEFT = "room_left"
    CONNECTION_ESTABLISHED = "connection_established"

class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: str
    data: Dict[str, Any] = {}
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    connection_id: Optional[str] = None
    user_id: Optional[str] = None

class ChannelType(Enum):
    """Channel types for subscriptions"""
    # Market data channels
    MARKET_DATA = "market_data"  # market_data.SYMBOL
    QUOTES = "quotes"            # quotes.SYMBOL
    NEWS = "news"                # news.general or news.SYMBOL
    
    # Trading channels
    ORDERS = "orders"            # orders.USER_ID
    POSITIONS = "positions"      # positions.USER_ID
    PORTFOLIO = "portfolio"      # portfolio.USER_ID
    
    # Prediction channels
    PREDICTIONS = "predictions"  # predictions.SYMBOL
    ALERTS = "alerts"           # alerts.USER_ID
    
    # General channels
    SYSTEM = "system"           # system.announcements
    NOTIFICATIONS = "notifications"  # notifications.USER_ID

class RoomType(Enum):
    """Room types for group communications"""
    WATCHLIST = "watchlist"     # watchlist.WATCHLIST_ID
    STRATEGY = "strategy"       # strategy.STRATEGY_ID
    CHAT = "chat"              # chat.ROOM_ID
    TRADING_ROOM = "trading_room"  # trading_room.ROOM_ID

# Message schemas for specific message types
class SubscribeMessage(BaseModel):
    channel: str
    symbols: Optional[list] = None

class UnsubscribeMessage(BaseModel):
    channel: str

class JoinRoomMessage(BaseModel):
    room_id: str
    room_type: str

class LeaveRoomMessage(BaseModel):
    room_id: str

class GetQuoteMessage(BaseModel):
    symbol: str
    request_id: Optional[str] = None

class PlaceOrderMessage(BaseModel):
    order: Dict[str, Any]
    request_id: Optional[str] = None

class CancelOrderMessage(BaseModel):
    order_id: str
    request_id: Optional[str] = None

class QuoteUpdateMessage(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: datetime

class OrderUpdateMessage(BaseModel):
    order_id: str
    status: str
    filled_quantity: Optional[int] = None
    average_fill_price: Optional[float] = None
    timestamp: datetime

class PortfolioUpdateMessage(BaseModel):
    total_value: float
    day_change: float
    day_change_percent: float
    cash_balance: float
    timestamp: datetime

class PredictionUpdateMessage(BaseModel):
    symbol: str
    prediction_type: str
    predicted_price: Optional[float] = None
    confidence: float
    horizon: str
    timestamp: datetime

class AlertMessage(BaseModel):
    alert_type: str
    title: str
    message: str
    severity: str  # info, warning, error, success
    symbol: Optional[str] = None
    timestamp: datetime

class ErrorMessage(BaseModel):
    message: str
    code: Optional[str] = None
    timestamp: datetime