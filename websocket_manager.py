"""
WebSocket manager for real-time updates
Handles WebSocket connections and broadcasting
"""

import asyncio
import json
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id,
            "connected_at": asyncio.get_event_loop().time()
        }
        logger.info(f"WebSocket connected: {client_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to Social Media Monitor",
            "client_id": client_id
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            client_info = self.connection_info.pop(websocket, {})
            logger.info(f"WebSocket disconnected: {client_info.get('client_id')}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_brand_update(self, brand_data: Dict[str, Any]):
        """Broadcast brand-related updates"""
        await self.broadcast({
            "type": "brand_update",
            "data": brand_data,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def broadcast_post_update(self, posts_data: List[Dict[str, Any]]):
        """Broadcast new posts updates"""
        await self.broadcast({
            "type": "posts_update",
            "data": posts_data,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def broadcast_analytics_update(self, brand_id: int, analytics_data: Dict[str, Any]):
        """Broadcast analytics updates"""
        await self.broadcast({
            "type": "analytics_update",
            "brand_id": brand_id,
            "data": analytics_data,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def broadcast_notification(self, message: str, notification_type: str = "info"):
        """Broadcast general notifications"""
        await self.broadcast({
            "type": "notification",
            "message": message,
            "notification_type": notification_type,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Get information about all active connections"""
        return [
            {
                "client_id": info.get("client_id"),
                "connected_at": info.get("connected_at"),
                "duration": asyncio.get_event_loop().time() - info.get("connected_at", 0)
            }
            for info in self.connection_info.values()
        ]

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

