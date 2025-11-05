import os
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class MongoAdapter:
    """Read-only adapter to multiple agent MongoDBs.

    Expects env MONGO_URIS as comma-separated MongoDB URIs.
    Each Mongo contains collections for execution logs and progress logs.
    This adapter avoids schema assumptions and attempts best-effort field resolution.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        uris = os.getenv("MONGO_URIS", "").strip()
        self.clients: List[Tuple[str, MongoClient]] = []
        if uris:
            for uri in [u.strip() for u in uris.split(",") if u.strip()]:
                try:
                    client = MongoClient(uri, serverSelectionTimeoutMS=3000, uuidRepresentation="standard", connectTimeoutMS=3000)
                    # touch server to validate
                    client.admin.command("ping")
                    self.clients.append((uri, client))
                    self.logger.info(json.dumps({"event": "mongo_connected", "uri": uri}))
                except Exception as e:
                    self.logger.error(json.dumps({"event": "mongo_connect_error", "uri": uri, "error": str(e)}))
        else:
            self.logger.warning(json.dumps({"event": "mongo_no_uris"}))

        # heuristics for field names across different agent schemas
        self.timestamp_fields = ["timestamp", "ts", "time", "created_at", "_ts"]
        self.agent_id_fields = ["agent_id", "agent", "agentId"]
        self.task_id_fields = ["task_id", "task", "taskId"]
        self.level_fields = ["level", "lvl", "severity"]
        self.message_fields = ["message", "msg", "text"]
        self.error_keywords = ["error", "exception", "traceback", "failed", "timeout"]
        self.retry_keywords = ["retry", "re-try", "attempt", "backoff"]
        self.dependency_patterns = [
            re.compile(r"request(ed)?\s+(human|user)", re.I),
            re.compile(r"ask(ing)?\s+(human|user)", re.I),
            re.compile(r"request(ed)?\s+agent", re.I),
            re.compile(r"handoff\s+to\s+agent", re.I),
        ]

    def _extract_first(self, doc: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        for k in keys:
            if k in doc:
                return doc[k]
        return default

    def _parse_ts(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            # common iso string
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def list_dbs(self) -> List[str]:
        names: List[str] = []
        for uri, client in self.clients:
            try:
                names.extend([f"{uri}|{n}" for n in client.list_database_names() if n not in ("admin", "local", "config")])
            except PyMongoError as e:
                self.logger.error(json.dumps({"event": "mongo_list_dbs_error", "uri": uri, "error": str(e)}))
        return names

    def _candidate_collections(self, db) -> List[str]:
        names = []
        try:
            for n in db.list_collection_names():
                ln = n.lower()
                if any(x in ln for x in ["log", "progress", "execution", "events"]):
                    names.append(n)
        except PyMongoError as e:
            self.logger.error(json.dumps({"event": "mongo_list_cols_error", "db": db.name, "error": str(e)}))
        return names

    def iter_logs(self, since: Optional[datetime] = None) -> Generator[Dict[str, Any], None, None]:
        """Yield normalized log entries across all MongoDBs since a timestamp.
        Output fields: timestamp, agent_id, task_id, level, message, raw
        """
        for uri, client in self.clients:
            try:
                for db_name in client.list_database_names():
                    if db_name in ("admin", "local", "config"):
                        continue
                    db = client[db_name]
                    for col_name in self._candidate_collections(db):
                        col = db[col_name]
                        query = {}
                        if since:
                            # try common fields
                            ors = [{f: {"$gte": since}} for f in self.timestamp_fields]
                            query = {"$or": ors}
                        try:
                            for doc in col.find(query, no_cursor_timeout=True):
                                ts = None
                                for f in self.timestamp_fields:
                                    ts = self._parse_ts(doc.get(f))
                                    if ts:
                                        break
                                if since and ts and ts < since:
                                    continue
                                agent_id = self._extract_first(doc, self.agent_id_fields, None)
                                task_id = self._extract_first(doc, self.task_id_fields, None)
                                level = (self._extract_first(doc, self.level_fields, "INFO") or "INFO").upper()
                                message = str(self._extract_first(doc, self.message_fields, ""))
                                yield {
                                    "timestamp": ts or datetime.now(timezone.utc),
                                    "agent_id": str(agent_id) if agent_id is not None else None,
                                    "task_id": str(task_id) if task_id is not None else None,
                                    "level": level,
                                    "message": message,
                                    "raw": doc,
                                    "source": f"{uri}/{db_name}.{col_name}",
                                }
                        except PyMongoError as e:
                            self.logger.error(json.dumps({"event": "mongo_iter_error", "collection": f"{db_name}.{col_name}", "error": str(e)}))
            except PyMongoError as e:
                self.logger.error(json.dumps({"event": "mongo_db_iter_error", "uri": uri, "error": str(e)}))

    def compute_basic_metrics(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        error_count = 0
        retry_count = 0
        dependency_count = 0
        total_api_calls = 0
        first_ts: Optional[datetime] = None
        last_ts: Optional[datetime] = None

        for log in logs:
            msg = (log.get("message") or "").lower()
            level = (log.get("level") or "").lower()
            ts = log.get("timestamp")
            if ts:
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts

            if any(k in msg for k in self.error_keywords) or level in ("error", "fatal"):
                error_count += 1
            if any(k in msg for k in self.retry_keywords):
                retry_count += 1
            if any(p.search(msg) for p in self.dependency_patterns):
                dependency_count += 1
            if "api call" in msg or "http" in msg:
                total_api_calls += 1

        completion_time_s = 0.0
        if first_ts and last_ts:
            completion_time_s = max(0.0, (last_ts - first_ts).total_seconds())

        return {
            "completion_time_s": completion_time_s,
            "error_count": error_count,
            "retry_count": retry_count,
            "human_or_agent_requests": dependency_count,
            "total_api_calls": total_api_calls,
        }

    def fetch_task_logs(self, agent_id: str, task_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for entry in self.iter_logs(since=since):
            if (agent_id is None or entry.get("agent_id") == str(agent_id)) and (task_id is None or entry.get("task_id") == str(task_id)):
                results.append(entry)
        return results

    def fetch_task_logs_until(self, agent_id: str, task_id: str, until: Optional[datetime]) -> List[Dict[str, Any]]:
        """Fetch logs for a task up to and including 'until' timestamp."""
        if until is None:
            return self.fetch_task_logs(agent_id, task_id)
        results: List[Dict[str, Any]] = []
        for entry in self.iter_logs(since=None):
            if (agent_id is None or entry.get("agent_id") == str(agent_id)) and (task_id is None or entry.get("task_id") == str(task_id)):
                ts = entry.get("timestamp")
                if ts is None or ts <= until:
                    results.append(entry)
        return results
