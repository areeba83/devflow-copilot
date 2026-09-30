"""
Shared pytest fixtures. Every test in this suite runs without Ollama —
the model call is monkeypatched, so `pytest` passes on any machine with
just the Python dependencies installed, even without Ollama running.
This matches SRS 22.1 (unit tests for validation/persistence/export) —
the AI evaluation harness in eval/ is a separate, model-dependent suite.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MOCK_SPEC_JSON = {
    "project_summary": "A mobile app for booking salon appointments with push reminders.",
    "features": [
        {"name": "Appointment booking", "description": "Customers can book with a stylist", "priority": "high"},
        {"name": "Push reminders", "description": "Send push notification reminders", "priority": "medium"},
    ],
    "user_stories": [
        {"role": "customer", "goal": "book an appointment with a stylist", "benefit": "I don't have to call the salon"}
    ],
    "assumptions": ["Assumed iOS and Android both needed since 'mobile app' was used generically"],
    "open_questions": ["Should customers be able to choose a specific stylist, or just a time slot?"],
}

MOCK_ACCEPTANCE_JSON = {
    "acceptance_criteria": [
        {"story_id": "US-001", "given": "a customer is on the booking screen",
         "when": "they select a time slot and confirm",
         "then": "the appointment is created and a confirmation is shown"}
    ]
}


@pytest.fixture
def mock_spec_raw() -> str:
    return json.dumps(MOCK_SPEC_JSON)


@pytest.fixture
def mock_acceptance_raw() -> str:
    return json.dumps(MOCK_ACCEPTANCE_JSON)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Points app.storage at a throwaway SQLite file for this test only."""
    from app import storage
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage.init_db()
    return storage


@pytest.fixture
def client(temp_db, monkeypatch):
    """A FastAPI TestClient with the LLM call mocked and pointed at temp_db."""
    from app import main as main_module

    def fake_generate_raw(prompt, model_name=None):
        if "<specification>" in prompt:
            return json.dumps(MOCK_ACCEPTANCE_JSON)
        return json.dumps(MOCK_SPEC_JSON)

    monkeypatch.setattr(main_module, "generate_raw", fake_generate_raw)

    from fastapi.testclient import TestClient
    with TestClient(main_module.app) as c:
        yield c
