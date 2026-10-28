import os
import sys
import io
import base64
import ctypes
from typing import Tuple, Optional
from PIL import Image
import mss

_default_desktop_handle = None

def attach_default_desktop() -> bool:
    """
    On Windows, ensures the current thread is attached to the interactive 'Default' desktop.
    Must be called before any GDI/Window hooks are created on the thread.
    """
    global _default_desktop_handle
    if sys.platform != "win32":
        return True
    try:
        user32 = ctypes.windll.user32
        if _default_desktop_handle is None:
            _default_desktop_handle = user32.OpenDesktopW("Default", 0, False, 0x10000000)
        if _default_desktop_handle:
            res = user32.SetThreadDesktop(_default_desktop_handle)
            return bool(res)
    except Exception:
        pass
    return False

attach_default_desktop()


def get_screen_resolution(monitor_index: int = 1) -> Tuple[int, int]:
    """
    Returns the (width, height) in pixels of the specified monitor (default 1 = primary).
    """
    attach_default_desktop()
    try:
        with mss.MSS() as sct:
            if monitor_index < len(sct.monitors):
                mon = None
                if monitor_index == 1:
                    mon = next((m for m in sct.monitors[1:] if m.get("is_primary")), sct.monitors[1])
                else:
                    mon = sct.monitors[monitor_index]
                return mon["width"], mon["height"]
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass

    return 1920, 1080


def capture_screen(
    monitor_index: int = 1,
    max_dimension: int = 1280,
    quality: int = 85,
    save_path: Optional[str] = None
) -> Tuple[str, Tuple[int, int]]:
    """
    Captures the primary (or specified) screen, returns:
    (base64_encoded_jpeg_string, (original_width, original_height))
    
    The image is automatically downscaled if its width or height exceeds max_dimension
    to optimize Ollama VLM latency and token memory while preserving fine visual details.
    """
    attach_default_desktop()
    img = None
    orig_size = (1920, 1080)

    try:
        with mss.MSS() as sct:
            mon = None
            if monitor_index == 1:
                mon = next((m for m in sct.monitors[1:] if m.get("is_primary")), sct.monitors[1])
            elif monitor_index < len(sct.monitors):
                mon = sct.monitors[monitor_index]
            else:
                mon = sct.monitors[1]
                
            orig_size = (mon["width"], mon["height"])
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            orig_size = img.size
        except Exception as fallback_err:
            raise RuntimeError(f"Screen capture failed: mss ({e}), ImageGrab ({fallback_err})")

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        img.save(save_path)

    vlm_img = img.copy()
    if max(vlm_img.size) > max_dimension:
        vlm_img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    vlm_img.save(buffer, format="JPEG", quality=quality)
    base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return base64_str, orig_size
