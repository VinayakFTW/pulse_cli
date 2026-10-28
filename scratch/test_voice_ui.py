import os
import sys
import time
import json
import torch
import numpy as np
import requests
import asyncio
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pulse_ui.voice_server import (
    start_voice_server,
    broadcast_state,
    broadcast_amplitude,
    get_server_port,
    is_voice_paused,
    set_voice_paused,
    toggle_voice_pause,
)
from pulse_ear.speech_handler import (
    set_amplitude_callback,
    set_user_amplitude_callback,
    play_stream_monitored,
)


def test_server_and_static_files():
    print("\n[Test 1] Starting Voice Server & Verifying Static Assets...")
    port = start_voice_server(port=8765)
    base_url = f"http://127.0.0.1:{port}"

    # Verify health
    res = requests.get(f"{base_url}/health", timeout=3)
    assert res.status_code == 200, f"Health check failed with {res.status_code}"
    data = res.json()
    assert data["status"] == "ok"
    print(f"  [OK] /health returned 200 OK ({data})")

    # Verify index.html contains canvas and pause controls
    res = requests.get(f"{base_url}/", timeout=3)
    assert res.status_code == 200
    assert "<canvas id=\"orb-canvas\"" in res.text
    assert "pause-btn" in res.text
    print("  [OK] / served index.html containing #orb-canvas and #pause-btn")

    # Verify orb.js contains 5000 nano particles
    res_orb = requests.get(f"{base_url}/static/orb.js", timeout=3)
    assert res_orb.status_code == 200
    assert "particleCount = 5000" in res_orb.text
    assert "NanoParticle" in res_orb.text
    print("  [OK] /static/orb.js served with 5,000 nano particles configured")

    # Verify style.css and app.js
    for asset in ["style.css", "app.js"]:
        res = requests.get(f"{base_url}/static/{asset}", timeout=3)
        assert res.status_code == 200
        assert len(res.text) > 50
        print(f"  [OK] /static/{asset} served ({len(res.text)} bytes)")


async def _async_ws_test(port):
    ws_url = f"ws://127.0.0.1:{port}/ws/voice"
    async with websockets.connect(ws_url) as ws:
        # First message is initial state
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "state", f"Expected state message, got: {msg}"
        print(f"  [OK] Initial WS state received: {msg}")

        # Second message is initial pause_state
        raw_pause = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg_pause = json.loads(raw_pause)
        assert msg_pause["type"] == "pause_state"
        print(f"  [OK] Initial WS pause_state received: {msg_pause}")

        # Broadcast state update
        broadcast_state("speaking")
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "state" and msg["state"] == "speaking"
        print(f"  [OK] State update 'speaking' received: {msg}")

        # Broadcast amplitude update
        broadcast_amplitude(0.72)
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "amplitude" and abs(msg["value"] - 0.72) < 0.01
        print(f"  [OK] Real-time amplitude telemetry received: {msg}")

        # Test toggle_pause action over WebSocket
        print("  Testing client toggle_pause action...")
        await ws.send(json.dumps({"action": "toggle_pause"}))
        await asyncio.sleep(0.1)

        # Should receive state 'paused' and pause_state {paused: True}
        msg1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        msg2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        received_types = {msg1["type"], msg2["type"]}
        assert "pause_state" in received_types and "state" in received_types
        assert is_voice_paused() is True
        print("  [OK] Voice paused via WebSocket action verified")

        # Toggle back to resume
        await ws.send(json.dumps({"action": "toggle_pause"}))
        await asyncio.sleep(0.1)
        assert is_voice_paused() is False
        print("  [OK] Voice resumed via WebSocket action verified")


def test_websocket_telemetry_and_pause():
    print("\n[Test 2] Testing WebSocket Telemetry & Pause Actions...")
    port = get_server_port()
    asyncio.run(_async_ws_test(port))


def test_monitored_audio_playback():
    print("\n[Test 3] Testing Monitored Audio Stream & Amplitude Hook...")
    received_amplitudes = []

    def mock_amplitude_cb(val):
        received_amplitudes.append(val)

    set_amplitude_callback(mock_amplitude_cb)

    # Generate synthetic audio stream chunks
    def dummy_audio_stream():
        sr = 32000
        chunk_len = 800
        t = np.linspace(0, 0.2, sr // 5)
        sine = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        for i in range(0, len(sine), chunk_len):
            chunk = sine[i : i + chunk_len]
            if len(chunk) > 0:
                yield torch.from_numpy(chunk)

    play_stream_monitored(dummy_audio_stream(), sample_rate=32000)

    assert len(received_amplitudes) > 0
    assert received_amplitudes[-1] == 0.0
    max_amp = max(received_amplitudes)
    print(f"  [OK] Stream playback monitored: {len(received_amplitudes)} chunks processed, peak amp: {max_amp:.3f}")
    assert max_amp > 0.05


def main():
    print("=" * 60)
    print("      Pulse AI - Nano-Orb & Pause Engine Verification")
    print("=" * 60)

    try:
        test_server_and_static_files()
        test_websocket_telemetry_and_pause()
        test_monitored_audio_playback()
        print("\n" + "=" * 60)
        print("   ALL TESTS PASSED: 5,000 Nano-Orb & Pause Ready!   ")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAILED] Verification error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
