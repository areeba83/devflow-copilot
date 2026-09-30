import json

from app.validator import build_result, extract_json, build_generic_result
from app.schemas import ProjectSpec, AcceptanceCriteriaDoc


def test_clean_json_is_ok(mock_spec_raw):
    r = build_result(mock_spec_raw, "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "ok"
    assert r.spec.project_summary


def test_markdown_fenced_json_is_extracted(mock_spec_raw):
    fenced = f"```json\n{mock_spec_raw}\n```"
    r = build_result(fenced, "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "ok"


def test_json_with_leading_prose_is_extracted(mock_spec_raw):
    wrapped = f"Sure, here is the specification:\n\n{mock_spec_raw}\n\nLet me know if you need changes."
    r = build_result(wrapped, "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "ok"


def test_malformed_json_returns_invalid_json_status():
    bad = "Sure, here is the spec: {project_summary: missing quotes around keys}"
    r = build_result(bad, "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "invalid_json"
    assert r.raw_model_output == bad


def test_wrong_enum_value_returns_schema_error():
    wrong = json.dumps({
        "project_summary": "x",
        "features": [{"name": "A", "description": "d", "priority": "urgent"}],
        "user_stories": [], "assumptions": [], "open_questions": [],
    })
    r = build_result(wrong, "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "schema_error"
    assert "urgent" in r.error_message or "priority" in r.error_message


def test_missing_required_field_returns_schema_error():
    incomplete = json.dumps({"features": [], "user_stories": [], "assumptions": [], "open_questions": []})
    r = build_result(incomplete, "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "schema_error"


def test_empty_string_returns_invalid_json():
    r = build_result("", "qwen2.5:7b", "spec_prompt_v1")
    assert r.status == "invalid_json"


def test_generic_result_works_for_non_spec_schema(mock_acceptance_raw):
    r = build_generic_result(mock_acceptance_raw, AcceptanceCriteriaDoc, "qwen2.5:7b",
                              "acceptance_criteria_prompt_v1", "acceptance_criteria")
    assert r.status == "ok"
    assert r.content["acceptance_criteria"][0]["story_id"] == "US-001"


def test_extract_json_raises_on_no_json_found():
    import pytest
    import json as jsonlib
    with pytest.raises(jsonlib.JSONDecodeError):
        extract_json("no json anywhere in this text")
