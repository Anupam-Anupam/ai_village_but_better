import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


SCHEMA_WEIGHTS = {
    "correctness": 0.35,
    "efficiency": 0.15,
    "quality": 0.15,
    "stability": 0.10,
    "autonomy": 0.15,
    "resource_efficiency": 0.10,
}


class ReportBuilder:
    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def build_report(self, data: Dict[str, Any], score_pack: Dict[str, Any], summary: str) -> Dict[str, Any]:
        task_id = str(data.get("task_id"))
        agent_id = str(data.get("agent_id"))
        metrics = data.get("metrics", {})
        evaluated_at = datetime.now(timezone.utc).isoformat()

        report = {
            "task_id": task_id,
            "agent_id": agent_id,
            "scores": score_pack.get("scores", {}),
            "metrics": {
                "completion_time_s": float(metrics.get("completion_time_s", 0.0)),
                "error_count": int(metrics.get("error_count", 0)),
                "retry_count": int(metrics.get("retry_count", 0)),
                "human_or_agent_requests": int(metrics.get("human_or_agent_requests", 0)),
                "total_api_calls": int(metrics.get("total_api_calls", 0)),
                "memory_usage_mb": float(metrics.get("memory_usage_mb", 0.0)),
                "cpu_usage_percent": float(metrics.get("cpu_usage_percent", 0.0)),
                "cost_usd": float(metrics.get("cost_usd", 0.0)),
            },
            "weights": SCHEMA_WEIGHTS,
            "penalties": score_pack.get("penalties", {}),
            "evaluation_summary": summary,
            "evaluated_at": evaluated_at,
            "version": "v1.3",
        }
        self.logger.info(json.dumps({"event": "report_built", "task_id": task_id, "agent_id": agent_id}))
        return report

    def aggregate(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "count": len(reports),
            "avg_final_score": (sum(r.get("scores", {}).get("final_score", 0.0) for r in reports) / len(reports)) if reports else 0.0,
            "reports": reports,
        }
