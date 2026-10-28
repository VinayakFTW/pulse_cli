import unittest
from unittest.mock import patch, MagicMock
from pulse_eye.screen_capture import get_screen_resolution, capture_screen
from pulse_eye.computer_use import (
    denormalize_coordinates,
    bbox_to_center_coords,
    scroll_screen,
    wait_seconds,
    type_keyboard_text,
    press_keyboard_key,
    send_hotkey
)
from pulse_eye.vlm_client import VLMClient
from pulse_eye.vision_agent import (
    classify_task_mode,
    build_vision_graph,
    ASSIGNED_TOOLS,
    VisionAgentState
)
from pulse_brain.llm_interface import parse_tool_call
from pulse_config.config import ROUTER_SYSTEM_PROMPT


class TestPulseEye(unittest.TestCase):

    def test_screen_resolution(self):
        width, height = get_screen_resolution()
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)

    def test_capture_screen(self):
        b64_str, (orig_w, orig_h) = capture_screen(max_dimension=640)
        self.assertIsInstance(b64_str, str)
        self.assertGreater(len(b64_str), 100)
        self.assertGreater(orig_w, 0)
        self.assertGreater(orig_h, 0)

    def test_denormalize_coordinates(self):
        screen = (1920, 1080)
        # Center
        self.assertEqual(denormalize_coordinates(500, 500, screen), (960, 540))
        # Top-left
        self.assertEqual(denormalize_coordinates(0, 0, screen), (0, 0))
        # Bottom-right
        self.assertEqual(denormalize_coordinates(1000, 1000, screen), (1919, 1079))
        # Clamping out-of-bounds
        self.assertEqual(denormalize_coordinates(-50, 1200, screen), (0, 1079))

    def test_bbox_to_center_coords(self):
        screen = (1920, 1080)
        bbox = [100, 200, 300, 400]  # ymin, xmin, ymax, xmax
        # center is (300, 200) -> 300/1000*1920 = 576, 200/1000*1080 = 216
        self.assertEqual(bbox_to_center_coords(bbox, screen), (576, 216))

    def test_task_mode_classification(self):
        self.assertEqual(classify_task_mode("What is on my screen?"), "read")
        self.assertEqual(classify_task_mode("Read the text in the active window"), "read")
        self.assertEqual(classify_task_mode("Summarize the open document"), "read")
        self.assertEqual(classify_task_mode("Click the submit button"), "act")
        self.assertEqual(classify_task_mode("Find the search box and type hello"), "act")
        self.assertEqual(classify_task_mode("Scroll down to read more"), "act")

    def test_vlm_json_extraction(self):
        vlm = VLMClient()
        
        # 1. Markdown code fence
        raw_md = '```json\n{"thought": "test", "action": "click", "point": [100, 200]}\n```'
        parsed = vlm.extract_json_decision(raw_md)
        self.assertEqual(parsed["action"], "click")
        self.assertEqual(parsed["point"], [100, 200])

        # 2. Preamble text with JSON
        raw_text = 'Here is what to do:\n{"thought": "found it", "action": "finish", "finish_message": "done"}'
        parsed2 = vlm.extract_json_decision(raw_text)
        self.assertEqual(parsed2["action"], "finish")
        self.assertEqual(parsed2["finish_message"], "done")

        # 3. Malformed fallback
        parsed3 = vlm.extract_json_decision("No json here at all")
        self.assertEqual(parsed3["action"], "finish")
        self.assertIn("No json here at all", parsed3["finish_message"])

    def test_langgraph_compilation(self):
        graph = build_vision_graph()
        self.assertIsNotNone(graph)
        self.assertGreaterEqual(len(ASSIGNED_TOOLS), 7)

    def test_parse_tool_call_routing(self):
        t_name, params = parse_tool_call("[TOOL: vision_agent, task: inspect screen and read terminal]")
        self.assertEqual(t_name, "vision_agent")
        self.assertEqual(params["task"], "inspect screen and read terminal")

        t_name2, params2 = parse_tool_call("[TOOL: cli_agent, task: run ls]")
        self.assertEqual(t_name2, "cli_agent")
        self.assertEqual(params2["task"], "run ls")

    def test_router_prompt_contains_vision(self):
        self.assertIn("VISION & COMPUTER USE AGENT TASK", ROUTER_SYSTEM_PROMPT)
        self.assertIn("vision_agent", ROUTER_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
