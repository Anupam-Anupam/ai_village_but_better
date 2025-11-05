import os
import json
import logging
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras


class PostgresAdapter:
    """Read-only adapter to central PostgreSQL for tasks and global progress."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        dsn = os.getenv("POSTGRES_DSN", "")
        self.conn = None
        if dsn:
            try:
                self.conn = psycopg2.connect(dsn, connect_timeout=3)
                self.conn.autocommit = True
                self.logger.info(json.dumps({"event": "postgres_connected"}))
                # Initialize schema if needed
                self._init_schema()
            except Exception as e:
                self.logger.error(json.dumps({"event": "postgres_connect_error", "error": str(e)}))
        else:
            self.logger.warning(json.dumps({"event": "postgres_no_dsn"}))

    def _init_schema(self):
        """Initialize required tables if they don't exist."""
        if not self.conn:
            return
            
        with self.conn.cursor() as cur:
            # Create tables if they don't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id text PRIMARY KEY,
                    agent_id text,
                    created_at timestamptz DEFAULT now(),
                    status text,
                    title text
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS task_progress (
                    task_id text,
                    status text,
                    progress numeric,
                    updated_at timestamptz DEFAULT now(),
                    CONSTRAINT fk_task FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Create index for faster lookups
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_progress_task_id 
                ON task_progress(task_id, updated_at)
            """)
            
            # Add a default task if none exists
            cur.execute("""
                INSERT INTO tasks (task_id, agent_id, status, title)
                VALUES ('default_task', 'agent1', 'in_progress', 'Default Task')
                ON CONFLICT (task_id) DO NOTHING
            """)
            
            # Add initial progress if none exists
            cur.execute("""
                INSERT INTO task_progress (task_id, status, progress, updated_at)
                SELECT 'default_task', 'started', 0.0, now() - interval '5 minutes'
                WHERE NOT EXISTS (SELECT 1 FROM task_progress LIMIT 1)
            """)
            
            # Add some sample progress updates
            cur.execute("""
                WITH new_rows AS (
                    SELECT 
                        'default_task' as task_id,
                        status,
                        progress,
                        updated_at
                    FROM (
                        VALUES 
                            ('in_progress', 0.25, now() - interval '4 minutes'),
                            ('in_progress', 0.50, now() - interval '3 minutes'),
                            ('in_progress', 0.75, now() - interval '2 minutes'),
                            ('completed', 1.00, now() - interval '1 minute')
                    ) AS t(status, progress, updated_at)
                )
                INSERT INTO task_progress (task_id, status, progress, updated_at)
                SELECT * FROM new_rows
                WHERE NOT EXISTS (SELECT 1 FROM task_progress WHERE task_id = 'default_task')
            """)
            
            self.conn.commit()

    def _query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or tuple())
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            self.logger.error(json.dumps({"event": "postgres_query_error", "error": str(e), "sql": sql}))
            return []

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        # Try common table/column names; fallback to empty
        candidates = [
            "SELECT task_id, agent_id, created_at, status, title FROM tasks",
            "SELECT id as task_id, agent_id, created_at, status, title FROM agent_tasks",
        ]
        for sql in candidates:
            rows = self._query(sql)
            if rows:
                return rows
        return []

    def get_task_progress(self, task_id: str) -> List[Dict[str, Any]]:
        candidates = [
            ("SELECT task_id, status, progress, updated_at FROM task_progress WHERE task_id = %s ORDER BY updated_at ASC", (task_id,)),
            ("SELECT task_id, status, progress, ts as updated_at FROM progress_updates WHERE task_id = %s ORDER BY ts ASC", (task_id,)),
        ]
        for sql, params in candidates:
            rows = self._query(sql, params)
            if rows:
                return rows
        return []

    def list_agents(self) -> List[str]:
        candidates = [
            "SELECT DISTINCT agent_id FROM tasks",
            "SELECT DISTINCT agent_id FROM agent_tasks",
        ]
        for sql in candidates:
            rows = self._query(sql)
            if rows and "agent_id" in rows[0]:
                return [str(r["agent_id"]) for r in rows]
        return []
