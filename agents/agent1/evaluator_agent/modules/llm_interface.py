import os
import logging
from typing import Any, Dict, List, Optional

import requests


class LLMInterface:
    """Minimal LLM interface for generating evaluation summaries.

    Uses a hypothetical GPT-5 reasoning API with an OpenAI-compatible endpoint if available.
    Set env: GPT5_API_BASE, GPT5_API_KEY, GPT5_MODEL
    Fallback: produce a rule-based short summary if API not configured.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.api_base = os.getenv("GPT5_API_BASE", "https://api.openai.com/v1")
        self.api_key = os.getenv("GPT5_API_KEY")
        self.model = os.getenv("GPT5_MODEL", "gpt-5-reasoning")

    def summarize(self, task: Dict[str, Any]) -> str:
        if not self.api_key:
            return self._fallback_summary(task)

        logs: List[Dict[str, Any]] = task.get("logs", [])
        sample = "\n".join([f"[{l.get('timestamp')}] {l.get('level')}: {str(l.get('message'))[:200]}" for l in logs[-50:]])
        m = task.get("metrics", {})
        prompt = (
            "You are an evaluator of an autonomous agent. Summarize the agent's performance, correctness, autonomy behavior, and notable events.\n"
            f"Metrics: {m}\n"
            f"Recent logs:\n{sample}\n"
            "Provide a concise, objective assessment."
        )
        try:
            resp = requests.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a precise evaluation summarizer."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 300,
                },
                timeout=20,
            )
            if resp.ok:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                return content or self._fallback_summary(task)
        except Exception:
            pass
        return self._fallback_summary(task)

    def _fallback_summary(self, task: Dict[str, Any]) -> str:
        m = task.get("metrics", {})
        return (
            "Evaluation summary based on heuristics: "
            f"completion_time={m.get('completion_time_s', 0.0)}s, "
            f"errors={m.get('error_count', 0)}, retries={m.get('retry_count', 0)}, "
            f"dependency_requests={m.get('human_or_agent_requests', 0)}, api_calls={m.get('total_api_calls', 0)}."
        )
