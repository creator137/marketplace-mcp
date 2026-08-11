from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    customer TEXT,
    budget_json TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    inspected INTEGER NOT NULL DEFAULT 0,
    relevance_score INTEGER,
    submitted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS project_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    viewed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposal_drafts (
    project_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submitted_proposals (
    project_id TEXT PRIMARY KEY,
    proposal_id TEXT,
    text TEXT NOT NULL,
    price INTEGER,
    delivery_days INTEGER,
    submitted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS avito_ad_drafts (
    draft_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT,
    price INTEGER,
    location TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS avito_published_ads (
    draft_id TEXT PRIMARY KEY,
    avito_item_id TEXT,
    url TEXT,
    payload_json TEXT NOT NULL,
    published_at TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con
