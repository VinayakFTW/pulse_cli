import json
import re
import requests
from typing import Tuple, Dict, Any, Optional, List
from pulse_eye.prompts import VISION_READER_PROMPT, COMPUTER_USE_PROMPT

class VLMClient:
    """
    Communicates with local Ollama VLM instance (e.g. qwen2.5vl:3b or moondream).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5vl:3b",
        timeout: int = 60,
        keep_alive: str = "10m"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.keep_alive = keep_alive

    def check_health(self) -> Tuple[bool, str]:
        """
        Verifies Ollama server connectivity and model availability.
        """
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code != 200:
                return False, f"Ollama returned HTTP status {r.status_code}."
            
            data = r.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            
            target_prefix = self.model.split(":")[0]
            matched = any(self.model in m or target_prefix in m for m in models)
            if not matched:
                return False, (
                    f"Ollama is running, but model '{self.model}' was not found. "
                    f"Please run: ollama pull {self.model}"
                )
            return True, f"Ollama is healthy. Model '{self.model}' is ready."

        except requests.exceptions.ConnectionError:
            return False, (
                f"Cannot connect to Ollama at {self.base_url}. "
                "Please make sure Ollama is running ('ollama serve' or open the Ollama app)."
            )
        except Exception as e:
            return False, f"Error checking Ollama status: {e}"

    def query_vlm(
        self,
        user_prompt: str,
        base64_image: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Sends a multimodal chat completion request to the local Ollama instance.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_msg: Dict[str, Any] = {"role": "user", "content": user_prompt}
        if base64_image:
            user_msg["images"] = [base64_image]
        messages.append(user_msg)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            res_data = response.json()
            return res_data.get("message", {}).get("content", "").strip()

        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama VLM query timed out after {self.timeout} seconds.")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. Is 'ollama serve' running?"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama VLM query failed: {e}")

    def read_screen(self, base64_image: str, query: str) -> str:
        """
        Performs visual reading or question answering against the captured screenshot.
        """
        prompt = (
            f"User Question/Request: {query}\n\n"
            "Analyze the attached screenshot and provide your answer."
        )
        return self.query_vlm(
            user_prompt=prompt,
            base64_image=base64_image,
            system_prompt=VISION_READER_PROMPT
        )

    def plan_computer_use_action(
        self,
        base64_image: str,
        task: str,
        action_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Inspects the screenshot and task to return a structured JSON action dictionary.
        """
        history_text = ""
        if action_history:
            history_lines = []
            for idx, item in enumerate(action_history, 1):
                action = item.get("action", "unknown")
                result = item.get("result", "")
                history_lines.append(f"Step {idx}: action={action} -> result: {result}")
            history_text = "\nPREVIOUS ACTIONS TAKEN:\n" + "\n".join(history_lines) + "\n"

        prompt = (
            f"GOAL: {task}\n"
            f"{history_text}\n"
            "Inspect the current screen state and decide the exact next action to perform.\n"
            "Return ONLY valid JSON matching the specified schema."
        )

        response_str = self.query_vlm(
            user_prompt=prompt,
            base64_image=base64_image,
            system_prompt=COMPUTER_USE_PROMPT
        )

        return self.extract_json_decision(response_str)

    @staticmethod
    def extract_json_decision(response_str: str) -> Dict[str, Any]:
        """
        Extracts and parses JSON object from model response with markdown stripping and regex fallbacks.
        """
        cleaned = response_str.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            pass

        start_idx = cleaned.find("{")
        if start_idx != -1:
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(cleaned[start_idx:])
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        return {
            "thought": f"Could not parse structured JSON from VLM response: {response_str}",
            "action": "finish",
            "finish_message": response_str
        }
