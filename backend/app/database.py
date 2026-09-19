from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parents[1] / "data" / "app.db")))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                active_version_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id),
                file_path TEXT,
                source_filename TEXT NOT NULL,
                state TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                external_job_id TEXT,
                error_message TEXT,
                raw_response_json TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transcript_segments (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL REFERENCES jobs(id),
                ordinal INTEGER NOT NULL,
                text TEXT NOT NULL,
                speaker_id TEXT,
                start_seconds REAL,
                end_seconds REAL
            );
            CREATE TABLE IF NOT EXISTS document_versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id),
                version_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                source_job_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                document_id TEXT,
                job_id TEXT,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                audio_bytes INTEGER NOT NULL,
                duration_seconds REAL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS jobs_document_idx ON jobs(document_id);
            CREATE INDEX IF NOT EXISTS segments_job_idx ON transcript_segments(job_id, ordinal);
            CREATE INDEX IF NOT EXISTS audit_created_idx ON audit_events(created_at);
            """
        )


def create_document(document_id: str, title: str) -> None:
    timestamp = now()
    with connect() as connection:
        connection.execute(
            "INSERT INTO documents (id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (document_id, title, "processing", timestamp, timestamp),
        )


def create_job(job_id: str, document_id: str, source_filename: str, file_path: str, state: str) -> None:
    timestamp = now()
    with connect() as connection:
        connection.execute(
            "INSERT INTO jobs (id, document_id, source_filename, file_path, state, progress, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, document_id, source_filename, file_path, state, 15, timestamp, timestamp),
        )


def update_job(job_id: str, **values: Any) -> None:
    values["updated_at"] = now()
    assignments = ", ".join(f"{key} = ?" for key in values)
    with connect() as connection:
        connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", (*values.values(), job_id))


def get_job(job_id: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def get_pollable_jobs(limit: int = 20) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM jobs WHERE state IN ('submitted', 'running') AND external_job_id IS NOT NULL ORDER BY updated_at LIMIT ?",
            (limit,),
        ).fetchall()


def get_document(document_id: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()


def save_result(job_id: str, document_id: str, transcript: str, segments: list[dict[str, Any]], raw_response: Any) -> None:
    timestamp = now()
    with connect() as connection:
        existing = connection.execute("SELECT id FROM document_versions WHERE source_job_id = ?", (job_id,)).fetchone()
        if existing:
            return
        version_number = connection.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version FROM document_versions WHERE document_id = ?",
            (document_id,),
        ).fetchone()["next_version"]
        version_id = f"version-{job_id}"
        connection.execute(
            "INSERT INTO document_versions (id, document_id, version_number, content, source_job_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (version_id, document_id, version_number, transcript, job_id, timestamp),
        )
        connection.execute(
            "UPDATE documents SET active_version_id = ?, status = ?, updated_at = ? WHERE id = ?",
            (version_id, "ready", timestamp, document_id),
        )
        connection.execute("DELETE FROM transcript_segments WHERE job_id = ?", (job_id,))
        for ordinal, segment in enumerate(segments):
            connection.execute(
                "INSERT INTO transcript_segments (id, job_id, ordinal, text, speaker_id, start_seconds, end_seconds) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (segment["id"], job_id, ordinal, segment["text"], segment.get("speaker_id"), segment.get("start_seconds"), segment.get("end_seconds")),
            )
        update_values = {
            "state": "completed",
            "progress": 100,
            "raw_response_json": json.dumps(raw_response, ensure_ascii=False, default=str),
            "error_message": None,
        }
        assignments = ", ".join(f"{key} = ?" for key in update_values)
        connection.execute(f"UPDATE jobs SET {assignments}, updated_at = ? WHERE id = ?", (*update_values.values(), timestamp, job_id))


def save_edited_version(document_id: str, content: str) -> int:
    timestamp = now()
    with connect() as connection:
        next_version = connection.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version FROM document_versions WHERE document_id = ?",
            (document_id,),
        ).fetchone()["next_version"]
        version_id = f"edit-{document_id}-{next_version}"
        connection.execute(
            "INSERT INTO document_versions (id, document_id, version_number, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (version_id, document_id, next_version, content, timestamp),
        )
        connection.execute("UPDATE documents SET active_version_id = ?, updated_at = ? WHERE id = ?", (version_id, timestamp, document_id))
    return next_version


def get_document_content(document_id: str) -> str:
    with connect() as connection:
        row = connection.execute(
            "SELECT content FROM document_versions WHERE id = (SELECT active_version_id FROM documents WHERE id = ?)",
            (document_id,),
        ).fetchone()
        return row["content"] if row else ""


def get_versions(document_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, version_number, content, source_job_id, created_at FROM document_versions WHERE document_id = ? ORDER BY version_number DESC",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_segments(job_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, text, speaker_id, start_seconds, end_seconds FROM transcript_segments WHERE job_id = ? ORDER BY ordinal",
            (job_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def audit(event_type: str, document_id: str | None = None, job_id: str | None = None, **details: Any) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO audit_events (event_type, document_id, job_id, details_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_type, document_id, job_id, json.dumps(details, ensure_ascii=False, default=str), now()),
        )


def add_usage(job_id: str, audio_bytes: int, duration_seconds: float | None) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO usage_events (job_id, audio_bytes, duration_seconds, created_at) VALUES (?, ?, ?, ?)",
            (job_id, audio_bytes, duration_seconds, now()),
        )


def usage_summary() -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS uploads, COALESCE(SUM(audio_bytes), 0) AS audio_bytes, COALESCE(SUM(duration_seconds), 0) AS duration_seconds FROM usage_events"
        ).fetchone()
        jobs = connection.execute("SELECT state, COUNT(*) AS count FROM jobs GROUP BY state").fetchall()
    return {
        "uploads": row["uploads"],
        "audio_bytes": row["audio_bytes"],
        "duration_seconds": row["duration_seconds"],
        "jobs": {item["state"]: item["count"] for item in jobs},
    }


def get_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT event_type, document_id, job_id, details_json, created_at FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    events = []
    for row in rows:
        event = dict(row)
        event["details"] = json.loads(event.pop("details_json"))
        events.append(event)
    return events


def cleanup_uploads(max_age_hours: int = 24) -> int:
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 60 * 60)
    removed = 0
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, file_path FROM jobs WHERE file_path IS NOT NULL AND state IN ('completed', 'failed') AND created_at < datetime(?, 'unixepoch')",
            (cutoff,),
        ).fetchall()
        for row in rows:
            if row["file_path"] and Path(row["file_path"]).exists():
                Path(row["file_path"]).unlink(missing_ok=True)
                removed += 1
            connection.execute("UPDATE jobs SET file_path = NULL WHERE id = ?", (row["id"],))
    return removed
