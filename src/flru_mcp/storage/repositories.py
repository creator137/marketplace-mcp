from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from flru_mcp.flru.models import ProjectDetail, ProjectSummary


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HistoryRepository:
    def __init__(self, con: sqlite3.Connection):
        self.con = con

    def upsert_project(self, project: ProjectSummary | ProjectDetail, relevance_score: int | None = None) -> None:
        now = now_iso()
        self.con.execute(
            """
            INSERT INTO projects(project_id, url, title, customer, budget_json, first_seen_at, last_seen_at, relevance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                customer=excluded.customer,
                budget_json=excluded.budget_json,
                last_seen_at=excluded.last_seen_at,
                relevance_score=COALESCE(excluded.relevance_score, projects.relevance_score)
            """,
            (
                project.id,
                project.url,
                project.title,
                project.customer.name,
                project.budget.model_dump_json(),
                now,
                now,
                relevance_score,
            ),
        )
        self.con.execute(
            "INSERT INTO project_snapshots(project_id, captured_at, payload_json) VALUES (?, ?, ?)",
            (project.id, now, project.model_dump_json()),
        )
        self.con.commit()

    def mark_seen(self, project_id: str) -> None:
        now = now_iso()
        self.con.execute("UPDATE projects SET inspected=1 WHERE project_id=?", (project_id,))
        self.con.execute("INSERT INTO project_views(project_id, viewed_at) VALUES (?, ?)", (project_id, now))
        self.con.commit()

    def unseen_projects(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.con.execute(
            "SELECT * FROM projects WHERE inspected=0 ORDER BY first_seen_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def is_inspected(self, project_id: str) -> bool:
        row = self.con.execute("SELECT inspected FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return bool(row and row["inspected"])

    def history(self, project_id: str) -> dict[str, Any]:
        project = self.con.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        snapshots = self.con.execute("SELECT * FROM project_snapshots WHERE project_id=? ORDER BY captured_at DESC", (project_id,)).fetchall()
        views = self.con.execute("SELECT * FROM project_views WHERE project_id=? ORDER BY viewed_at DESC", (project_id,)).fetchall()
        draft = self.con.execute("SELECT * FROM proposal_drafts WHERE project_id=?", (project_id,)).fetchone()
        submitted = self.con.execute("SELECT * FROM submitted_proposals WHERE project_id=?", (project_id,)).fetchone()
        return {
            "project": dict(project) if project else None,
            "snapshots": [dict(row) for row in snapshots],
            "views": [dict(row) for row in views],
            "draft": dict(draft) if draft else None,
            "submitted_proposal": dict(submitted) if submitted else None,
        }

    def save_draft(self, project_id: str, text: str) -> None:
        self.con.execute(
            """
            INSERT INTO proposal_drafts(project_id, text, saved_at) VALUES (?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET text=excluded.text, saved_at=excluded.saved_at
            """,
            (project_id, text, now_iso()),
        )
        self.con.commit()

    def get_draft(self, project_id: str) -> dict[str, Any] | None:
        row = self.con.execute("SELECT * FROM proposal_drafts WHERE project_id=?", (project_id,)).fetchone()
        return dict(row) if row else None

    def has_submitted(self, project_id: str) -> bool:
        row = self.con.execute("SELECT 1 FROM submitted_proposals WHERE project_id=?", (project_id,)).fetchone()
        return bool(row)

    def record_submission(self, project_id: str, text: str, proposal_id: str | None, price: int | None, delivery_days: int | None) -> None:
        now = now_iso()
        self.con.execute(
            "INSERT INTO submitted_proposals(project_id, proposal_id, text, price, delivery_days, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, proposal_id, text, price, delivery_days, now),
        )
        self.con.execute("UPDATE projects SET submitted=1 WHERE project_id=?", (project_id,))
        self.con.commit()

    def save_avito_draft(self, payload: dict[str, Any], draft_id: str | None = None) -> dict[str, Any]:
        now = now_iso()
        resolved_id = draft_id or f"avito-{uuid.uuid4().hex[:12]}"
        self.con.execute(
            """
            INSERT INTO avito_ad_drafts(draft_id, title, category, price, location, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(draft_id) DO UPDATE SET
                title=excluded.title,
                category=excluded.category,
                price=excluded.price,
                location=excluded.location,
                payload_json=excluded.payload_json,
                updated_at=excluded.updated_at
            """,
            (
                resolved_id,
                payload.get("title") or "",
                payload.get("category"),
                payload.get("price"),
                payload.get("location"),
                json.dumps(payload, ensure_ascii=False),
                now,
                now,
            ),
        )
        self.con.commit()
        return self.get_avito_draft(resolved_id) or {"draft_id": resolved_id}

    def get_avito_draft(self, draft_id: str) -> dict[str, Any] | None:
        row = self.con.execute("SELECT * FROM avito_ad_drafts WHERE draft_id=?", (draft_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["payload"] = json.loads(data.pop("payload_json"))
        return data

    def list_avito_drafts(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.con.execute("SELECT * FROM avito_ad_drafts ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        drafts = []
        for row in rows:
            data = dict(row)
            data["payload"] = json.loads(data.pop("payload_json"))
            drafts.append(data)
        return drafts

    def record_avito_publication(self, draft_id: str, payload: dict[str, Any], avito_item_id: str | None, url: str | None) -> None:
        self.con.execute(
            """
            INSERT INTO avito_published_ads(draft_id, avito_item_id, url, payload_json, published_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(draft_id) DO UPDATE SET
                avito_item_id=excluded.avito_item_id,
                url=excluded.url,
                payload_json=excluded.payload_json,
                published_at=excluded.published_at
            """,
            (draft_id, avito_item_id, url, json.dumps(payload, ensure_ascii=False), now_iso()),
        )
        self.con.commit()

    def has_published_avito_draft(self, draft_id: str) -> bool:
        row = self.con.execute("SELECT 1 FROM avito_published_ads WHERE draft_id=?", (draft_id,)).fetchone()
        return bool(row)
