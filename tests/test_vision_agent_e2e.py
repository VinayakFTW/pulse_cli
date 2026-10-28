import unittest
from unittest.mock import patch, MagicMock
from pulse_eye.vision_agent import run_vision_agent, build_vision_graph, VisionAgentState
from pulse_brain.llm_interface import tool_dispatcher


class TestVisionAgentE2E(unittest.TestCase):

    @patch("pulse_eye.vlm_client.VLMClient.check_health")
    @patch("pulse_eye.vlm_client.VLMClient.read_screen")
    def test_mock_read_workflow(self, mock_read, mock_health):
        mock_health.return_value = (True, "Ready")
        mock_read.return_value = "VS Code editor is open with test_pulse_eye.py."

        result = run_vision_agent("What is visible on the screen?")
        self.assertIn("VS Code editor is open", result)

    @patch("pulse_eye.vlm_client.VLMClient.check_health")
    @patch("pulse_eye.vlm_client.VLMClient.plan_computer_use_action")
    @patch("pulse_eye.vision_agent.click_at")
    def test_mock_act_workflow(self, mock_click, mock_plan, mock_health):
        mock_health.return_value = (True, "Ready")
        mock_click.return_value = "Clicked at pixel coordinates (960, 540)."
        
        # Step 1: click center
        # Step 2: finish
        mock_plan.side_effect = [
            {
                "thought": "Need to click center button",
                "action": "click",
                "point": [500, 500]
            },
            {
                "thought": "Button was clicked",
                "action": "finish",
                "finish_message": "Successfully clicked the target button."
            }
        ]

        result = run_vision_agent("Click the center button on screen", max_steps=2)
        self.assertTrue(mock_click.called)
        self.assertIn("Successfully clicked", result)

    @patch("pulse_eye.vision_agent.run_vision_agent")
    def test_tool_dispatcher_integration(self, mock_run_agent):
        mock_run_agent.return_value = "Observed terminal window."

        tool_name, tool_result = tool_dispatcher(
            "[TOOL: vision_agent, task: inspect screen]",
            model_obj=None,
            model_type="openai"
        )
        self.assertEqual(tool_name, "vision_agent")
        self.assertEqual(tool_result, "Observed terminal window.")
        mock_run_agent.assert_called_once_with("inspect screen")


if __name__ == "__main__":
    unittest.main()
