import os
import json
import uuid
from typing import Any, Dict, List, Optional


class HistoryStore:
    """Filesystem-backed JSONL history store.

    Each report is appended as a JSON line under {root}/reports.jsonl
    and also per-task file {root}/tasks/{task_id}.jsonl for quick retrieval.
    """

    def __init__(self, root: str, logger) -> None:
        self.root = root
        self.logger = logger
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        os.makedirs(self.root, exist_ok=True)
        os.makedirs(os.path.join(self.root, "tasks"), exist_ok=True)

    def append(self, report: Dict[str, Any]) -> None:
        # Append to global file
        global_path = os.path.join(self.root, "reports.jsonl")
        with open(global_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(report) + "\n")
        # Append to per-task
        task_id = str(report.get("task_id", "unknown"))
        task_path = os.path.join(self.root, "tasks", f"{task_id}.jsonl")
        with open(task_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(report) + "\n")

    def load_all(self) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []
        path = os.path.join(self.root, "reports.jsonl")
        if not os.path.exists(path):
            return reports
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        reports.append(json.loads(line))
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(json.dumps({"event": "history_read_error", "error": str(e)}))
        return reports

    def load_task(self, task_id: str) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []
        path = os.path.join(self.root, "tasks", f"{task_id}.jsonl")
        if not os.path.exists(path):
            return reports
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        reports.append(json.loads(line))
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(json.dumps({"event": "history_task_read_error", "task_id": task_id, "error": str(e)}))
        return reports
