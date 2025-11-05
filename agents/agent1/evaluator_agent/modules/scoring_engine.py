from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal


DEFAULT_WEIGHTS = {
    "correctness": 0.35,
    "efficiency": 0.15,
    "quality": 0.15,
    "stability": 0.10,
    "autonomy": 0.15,
    "resource_efficiency": 0.10,
}


class ScoringEngine:
    def __init__(self, logger: Optional[logging.Logger] = None, weights: Optional[Dict[str, float]] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.weights = weights or DEFAULT_WEIGHTS

    def _clip(self, v: float) -> float:
        return max(0.0, min(1.0, v))

    def score_task(self, data: Dict[str, Any], num_agents: int = 1) -> Dict[str, Any]:
        m = data.get("metrics", {})
        logs: List[Dict[str, Any]] = data.get("logs", [])

        # Heuristic scoring
        error_count = float(m.get("error_count", 0))
        retry_count = float(m.get("retry_count", 0))
        deps = float(m.get("human_or_agent_requests", 0))
        completion_time = float(m.get("completion_time_s", 0.0))
        total_api_calls = float(m.get("total_api_calls", 0))
        mem = float(m.get("memory_usage_mb", 0.0))
        cpu = float(m.get("cpu_usage_percent", 0.0))

        # correctness: inverse of errors, plus progress completion evidence
        progress = data.get("progress", [])
        progress_ratio = 0.0
        if progress:
            # try to infer completion from status/progress columns
            last = progress[-1]
            status = (str(last.get("status") or "").lower())
            prog = last.get("progress")
            # Accept Decimal or string numeric
            if isinstance(prog, Decimal):
                prog = float(prog)
            elif isinstance(prog, str):
                try:
                    prog = float(prog.strip())
                except Exception:
                    prog = None
            if isinstance(prog, (int, float)):
                progress_ratio = max(0.0, min(1.0, float(prog))) if float(prog) <= 1 else min(1.0, float(prog) / 100.0)
            if "done" in status or "complete" in status or status == "success":
                progress_ratio = max(progress_ratio, 1.0)
        correctness = self._clip(0.9 * progress_ratio + 0.1 * (1.0 / (1.0 + error_count)))

        # efficiency: shorter completion, fewer API calls, fewer retries
        efficiency = self._clip(0.4 * (1.0 / (1.0 + completion_time / 300.0)) + 0.3 * (1.0 / (1.0 + total_api_calls / 50.0)) + 0.3 * (1.0 / (1.0 + retry_count)))

        # quality: fewer errors and retries + some stability reflection
        quality = self._clip(0.6 * (1.0 / (1.0 + error_count)) + 0.4 * (1.0 / (1.0 + retry_count)))

        # stability: inversely related to errors and long runs
        stability = self._clip(0.5 * (1.0 / (1.0 + error_count)) + 0.5 * (1.0 / (1.0 + completion_time / 600.0)))

        # autonomy: penalize dependency requests
        autonomy = self._clip(1.0 / (1.0 + deps))

        # resource_efficiency: low mem and CPU use is better
        resource_efficiency = self._clip(0.5 * (1.0 / (1.0 + mem / 1024.0)) + 0.5 * (1.0 / (1.0 + cpu / 100.0)))

        penalties = {
            "dependency_penalty": min(0.3, 0.05 * deps),
            "timeout_penalty": 0.0,  # could be inferred from logs in future
            "error_penalty": min(0.3, 0.05 * error_count),
        }

        weighted = (
            self.weights["correctness"] * correctness
            + self.weights["efficiency"] * efficiency
            + self.weights["quality"] * quality
            + self.weights["stability"] * stability
            + self.weights["autonomy"] * autonomy
            + self.weights["resource_efficiency"] * resource_efficiency
        )
        final_score = max(0.0, weighted - sum(penalties.values()))

        # Cost adjustment: divide score by total task cost if provided
        cost = float(m.get("cost_usd", 0.0) or 0.0)
        if cost > 0:
            final_score = final_score / cost

        scores = {
            "correctness": round(correctness, 4),
            "efficiency": round(efficiency, 4),
            "quality": round(quality, 4),
            "stability": round(stability, 4),
            "autonomy": round(autonomy, 4),
            "resource_efficiency": round(resource_efficiency, 4),
            "final_score": round(final_score, 4),
        }

        return {"scores": scores, "penalties": penalties}
