import os
import sys
import time
import subprocess
import webbrowser
from typing import Optional

_ui_process: Optional[subprocess.Popen] = None


def run_window_process(url: str, width: int = 650, height: int = 650):
    """
    Subprocess entry point to run pywebview in its own clean GUI process.
    """
    try:
        import webview
        # Create frameless, draggable, fixed-size desktop window
        window = webview.create_window(
            title="Pulse AI - Voice",
            url=url,
            width=width,
            height=height,
            resizable=False,
            frameless=True,
            easy_drag=True,
            on_top=False,
            background_color="#070a10",
        )
        webview.start(gui="edgechromium", debug=False)
    except Exception as e:
        print(f"[Voice UI] Falling back to default browser: {e}")
        webbrowser.open(url)


def launch_voice_ui(port: int = 8765, width: int = 650, height: int = 650) -> bool:
    """
    Starts the voice server, hooks amplitude callbacks, and launches the frameless desktop window.
    """
    global _ui_process

    # 1. Start background FastAPI server
    from pulse_ui.voice_server import start_voice_server, broadcast_amplitude
    from pulse_ear.speech_handler import set_amplitude_callback, set_user_amplitude_callback

    active_port = start_voice_server(port=port)
    url = f"http://127.0.0.1:{active_port}"

    # 2. Hook real-time amplitude callbacks from speech_handler
    set_amplitude_callback(lambda amp: broadcast_amplitude(amp, state="speaking"))
    set_user_amplitude_callback(lambda amp: broadcast_amplitude(amp, state="listening"))

    # 3. Check if window process is already running
    if _ui_process and _ui_process.poll() is None:
        return True

    # 4. Spawn frameless window in dedicated child process
    python_exe = sys.executable
    cmd = [
        python_exe,
        "-c",
        f"from pulse_ui.window_manager import run_window_process; run_window_process('{url}', {width}, {height})"
    ]

    try:
        _ui_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        print(f"[Voice UI] Frameless desktop window launched at {url}")
        return True
    except Exception as e:
        print(f"[Voice UI] Subprocess launch error ({e}). Opening in browser...")
        webbrowser.open(url)
        return False


def close_voice_ui():
    """Closes the voice UI window if running."""
    global _ui_process
    if _ui_process and _ui_process.poll() is None:
        try:
            _ui_process.terminate()
            _ui_process.wait(timeout=1.0)
        except Exception:
            try:
                _ui_process.kill()
            except Exception:
                pass
        _ui_process = None


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    run_window_process(target_url)
