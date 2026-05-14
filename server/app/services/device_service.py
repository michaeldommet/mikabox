"""Device communication service — WebSocket hub for device ↔ app relay."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger("mikabox.service.device")

# Active device connections: device_id → WebSocket
_device_connections: dict[str, WebSocket] = {}

# Active app connections watching a device: device_id → list[WebSocket]
_app_watchers: dict[str, list[WebSocket]] = {}


async def register_device(device_id: str, ws: WebSocket) -> None:
    """Register a device WebSocket connection."""
    _device_connections[device_id] = ws
    logger.info("Device connected: %s", device_id)


async def unregister_device(device_id: str) -> None:
    """Unregister a device WebSocket connection."""
    _device_connections.pop(device_id, None)
    logger.info("Device disconnected: %s", device_id)


async def send_to_device(device_id: str, command: str, payload: dict = None) -> bool:
    """Send a command to a device via WebSocket."""
    ws = _device_connections.get(device_id)
    if not ws:
        logger.warning("Device %s not connected.", device_id)
        return False

    try:
        await ws.send_json({"command": command, "payload": payload or {}})
        return True
    except Exception as exc:
        logger.error("Failed to send to device %s: %s", device_id, exc)
        return False


async def broadcast_device_state(device_id: str, state: dict) -> None:
    """Broadcast device state to all watching app connections."""
    watchers = _app_watchers.get(device_id, [])
    disconnected = []

    for ws in watchers:
        try:
            await ws.send_json({"type": "device_state", "data": state})
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        watchers.remove(ws)


async def register_app_watcher(device_id: str, ws: WebSocket) -> None:
    """Register a companion app WebSocket to watch a device."""
    if device_id not in _app_watchers:
        _app_watchers[device_id] = []
    _app_watchers[device_id].append(ws)


async def unregister_app_watcher(device_id: str, ws: WebSocket) -> None:
    """Unregister a companion app WebSocket."""
    watchers = _app_watchers.get(device_id, [])
    if ws in watchers:
        watchers.remove(ws)
