import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from services.database import get_db
from models.user import User
from services.auth_service import verify_token

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time communication"""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User connections mapping
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        
        # Channel subscriptions
        self.channel_subscriptions: Dict[str, Set[str]] = {}  # channel -> set of connection_ids
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Room subscriptions for trading rooms, watchlists, etc.
        self.room_subscriptions: Dict[str, Set[str]] = {}  # room_id -> set of connection_ids
        
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None) -> bool:
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            
            self.active_connections[connection_id] = websocket
            
            # Store connection metadata
            self.connection_metadata[connection_id] = {
                "user_id": user_id,
                "connected_at": datetime.now(),
                "channels": set(),
                "rooms": set()
            }
            
            # Map user to connection if authenticated
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
            
            logger.info(f"WebSocket connection established: {connection_id} (user: {user_id})")
            
            # Send connection confirmation
            await self.send_personal_message(connection_id, {
                "type": "connection_established",
                "connection_id": connection_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection {connection_id}: {str(e)}")
            return False
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        try:
            if connection_id in self.active_connections:
                # Get connection metadata
                metadata = self.connection_metadata.get(connection_id, {})
                user_id = metadata.get("user_id")
                channels = metadata.get("channels", set())
                rooms = metadata.get("rooms", set())
                
                # Remove from active connections
                del self.active_connections[connection_id]
                
                # Remove from user connections
                if user_id and user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                
                # Remove from channel subscriptions
                for channel in channels:
                    if channel in self.channel_subscriptions:
                        self.channel_subscriptions[channel].discard(connection_id)
                        if not self.channel_subscriptions[channel]:
                            del self.channel_subscriptions[channel]
                
                # Remove from room subscriptions
                for room in rooms:
                    if room in self.room_subscriptions:
                        self.room_subscriptions[room].discard(connection_id)
                        if not self.room_subscriptions[room]:
                            del self.room_subscriptions[room]
                
                # Remove metadata
                if connection_id in self.connection_metadata:
                    del self.connection_metadata[connection_id]
                
                logger.info(f"WebSocket connection disconnected: {connection_id}")
                
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket {connection_id}: {str(e)}")
    
    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific connection"""
        try:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {str(e)}")
            # Remove broken connection
            self.disconnect(connection_id)
            return False
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> int:
        """Send a message to all connections of a specific user"""
        sent_count = 0
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            for connection_id in connection_ids:
                if await self.send_personal_message(connection_id, message):
                    sent_count += 1
        return sent_count
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]) -> int:
        """Broadcast a message to all subscribers of a channel"""
        sent_count = 0
        if channel in self.channel_subscriptions:
            connection_ids = list(self.channel_subscriptions[channel])
            for connection_id in connection_ids:
                if await self.send_personal_message(connection_id, message):
                    sent_count += 1
        return sent_count
    
    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any]) -> int:
        """Broadcast a message to all members of a room"""
        sent_count = 0
        if room_id in self.room_subscriptions:
            connection_ids = list(self.room_subscriptions[room_id])
            for connection_id in connection_ids:
                if await self.send_personal_message(connection_id, message):
                    sent_count += 1
        return sent_count
    
    async def subscribe_to_channel(self, connection_id: str, channel: str) -> bool:
        """Subscribe a connection to a channel"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            # Add to channel subscriptions
            if channel not in self.channel_subscriptions:
                self.channel_subscriptions[channel] = set()
            self.channel_subscriptions[channel].add(connection_id)
            
            # Update connection metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["channels"].add(channel)
            
            logger.info(f"Connection {connection_id} subscribed to channel: {channel}")
            
            # Send confirmation
            await self.send_personal_message(connection_id, {
                "type": "channel_subscribed",
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe {connection_id} to channel {channel}: {str(e)}")
            return False
    
    async def unsubscribe_from_channel(self, connection_id: str, channel: str) -> bool:
        """Unsubscribe a connection from a channel"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            # Remove from channel subscriptions
            if channel in self.channel_subscriptions:
                self.channel_subscriptions[channel].discard(connection_id)
                if not self.channel_subscriptions[channel]:
                    del self.channel_subscriptions[channel]
            
            # Update connection metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["channels"].discard(channel)
            
            logger.info(f"Connection {connection_id} unsubscribed from channel: {channel}")
            
            # Send confirmation
            await self.send_personal_message(connection_id, {
                "type": "channel_unsubscribed",
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe {connection_id} from channel {channel}: {str(e)}")
            return False
    
    async def join_room(self, connection_id: str, room_id: str) -> bool:
        """Add a connection to a room"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            # Add to room subscriptions
            if room_id not in self.room_subscriptions:
                self.room_subscriptions[room_id] = set()
            self.room_subscriptions[room_id].add(connection_id)
            
            # Update connection metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["rooms"].add(room_id)
            
            logger.info(f"Connection {connection_id} joined room: {room_id}")
            
            # Send confirmation
            await self.send_personal_message(connection_id, {
                "type": "room_joined",
                "room_id": room_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add {connection_id} to room {room_id}: {str(e)}")
            return False
    
    async def leave_room(self, connection_id: str, room_id: str) -> bool:
        """Remove a connection from a room"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            # Remove from room subscriptions
            if room_id in self.room_subscriptions:
                self.room_subscriptions[room_id].discard(connection_id)
                if not self.room_subscriptions[room_id]:
                    del self.room_subscriptions[room_id]
            
            # Update connection metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["rooms"].discard(room_id)
            
            logger.info(f"Connection {connection_id} left room: {room_id}")
            
            # Send confirmation
            await self.send_personal_message(connection_id, {
                "type": "room_left",
                "room_id": room_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove {connection_id} from room {room_id}: {str(e)}")
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "authenticated_users": len(self.user_connections),
            "active_channels": len(self.channel_subscriptions),
            "active_rooms": len(self.room_subscriptions),
            "channels": {
                channel: len(connections) 
                for channel, connections in self.channel_subscriptions.items()
            },
            "rooms": {
                room: len(connections) 
                for room, connections in self.room_subscriptions.items()
            }
        }
    
    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user"""
        return list(self.user_connections.get(user_id, set()))
    
    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get all connection IDs subscribed to a channel"""
        return list(self.channel_subscriptions.get(channel, set()))
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Get all connection IDs in a room"""
        return list(self.room_subscriptions.get(room_id, set()))

# Global connection manager instance
connection_manager = ConnectionManager()