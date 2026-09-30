from pydantic import ValidationError
import pytest

from app.schemas import ProjectSpec, Feature, UserStory


def test_valid_spec_parses(mock_spec_raw):
    import json
    spec = ProjectSpec(**json.loads(mock_spec_raw))
    assert spec.project_summary
    assert len(spec.features) == 2
    assert spec.features[0].priority in {"high", "medium", "low"}


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        ProjectSpec(features=[], user_stories=[], assumptions=[], open_questions=[])
        # project_summary omitted entirely


def test_invalid_priority_enum_rejected():
    with pytest.raises(ValidationError):
        Feature(name="X", description="Y", priority="urgent")  # not high/medium/low


def test_empty_arrays_are_valid():
    """A spec with nothing extractable should still validate — empty lists
    are a legitimate failure-behavior response, not a schema violation."""
    spec = ProjectSpec(
        project_summary="No meaningful content could be extracted from this input.",
        features=[], user_stories=[], assumptions=[],
        open_questions=["Please provide more detail about the project."],
    )
    assert spec.features == []


def test_user_story_requires_all_three_fields():
    with pytest.raises(ValidationError):
        UserStory(role="customer", goal="book an appointment")  # missing benefit
