"""WebSocket connection manager for real-time updates."""

from typing import Dict, List, Optional, Set, Any

from fastapi import WebSocket, WebSocketDisconnect

from ..core.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manager for WebSocket connections with broadcast capabilities."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, bot_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        if bot_id not in self.active_connections:
            self.active_connections[bot_id] = []

        self.active_connections[bot_id].append(websocket)
        self.all_connections.add(websocket)

        logger.info(f"WebSocket connected for bot {bot_id}. Total: {len(self.all_connections)}")

    def disconnect(self, websocket: WebSocket, bot_id: str) -> None:
        """Remove a WebSocket connection."""
        if bot_id in self.active_connections:
            if websocket in self.active_connections[bot_id]:
                self.active_connections[bot_id].remove(websocket)
            if not self.active_connections[bot_id]:
                del self.active_connections[bot_id]

        self.all_connections.discard(websocket)
        logger.info(f"WebSocket disconnected for bot {bot_id}. Total: {len(self.all_connections)}")

    async def _safe_send(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Safely send message to websocket, return False if failed."""
        try:
            await websocket.send_json(message)
            return True
        except WebSocketDisconnect:
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket."""
        if not await self._safe_send(websocket, message):
            logger.warning("WebSocket already disconnected")

    async def broadcast_to_bot(self, bot_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connections for a specific bot."""
        if bot_id not in self.active_connections:
            logger.debug(f"No active connections for bot {bot_id}")
            return

        connections = self.active_connections[bot_id].copy()
        disconnected = []

        for websocket in connections:
            if not await self._safe_send(websocket, message):
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket, bot_id)

        sent_count = len(connections) - len(disconnected)
        logger.debug(f"Broadcasted to {sent_count} connections for bot {bot_id}")

    async def broadcast_to_all(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected WebSockets."""
        disconnected = []

        for websocket in self.all_connections.copy():
            if not await self._safe_send(websocket, message):
                disconnected.append(websocket)

        for websocket in disconnected:
            for bot_id, connections in list(self.active_connections.items()):
                if websocket in connections:
                    self.disconnect(websocket, bot_id)
                    break

        sent_count = len(self.all_connections) - len(disconnected)
        logger.debug(f"Broadcasted to {sent_count} connections")

    def get_connection_count(self, bot_id: Optional[str] = None) -> int:
        """Get number of active connections."""
        if bot_id:
            return len(self.active_connections.get(bot_id, []))
        return len(self.all_connections)

    def get_connected_bots(self) -> List[str]:
        """Get list of bot IDs with active connections."""
        return list(self.active_connections.keys())

    async def send_ping(self, websocket: WebSocket) -> bool:
        """Send a ping to check connection health."""
        return await self._safe_send(websocket, {"type": "ping", "timestamp": "now"})


_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create global connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
