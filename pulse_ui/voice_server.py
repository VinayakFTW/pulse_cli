import asyncio
import json
import logging
import os
import socket
import threading
import time
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title="Pulse Voice UI", docs_url=None, redoc_url=None)

# Mount static files
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# WebSocket state
_active_connections: Set[WebSocket] = set()
_connections_lock = threading.Lock()
_server_loop: asyncio.AbstractEventLoop | None = None
_current_state: str = "idle"
_current_amplitude: float = 0.0
_is_paused: bool = False
_server_thread: threading.Thread | None = None
_server_port: int = 8765
_server_instance: uvicorn.Server | None = None


def is_voice_paused() -> bool:
    """Returns whether voice recording is currently paused."""
    global _is_paused
    return _is_paused


def set_voice_paused(paused: bool):
    """Sets the voice pause state and broadcasts it to all connected clients."""
    global _is_paused
    _is_paused = bool(paused)
    new_state = "paused" if _is_paused else "listening"
    broadcast_state(new_state)

    payload = {"type": "pause_state", "paused": _is_paused}
    if _server_loop and _server_loop.is_running():
        asyncio.run_coroutine_threadsafe(_async_broadcast(payload), _server_loop)


def toggle_voice_pause() -> bool:
    """Toggles voice pause state and returns the new value."""
    global _is_paused
    set_voice_paused(not _is_paused)
    return _is_paused


@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "Voice UI static files not found"}, status_code=404)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "state": _current_state,
        "paused": _is_paused,
        "clients": len(_active_connections),
    }


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    global _server_loop
    await websocket.accept()

    # Store the loop running this coroutine for threadsafe dispatch
    _server_loop = asyncio.get_running_loop()

    with _connections_lock:
        _active_connections.add(websocket)

    # Send initial state and pause snapshot immediately
    try:
        await websocket.send_text(json.dumps({
            "type": "state",
            "state": "paused" if _is_paused else _current_state,
        }))
        await websocket.send_text(json.dumps({
            "type": "pause_state",
            "paused": _is_paused,
        }))
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif action == "toggle_pause":
                    toggle_voice_pause()
                elif action == "pause":
                    set_voice_paused(True)
                elif action == "resume":
                    set_voice_paused(False)
            except Exception:
                pass
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        with _connections_lock:
            _active_connections.discard(websocket)


async def _async_broadcast(payload: dict):
    with _connections_lock:
        connections = list(_active_connections)

    if not connections:
        return

    text = json.dumps(payload)
    for ws in connections:
        try:
            await ws.send_text(text)
        except Exception:
            with _connections_lock:
                _active_connections.discard(ws)


def broadcast_state(state: str):
    """
    Broadcasts state transition ('idle', 'listening', 'thinking', 'speaking', 'paused')
    to all active UI clients thread-safely.
    """
    global _current_state, _server_loop
    _current_state = state

    payload = {"type": "state", "state": state}
    if _server_loop and _server_loop.is_running():
        asyncio.run_coroutine_threadsafe(_async_broadcast(payload), _server_loop)


def broadcast_amplitude(value: float, state: str = "speaking"):
    """
    Broadcasts real-time audio amplitude [0.0, 1.0] to all active UI clients thread-safely.
    """
    global _current_amplitude, _server_loop
    _current_amplitude = max(0.0, min(1.0, float(value)))

    payload = {
        "type": "amplitude",
        "value": round(_current_amplitude, 4),
        "state": state,
    }
    if _server_loop and _server_loop.is_running():
        asyncio.run_coroutine_threadsafe(_async_broadcast(payload), _server_loop)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def get_server_port() -> int:
    return _server_port


def start_voice_server(host: str = "127.0.0.1", port: int = 8765) -> int:
    """
    Launches Uvicorn with FastAPI app in a background daemon thread.
    Returns the port the server is running on.
    """
    global _server_thread, _server_port, _server_instance

    if _server_thread and _server_thread.is_alive():
        return _server_port

    # If the default port is already in use by a running instance of our server, reuse it
    if is_port_in_use(port, host):
        _server_port = port
        return _server_port

    _server_port = port
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    _server_instance = uvicorn.Server(config)

    def _run_server():
        _server_instance.run()

    _server_thread = threading.Thread(target=_run_server, daemon=True, name="PulseVoiceServerThread")
    _server_thread.start()

    # Wait until server starts listening
    t0 = time.time()
    while time.time() - t0 < 3.0:
        if is_port_in_use(_server_port, host):
            break
        time.sleep(0.05)

    return _server_port
