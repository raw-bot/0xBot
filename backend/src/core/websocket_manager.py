"""WebSocket connection manager for real-time updates."""

import json
from typing import Dict, List, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from ..core.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manager for WebSocket connections.
    
    Handles multiple clients and broadcasts messages to specific bots.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        # Store active connections: {bot_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # Track all websockets for easy cleanup
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, bot_id: str) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            bot_id: Bot ID to associate with this connection
        """
        await websocket.accept()
        
        if bot_id not in self.active_connections:
            self.active_connections[bot_id] = []
        
        self.active_connections[bot_id].append(websocket)
        self.all_connections.add(websocket)
        
        logger.info(f"WebSocket connected for bot {bot_id}. Total connections: {len(self.all_connections)}")
    
    def disconnect(self, websocket: WebSocket, bot_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
            bot_id: Bot ID associated with this connection
        """
        if bot_id in self.active_connections:
            if websocket in self.active_connections[bot_id]:
                self.active_connections[bot_id].remove(websocket)
            
            # Clean up empty bot connection lists
            if not self.active_connections[bot_id]:
                del self.active_connections[bot_id]
        
        self.all_connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected for bot {bot_id}. Total connections: {len(self.all_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """
        Send a message to a specific WebSocket.
        
        Args:
            message: Message dict to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_json(message)
        except WebSocketDisconnect:
            logger.warning("WebSocket already disconnected")
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_bot(self, bot_id: str, message: dict) -> None:
        """
        Broadcast a message to all connections for a specific bot.
        
        Args:
            bot_id: Target bot ID
            message: Message dict to broadcast
        """
        if bot_id not in self.active_connections:
            logger.debug(f"No active connections for bot {bot_id}")
            return
        
        connections = self.active_connections[bot_id].copy()
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(websocket)
                logger.warning(f"WebSocket disconnected during broadcast for bot {bot_id}")
            except Exception as e:
                disconnected.append(websocket)
                logger.error(f"Error broadcasting to bot {bot_id}: {e}")
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket, bot_id)
        
        logger.debug(f"Broadcasted message to {len(connections) - len(disconnected)} connections for bot {bot_id}")
    
    async def broadcast_to_all(self, message: dict) -> None:
        """
        Broadcast a message to all connected WebSockets.
        
        Args:
            message: Message dict to broadcast
        """
        disconnected = []
        
        for websocket in self.all_connections.copy():
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to all: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            # Find and remove from bot connections
            for bot_id, connections in list(self.active_connections.items()):
                if websocket in connections:
                    self.disconnect(websocket, bot_id)
                    break
        
        logger.debug(f"Broadcasted message to {len(self.all_connections) - len(disconnected)} connections")
    
    def get_connection_count(self, bot_id: str = None) -> int:
        """
        Get number of active connections.
        
        Args:
            bot_id: Optional bot ID to filter by
            
        Returns:
            Number of active connections
        """
        if bot_id:
            return len(self.active_connections.get(bot_id, []))
        return len(self.all_connections)
    
    def get_connected_bots(self) -> List[str]:
        """
        Get list of bot IDs with active connections.
        
        Returns:
            List of bot IDs
        """
        return list(self.active_connections.keys())
    
    async def send_ping(self, websocket: WebSocket) -> bool:
        """
        Send a ping to check connection health.
        
        Args:
            websocket: WebSocket to ping
            
        Returns:
            True if ping successful, False otherwise
        """
        try:
            await websocket.send_json({"type": "ping", "timestamp": "now"})
            return True
        except Exception:
            return False


# Global connection manager instance
_connection_manager: ConnectionManager = None


def get_connection_manager() -> ConnectionManager:
    """
    Get or create global connection manager.
    
    Returns:
        ConnectionManager instance
    """
    global _connection_manager
    
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    
    return _connection_manager