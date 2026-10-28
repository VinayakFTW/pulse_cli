import re
import os
from typing import TypedDict, List, Dict, Any, Optional, Tuple, Literal
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

from pulse_eye.screen_capture import capture_screen, get_screen_resolution
from pulse_eye.computer_use import *
from pulse_eye.vlm_client import VLMClient

class VisionAgentState(TypedDict):
    task: str
    task_mode: Literal["read", "act"]
    step: int
    max_steps: int
    screenshot_b64: Optional[str]
    screen_size: Tuple[int, int]
    readings: Optional[str]
    plan: Optional[Dict[str, Any]]
    action_history: List[Dict[str, Any]]
    is_complete: bool
    error: Optional[str]
    output_message: str


@tool
def click_screen(x_norm: float, y_norm: float, button: str = "left", clicks: int = 1) -> str:
    """Clicks on the screen at normalized coordinates (0-1000 scale)."""
    screen_size = get_screen_resolution()
    px_x, px_y = denormalize_coordinates(x_norm, y_norm, screen_size)
    return click_at(px_x, px_y, button=button, clicks=clicks, screen_size=screen_size)

@tool
def double_click_screen(x_norm: float, y_norm: float) -> str:
    """Double clicks on the screen at normalized coordinates (0-1000 scale)."""
    screen_size = get_screen_resolution()
    px_x, px_y = denormalize_coordinates(x_norm, y_norm, screen_size)
    return double_click_at(px_x, px_y, screen_size=screen_size)

@tool
def right_click_screen(x_norm: float, y_norm: float) -> str:
    """Right clicks on the screen at normalized coordinates (0-1000 scale)."""
    screen_size = get_screen_resolution()
    px_x, px_y = denormalize_coordinates(x_norm, y_norm, screen_size)
    return right_click_at(px_x, px_y, screen_size=screen_size)

@tool
def type_text(text: str, press_enter: bool = False) -> str:
    """Types text on the keyboard with optional Enter key press."""
    return type_keyboard_text(text, press_enter=press_enter)

@tool
def press_key(key: str) -> str:
    """Presses a single key (e.g. 'enter', 'tab', 'esc', 'backspace', 'down')."""
    return press_keyboard_key(key)

@tool
def trigger_hotkey(keys: List[str]) -> str:
    """Sends a key combination, e.g. ['ctrl', 'c'] or ['alt', 'tab']."""
    return send_hotkey(keys)

@tool
def scroll_page(amount: int = 3, direction: str = "down") -> str:
    """Scrolls the active window page up or down."""
    return scroll_screen(amount, direction)

@tool
def wait_delay(seconds: float = 1.0) -> str:
    """Pauses for UI rendering or animations."""
    return wait_seconds(seconds)

ASSIGNED_TOOLS = [
    click_screen,
    double_click_screen,
    right_click_screen,
    type_text,
    press_key,
    trigger_hotkey,
    scroll_page,
    wait_delay,
]


def classify_task_mode(task: str) -> Literal["read", "act"]:
    """
    Classifies whether the user instruction is a visual reading task or an interactive computer-use action.
    """
    task_lower = task.lower().strip()
    
    interactive_keywords = [
        "click", "double click", "right click", "tap", "type", "press",
        "hotkey", "scroll", "drag", "select", "navigate to", "open application",
        "submit form", "enter text", "focus on", "fill in"
    ]
    for kw in interactive_keywords:
        if re.search(rf"\b{re.escape(kw)}\b", task_lower):
            return "act"

    return "read"


def node_init(state: VisionAgentState) -> Dict[str, Any]:
    task = state.get("task", "")
    mode = classify_task_mode(task)
    screen_res = get_screen_resolution()
    return {
        "task_mode": mode,
        "step": 0,
        "max_steps": state.get("max_steps", 5 if mode == "act" else 1),
        "screen_size": screen_res,
        "action_history": [],
        "is_complete": False,
        "error": None,
        "output_message": "",
    }


def node_capture(state: VisionAgentState) -> Dict[str, Any]:
    try:
        b64_str, size = capture_screen(max_dimension=1280, quality=85)
        return {
            "screenshot_b64": b64_str,
            "screen_size": size,
        }
    except Exception as e:
        return {
            "error": f"Failed to capture screen: {e}",
            "is_complete": True,
            "output_message": f"Screen capture failed: {e}"
        }


def node_vlm_read(state: VisionAgentState) -> Dict[str, Any]:
    vlm = VLMClient()
    b64_img = state.get("screenshot_b64")
    task = state.get("task", "Describe the current screen")

    try:
        healthy, msg = vlm.check_health()
        if not healthy:
            return {
                "error": msg,
                "is_complete": True,
                "output_message": f"Vision Model unavailable: {msg}"
            }

        reading = vlm.read_screen(base64_image=b64_img, query=task)
        return {
            "readings": reading,
            "is_complete": True,
            "output_message": reading
        }
    except Exception as e:
        err = f"VLM reading error: {e}"
        return {
            "error": err,
            "is_complete": True,
            "output_message": err
        }


def node_vlm_plan_action(state: VisionAgentState) -> Dict[str, Any]:
    vlm = VLMClient()
    b64_img = state.get("screenshot_b64")
    task = state.get("task", "")
    history = state.get("action_history", [])

    try:
        healthy, msg = vlm.check_health()
        if not healthy:
            return {
                "error": msg,
                "is_complete": True,
                "output_message": f"Vision Model unavailable: {msg}"
            }

        plan = vlm.plan_computer_use_action(
            base64_image=b64_img,
            task=task,
            action_history=history
        )
        return {"plan": plan}

    except Exception as e:
        err = f"VLM planning error: {e}"
        return {
            "error": err,
            "is_complete": True,
            "output_message": err
        }


def node_execute_action(state: VisionAgentState) -> Dict[str, Any]:
    plan = state.get("plan") or {}
    action = plan.get("action", "finish")
    thought = plan.get("thought", "")
    screen_size = state.get("screen_size", (1920, 1080))
    step = state.get("step", 0) + 1
    max_steps = state.get("max_steps", 5)
    history = list(state.get("action_history", []))

    if action == "finish" or not action:
        finish_msg = plan.get("finish_message") or thought or "Task completed successfully."
        return {
            "step": step,
            "is_complete": True,
            "output_message": finish_msg
        }

    px_x, px_y = None, None
    if "bbox" in plan and plan["bbox"] and len(plan["bbox"]) == 4:
        px_x, px_y = bbox_to_center_coords(plan["bbox"], screen_size)
    elif "point" in plan and plan["point"] and len(plan["point"]) == 2:
        px_x, px_y = denormalize_coordinates(plan["point"][0], plan["point"][1], screen_size)

    result_str = ""
    try:
        if action == "click":
            if px_x is not None and px_y is not None:
                result_str = click_at(px_x, px_y, button="left", clicks=1, screen_size=screen_size)
            else:
                result_str = "Error: Click action requested without valid point or bbox coordinates."

        elif action == "double_click":
            if px_x is not None and px_y is not None:
                result_str = double_click_at(px_x, px_y, screen_size=screen_size)
            else:
                result_str = "Error: Double click requested without valid coordinates."

        elif action == "right_click":
            if px_x is not None and px_y is not None:
                result_str = right_click_at(px_x, px_y, screen_size=screen_size)
            else:
                result_str = "Error: Right click requested without valid coordinates."

        elif action == "move":
            if px_x is not None and px_y is not None:
                result_str = move_cursor_to(px_x, px_y, screen_size=screen_size)
            else:
                result_str = "Error: Move requested without valid coordinates."

        elif action == "type":
            text = plan.get("text", "")
            press_enter = plan.get("press_enter", False)
            result_str = type_keyboard_text(text, press_enter=press_enter)

        elif action == "press_key":
            key = plan.get("key", "enter")
            result_str = press_keyboard_key(key)

        elif action == "hotkey":
            keys = plan.get("keys", ["enter"])
            result_str = send_hotkey(keys)

        elif action == "scroll":
            direction = plan.get("direction", "down")
            amount = plan.get("amount", 3)
            result_str = scroll_screen(amount=amount, direction=direction)

        elif action == "wait":
            seconds = plan.get("seconds", 1.0)
            result_str = wait_seconds(seconds)

        else:
            result_str = f"Unknown action '{action}'."

    except Exception as e:
        result_str = f"Action execution error: {e}"

    history.append({
        "step": step,
        "thought": thought,
        "action": action,
        "coordinates": (px_x, px_y) if px_x is not None else None,
        "result": result_str
    })

    is_complete = (step >= max_steps)
    summary = f"Executed {action}: {result_str}"
    if is_complete and not state.get("output_message"):
        summary += f" (Reached maximum action steps limit: {max_steps})"

    return {
        "step": step,
        "action_history": history,
        "is_complete": is_complete,
        "output_message": summary
    }


def route_mode(state: VisionAgentState) -> str:
    if state.get("is_complete"):
        return END
    return "read" if state.get("task_mode") == "read" else "act"


def route_action_completion(state: VisionAgentState) -> str:
    if state.get("is_complete"):
        return END
    return "capture"


def build_vision_graph():
    """
    Constructs and compiles the LangGraph StateGraph for Vision & Computer Use.
    """
    graph = StateGraph(VisionAgentState)

    graph.add_node("init", node_init)
    graph.add_node("capture", node_capture)
    graph.add_node("read", node_vlm_read)
    graph.add_node("plan", node_vlm_plan_action)
    graph.add_node("act", node_execute_action)

    graph.add_edge(START, "init")
    graph.add_edge("init", "capture")

    graph.add_conditional_edges(
        "capture",
        route_mode,
        {
            "read": "read",
            "act": "plan",
            END: END
        }
    )

    graph.add_edge("read", END)
    graph.add_edge("plan", "act")

    graph.add_conditional_edges(
        "act",
        route_action_completion,
        {
            "capture": "capture",
            END: END
        }
    )

    return graph.compile()


_vision_graph = build_vision_graph()


def run_vision_agent(task_description: str, max_steps: int = 5) -> str:
    """
    Main entry point for Pulse: runs the LangGraph Vision Agent for visual reading or computer use.
    Returns a concise textual summary / reading suitable for speech and CLI display.
    """
    initial_state: VisionAgentState = {
        "task": task_description,
        "task_mode": "read",
        "step": 0,
        "max_steps": max_steps,
        "screenshot_b64": None,
        "screen_size": (1920, 1080),
        "readings": None,
        "plan": None,
        "action_history": [],
        "is_complete": False,
        "error": None,
        "output_message": "",
    }

    try:
        final_state = _vision_graph.invoke(initial_state)
        return final_state.get("output_message") or final_state.get("readings") or "Vision task finished."
    except Exception as e:
        return f"Error executing vision agent: {e}"
