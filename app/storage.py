"""
SQLite persistence — the full SRS ERD (Section 14): Project, InputDocument,
GenerationRun, Artifact, EvaluationTest, ReviewFeedback.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "devflow.db"
DB_PATH.parent.mkdir(exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS input_document (
    input_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    input_type TEXT NOT NULL,          -- 'text' | 'image' | 'combined'
    source_text TEXT,
    file_path TEXT,                    -- set for 'image'/'combined'
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE IF NOT EXISTS generation_run (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    input_id INTEGER,                  -- nullable: Day 3 artifacts derive
                                        -- from a spec artifact, not a fresh input
    source_artifact_id INTEGER,        -- set when this run derives from a
                                        -- prior artifact (Day 3 downstream gen)
    artifact_type TEXT NOT NULL DEFAULT 'project_spec',
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES project(project_id),
    FOREIGN KEY (input_id) REFERENCES input_document(input_id)
);

CREATE TABLE IF NOT EXISTS artifact (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    content_json TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'draft',  -- draft|approved|edited|rejected
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES generation_run(run_id),
    FOREIGN KEY (project_id) REFERENCES project(project_id)
);

CREATE TABLE IF NOT EXISTS review_feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL,
    reviewer_note TEXT,
    label TEXT NOT NULL,               -- approve|edit|reject|regenerate
    created_at TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifact(artifact_id)
);

CREATE TABLE IF NOT EXISTS evaluation_test (
    test_id TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    category TEXT,
    expected_fields TEXT,              -- JSON-encoded list, informational
    status TEXT,                       -- structure_validity result of last run
    score_json TEXT,                   -- JSON-encoded manual 0-5 metric scores
    notes TEXT,
    run_at TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

def create_project(name: str, description: str, created_at: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO project (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, created_at),
        )
        return cur.lastrowid


def list_projects():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM project ORDER BY created_at DESC")]


# ---------------------------------------------------------------------------
# Input documents (Day 1 text, Day 2 image/combined)
# ---------------------------------------------------------------------------

def save_input_document(project_id: int, input_type: str, source_text: str,
                         created_at: str, file_path: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO input_document (project_id, input_type, source_text, file_path, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, input_type, source_text, file_path, created_at),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Generation runs
# ---------------------------------------------------------------------------

def save_generation_run(project_id: int, model_name: str, prompt_version: str,
                         status: str, created_at: str, artifact_type: str = "project_spec",
                         input_id: int = None, source_artifact_id: int = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO generation_run
               (project_id, input_id, source_artifact_id, artifact_type,
                model_name, prompt_version, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, input_id, source_artifact_id, artifact_type,
             model_name, prompt_version, status, created_at),
        )
        return cur.lastrowid


def get_runs_for_project(project_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM generation_run WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )]


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

def save_artifact(run_id: int, project_id: int, artifact_type: str,
                   content: dict, created_at: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO artifact (run_id, project_id, type, content_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, project_id, artifact_type, json.dumps(content), created_at),
        )
        return cur.lastrowid


def get_artifact(artifact_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM artifact WHERE artifact_id = ?", (artifact_id,)).fetchone()
        return dict(row) if row else None


def list_artifacts_for_project(project_id: int, artifact_type: str = None):
    with get_conn() as conn:
        if artifact_type:
            rows = conn.execute(
                "SELECT * FROM artifact WHERE project_id = ? AND type = ? ORDER BY created_at DESC",
                (project_id, artifact_type),
            )
        else:
            rows = conn.execute(
                "SELECT * FROM artifact WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
        return [dict(r) for r in rows]


def get_latest_artifact(project_id: int, artifact_type: str):
    """Used by Day 3 generation to find 'the current spec' to build from,
    preferring an approved/edited one over a plain draft if both exist."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM artifact
               WHERE project_id = ? AND type = ?
               ORDER BY (review_status IN ('approved','edited')) DESC, created_at DESC
               LIMIT 1""",
            (project_id, artifact_type),
        ).fetchone()
        return dict(row) if row else None


def update_artifact_content(artifact_id: int, content: dict, review_status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE artifact SET content_json = ?, review_status = ? WHERE artifact_id = ?",
            (json.dumps(content), review_status, artifact_id),
        )


def update_artifact_status(artifact_id: int, review_status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE artifact SET review_status = ? WHERE artifact_id = ?",
            (review_status, artifact_id),
        )


# ---------------------------------------------------------------------------
# Review feedback (Day 5)
# ---------------------------------------------------------------------------

def save_review_feedback(artifact_id: int, label: str, reviewer_note: str, created_at: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO review_feedback (artifact_id, label, reviewer_note, created_at) VALUES (?, ?, ?, ?)",
            (artifact_id, label, reviewer_note, created_at),
        )
        return cur.lastrowid


def get_feedback_for_artifact(artifact_id: int):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM review_feedback WHERE artifact_id = ? ORDER BY created_at DESC",
            (artifact_id,),
        )]


# ---------------------------------------------------------------------------
# Evaluation tests (Day 4)
# ---------------------------------------------------------------------------

def upsert_evaluation_result(test_id: str, scenario: str, category: str,
                              expected_fields: list, status: str, run_at: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO evaluation_test (test_id, scenario, category, expected_fields, status, run_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(test_id) DO UPDATE SET
                 scenario=excluded.scenario, category=excluded.category,
                 expected_fields=excluded.expected_fields, status=excluded.status,
                 run_at=excluded.run_at""",
            (test_id, scenario, category, json.dumps(expected_fields), status, run_at),
        )


def save_evaluation_scores(test_id: str, score_json: dict, notes: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE evaluation_test SET score_json = ?, notes = ? WHERE test_id = ?",
            (json.dumps(score_json), notes, test_id),
        )


def list_evaluation_results():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM evaluation_test ORDER BY test_id")]
