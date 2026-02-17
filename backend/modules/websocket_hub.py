"""
WebSocket Hub — Central real-time event broadcasting system.

Manages WebSocket connections and broadcasts events to all connected clients.
Used by route handlers to notify the frontend of data changes (styles, projects, etc).

Usage from any route:
    from modules.websocket_hub import manager
    await manager.broadcast("styles_updated", {"action": "saved", "id": 5})
"""

import asyncio
import json
import logging
import time
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        client = websocket.client
        logger.info(f"[WS] Client connected: {client.host}:{client.port} (total: {len(self._connections)})")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        client = websocket.client
        logger.info(f"[WS] Client disconnected: {client.host}:{client.port} (total: {len(self._connections)})")

    async def broadcast(self, event_type: str, data: Any = None):
        """
        Broadcast an event to ALL connected clients.
        
        Args:
            event_type: Event name, e.g. 'styles_updated', 'projects_updated'
            data: Optional payload dictionary
        """
        if not self._connections:
            return

        message = json.dumps({
            "event": event_type,
            "data": data or {},
            "timestamp": time.time(),
        }, ensure_ascii=False)

        # Send to all, collect dead connections
        dead: list[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)

            for ws in dead:
                self._connections.remove(ws)

        if dead:
            logger.info(f"[WS] Cleaned {len(dead)} dead connection(s), remaining: {len(self._connections)}")

    @property
    def active_count(self) -> int:
        return len(self._connections)


# ── Singleton instance ──
manager = ConnectionManager()
