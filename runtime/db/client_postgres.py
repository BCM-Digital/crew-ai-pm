"""
Postgres database client for PM Agent work graph.

Provides a simple interface for task, node, edge, signal, and audit operations.
Can be swapped for DynamoDB later by implementing the same interface.
"""

import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager


class PostgresClient:
    """Database client with consistent interface for work graph operations."""

    def __init__(self, connection_string: str):
        """
        Initialise Postgres client.

        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = psycopg2.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def upsert_task(self, task: Dict[str, Any]) -> str:
        """
        Insert or update a task.

        Args:
            task: Task dictionary with required fields: id, source, project, title, description, priority, status

        Returns:
            Task ID
        """
        required_fields = ["id", "source", "project", "title", "description", "priority", "status"]
        for field in required_fields:
            if field not in task:
                raise ValueError(f"Missing required field: {field}")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into task (id, source, project, title, description, priority, status,
                                      assignee, due_at, next_action, artefacts, created_at, updated_at)
                    values (%(id)s, %(source)s, %(project)s, %(title)s, %(description)s, %(priority)s, %(status)s,
                            %(assignee)s, %(due_at)s, %(next_action)s, %(artefacts)s, now(), now())
                    on conflict (id) do update set
                        source = excluded.source,
                        project = excluded.project,
                        title = excluded.title,
                        description = excluded.description,
                        priority = excluded.priority,
                        status = excluded.status,
                        assignee = excluded.assignee,
                        due_at = excluded.due_at,
                        next_action = excluded.next_action,
                        artefacts = excluded.artefacts,
                        updated_at = now()
                    """,
                    {
                        "id": task["id"],
                        "source": task["source"],
                        "project": task["project"],
                        "title": task["title"][:100],  # Enforce max length
                        "description": task["description"],
                        "priority": task["priority"],
                        "status": task["status"],
                        "assignee": task.get("assignee"),
                        "due_at": task.get("due_at"),
                        "next_action": task.get("next_action"),
                        "artefacts": json.dumps(task.get("artefacts", [])),
                    },
                )
        return task["id"]

    def list_tasks(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filters.

        Args:
            project: Filter by project name
            status: Filter by status
            assignee: Filter by assignee
            limit: Maximum number of results

        Returns:
            List of task dictionaries
        """
        conditions = []
        params = {"limit": limit}

        if project:
            conditions.append("project = %(project)s")
            params["project"] = project

        if status:
            conditions.append("status = %(status)s")
            params["status"] = status

        if assignee:
            conditions.append("assignee = %(assignee)s")
            params["assignee"] = assignee

        where_clause = "where " + " and ".join(conditions) if conditions else ""

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    select id, source, project, title, description, priority, status,
                           assignee, due_at, next_action, artefacts, created_at, updated_at
                    from task
                    {where_clause}
                    order by updated_at desc
                    limit %(limit)s
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]

    def list_changed_since(self, project: str, since: datetime) -> List[Dict[str, Any]]:
        """
        List tasks changed since a given time for a project.

        Args:
            project: Project name
            since: Datetime threshold (timezone-aware)

        Returns:
            List of task dictionaries
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    select id, source, project, title, description, priority, status,
                           assignee, due_at, next_action, artefacts, created_at, updated_at
                    from task
                    where project = %s and updated_at > %s
                    order by updated_at desc
                    """,
                    (project, since),
                )
                return [dict(row) for row in cur.fetchall()]

    def insert_nodes_edges(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> None:
        """
        Insert nodes and edges into the work graph.

        Args:
            nodes: List of node dicts with id, type, label, meta
            edges: List of edge dicts with id, src_id, dst_id, kind
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Insert nodes
                for node in nodes:
                    cur.execute(
                        """
                        insert into node (id, type, label, meta, created_at)
                        values (%s, %s, %s, %s, now())
                        on conflict (id) do update set
                            type = excluded.type,
                            label = excluded.label,
                            meta = excluded.meta
                        """,
                        (
                            node["id"],
                            node["type"],
                            node["label"],
                            json.dumps(node.get("meta", {})),
                        ),
                    )

                # Insert edges
                for edge in edges:
                    cur.execute(
                        """
                        insert into edge (id, src_id, dst_id, kind, created_at)
                        values (%s, %s, %s, %s, now())
                        on conflict (id) do nothing
                        """,
                        (edge["id"], edge["src_id"], edge["dst_id"], edge["kind"]),
                    )

    def record_audit(self, audit: Dict[str, Any]) -> str:
        """
        Record an audit entry for a tool invocation.

        Args:
            audit: Audit dict with run_id, agent, tool, input_hash, ok, error_code, links

        Returns:
            Audit ID
        """
        required_fields = ["id", "run_id", "agent", "tool", "input_hash", "ok"]
        for field in required_fields:
            if field not in audit:
                raise ValueError(f"Missing required field: {field}")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into audit (id, run_id, agent, tool, input_hash, ok, error_code, at, links)
                    values (%s, %s, %s, %s, %s, %s, %s, now(), %s)
                    """,
                    (
                        audit["id"],
                        audit["run_id"],
                        audit["agent"],
                        audit["tool"],
                        audit["input_hash"],
                        audit["ok"],
                        audit.get("error_code"),
                        json.dumps(audit.get("links", [])),
                    ),
                )
        return audit["id"]

    def get_blocking_items(self, project: str) -> List[Dict[str, Any]]:
        """
        Get tasks blocking a project.

        Args:
            project: Project name

        Returns:
            List of blocked/waiting tasks
        """
        return self.list_tasks(project=project, status="blocked") + self.list_tasks(
            project=project, status="waiting"
        )

    def insert_signal(self, signal: Dict[str, Any]) -> str:
        """
        Insert a signal (incoming event).

        Args:
            signal: Signal dict with id, source, source_id, payload

        Returns:
            Signal ID
        """
        required_fields = ["id", "source", "source_id", "payload"]
        for field in required_fields:
            if field not in signal:
                raise ValueError(f"Missing required field: {field}")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into signal (id, source, source_id, payload, at)
                    values (%s, %s, %s, %s, now())
                    """,
                    (
                        signal["id"],
                        signal["source"],
                        signal["source_id"],
                        json.dumps(signal["payload"]),
                    ),
                )
        return signal["id"]
