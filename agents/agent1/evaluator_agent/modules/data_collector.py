import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from storage import MongoAdapter, PostgresAdapter


class DataCollector:
    """Collects and normalizes data across Mongo and Postgres."""

    def __init__(self, mongo: MongoAdapter, pg: PostgresAdapter, logger: Optional[logging.Logger] = None) -> None:
        self.mongo = mongo
        self.pg = pg
        self.logger = logger or logging.getLogger(__name__)
        self.default_agent_id = os.getenv("DEFAULT_AGENT_ID")

    def _normalize_id(self, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def collect_for_task(self, agent_id: Optional[str], task_id: str) -> Dict[str, Any]:
        agent_id = self._normalize_id(agent_id or self.default_agent_id)
        task_id = self._normalize_id(task_id)

        logs = self.mongo.fetch_task_logs(agent_id, task_id)
        metrics = self.mongo.compute_basic_metrics(logs)
        progress = self.pg.get_task_progress(task_id)

        # Optional resource metrics extracted from logs heuristically
        mem_usage = 0.0
        cpu_usage = 0.0
        cost_usd = 0.0
        mem_re = re.compile(r"mem(ory)?[:=\s]+([0-9.]+)\s*mb", re.I)
        cpu_re = re.compile(r"cpu[:=\s]+([0-9.]+)\s*%", re.I)
        # Match common cost patterns e.g. cost: 0.0123, total_cost=$0.05, usd_cost=0.01
        cost_re = re.compile(r"(total_)?(usd_)?cost\s*[:=\s$]+([0-9]+(?:\.[0-9]+)?)", re.I)
        for l in logs:
            msg = l.get("message") or ""
            m1 = mem_re.search(msg)
            if m1:
                try:
                    mem_usage = max(mem_usage, float(m1.group(2)))
                except Exception:
                    pass
            m2 = cpu_re.search(msg)
            if m2:
                try:
                    cpu_usage = max(cpu_usage, float(m2.group(1)))
                except Exception:
                    pass
            mc = cost_re.search(msg)
            if mc:
                try:
                    cost_usd = max(cost_usd, float(mc.group(3)))
                except Exception:
                    pass
            # Also check raw dicts for structured cost fields
            raw = l.get("raw") or {}
            for key in ("cost_usd", "total_cost", "cost"):
                if isinstance(raw, dict) and key in raw:
                    try:
                        val = float(raw[key])
                        cost_usd = max(cost_usd, val)
                    except Exception:
                        pass
            usage = raw.get("usage") if isinstance(raw, dict) else None
            if isinstance(usage, dict):
                for key in ("cost_usd", "total_cost", "cost"):
                    if key in usage:
                        try:
                            val = float(usage[key])
                            cost_usd = max(cost_usd, val)
                        except Exception:
                            pass

        data = {
            "agent_id": agent_id,
            "task_id": task_id,
            "logs": logs,
            "metrics": {
                **metrics,
                "memory_usage_mb": mem_usage,
                "cpu_usage_percent": cpu_usage,
                "cost_usd": cost_usd,
            },
            "progress": progress,
            "collected_at": self._now().isoformat(),
        }
        self.logger.info(json.dumps({"event": "collected_task", "agent_id": agent_id, "task_id": task_id}))
        return data

    def collect_all(self) -> List[Dict[str, Any]]:
        tasks = self.pg.get_all_tasks()
        results: List[Dict[str, Any]] = []
        for t in tasks:
            task_id = self._normalize_id(t.get("task_id") or t.get("id"))
            agent_id = self._normalize_id(t.get("agent_id"))
            if not task_id:
                continue
            try:
                results.append(self.collect_for_task(agent_id, task_id))
            except Exception as e:
                self.logger.error(json.dumps({"event": "collect_task_error", "task_id": task_id, "error": str(e)}))
        return results

    def collect_snapshots_for_task(self, agent_id: Optional[str], task_id: str) -> List[Dict[str, Any]]:
        """Build a series of data snapshots, one per progress update.

        For each progress row timestamp, gather Mongo logs up to that time and compute metrics.
        """
        agent_id = self._normalize_id(agent_id or self.default_agent_id)
        task_id = self._normalize_id(task_id)

        progress = self.pg.get_task_progress(task_id)
        if not progress:
            # Fallback to single snapshot
            return [self.collect_for_task(agent_id, task_id)]

        snapshots: List[Dict[str, Any]] = []
        for idx, row in enumerate(progress):
            ts = row.get("updated_at") or row.get("ts")
            # normalize ts string
            cutoff = None
            if isinstance(ts, str):
                try:
                    from datetime import datetime
                    cutoff = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    cutoff = None
            else:
                cutoff = ts

            logs = self.mongo.fetch_task_logs_until(agent_id, task_id, cutoff)
            metrics = self.mongo.compute_basic_metrics(logs)

            # Reuse resource extraction across logs
            mem_usage = 0.0
            cpu_usage = 0.0
            cost_usd = 0.0
            mem_re = re.compile(r"mem(ory)?[:=\s]+([0-9.]+)\s*mb", re.I)
            cpu_re = re.compile(r"cpu[:=\s]+([0-9.]+)\s*%", re.I)
            cost_re = re.compile(r"(total_)?(usd_)?cost\s*[:=\s$]+([0-9]+(?:\.[0-9]+)?)", re.I)
            for l in logs:
                msg = l.get("message") or ""
                m1 = mem_re.search(msg)
                if m1:
                    try:
                        mem_usage = max(mem_usage, float(m1.group(2)))
                    except Exception:
                        pass
                m2 = cpu_re.search(msg)
                if m2:
                    try:
                        cpu_usage = max(cpu_usage, float(m2.group(1)))
                    except Exception:
                        pass
                mc = cost_re.search(msg)
                if mc:
                    try:
                        cost_usd = max(cost_usd, float(mc.group(3)))
                    except Exception:
                        pass
                raw = l.get("raw") or {}
                for key in ("cost_usd", "total_cost", "cost"):
                    if isinstance(raw, dict) and key in raw:
                        try:
                            val = float(raw[key])
                            cost_usd = max(cost_usd, val)
                        except Exception:
                            pass
                usage = raw.get("usage") if isinstance(raw, dict) else None
                if isinstance(usage, dict):
                    for key in ("cost_usd", "total_cost", "cost"):
                        if key in usage:
                            try:
                                val = float(usage[key])
                                cost_usd = max(cost_usd, val)
                            except Exception:
                                pass

            data = {
                "agent_id": agent_id,
                "task_id": task_id,
                "logs": logs,
                "metrics": {
                    **metrics,
                    "memory_usage_mb": mem_usage,
                    "cpu_usage_percent": cpu_usage,
                    "cost_usd": cost_usd,
                },
                # include progress up to this point
                "progress": progress[: idx + 1],
                # align snapshot timestamp with progress timestamp for plotting
                "collected_at": (ts.isoformat() if hasattr(ts, "isoformat") else str(ts)) if ts else self._now().isoformat(),
            }
            snapshots.append(data)

        self.logger.info(json.dumps({"event": "collected_task_snapshots", "agent_id": agent_id, "task_id": task_id, "count": len(snapshots)}))
        return snapshots
