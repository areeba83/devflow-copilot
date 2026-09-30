import json

from app.exporters import to_json, to_markdown


def test_to_json_roundtrips():
    content = {"a": 1, "b": [1, 2, 3]}
    out = to_json(content)
    assert json.loads(out) == content


def test_project_spec_markdown_contains_key_sections():
    content = {
        "project_summary": "Test summary.",
        "features": [{"name": "Login", "description": "Users can log in", "priority": "high"}],
        "user_stories": [{"role": "user", "goal": "log in", "benefit": "I can access my account"}],
        "assumptions": ["Assumed email/password auth"],
        "open_questions": ["Is SSO required?"],
    }
    md = to_markdown("project_spec", content)
    assert "Test summary." in md
    assert "Login" in md
    assert "Is SSO required?" in md


def test_unknown_artifact_type_falls_back_to_generic():
    md = to_markdown("some_future_type_not_yet_registered", {"foo": "bar"})
    assert "foo" in md
    assert "bar" in md


def test_test_cases_markdown_numbers_steps():
    content = {"test_cases": [{
        "test_id": "TC-001", "title": "Login succeeds", "preconditions": None,
        "steps": ["Open app", "Enter credentials", "Tap login"],
        "expected_result": "User reaches home screen", "related_story_id": "US-001",
    }]}
    md = to_markdown("test_cases", content)
    assert "1. Open app" in md
    assert "TC-001" in md
