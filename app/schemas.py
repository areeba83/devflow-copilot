"""
Day 1 canonical schema — a reduced slice of the full SRS "Canonical Artifact
Schema" (Section 10). Day 1 only needs: project_summary, features,
user_stories, assumptions, open_questions. Later days extend this with
acceptance_criteria, implementation_plan, test_cases, developer_prompt,
evidence_notes — don't add those fields yet, keep Day 1 scoped.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError


class Feature(BaseModel):
    name: str
    description: str
    priority: Literal["high", "medium", "low"]


class UserStory(BaseModel):
    role: str
    goal: str
    benefit: str


class ProjectSpec(BaseModel):
    """The structured output the model must produce for a single
    requirement text (GEN-002: structured JSON for machine-validated
    artifact types)."""

    project_summary: str
    features: List[Feature] = Field(default_factory=list)
    user_stories: List[UserStory] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """What the API returns for one generation call — spec plus the audit
    fields GEN-006/GEN-007 require (prompt version, model name, timestamp)."""

    status: Literal["ok", "invalid_json", "schema_error", "model_error"]
    spec: Optional[ProjectSpec] = None
    raw_model_output: Optional[str] = None
    error_message: Optional[str] = None
    model_name: str
    prompt_version: str
    generated_at: str


def validate_spec(raw_json: dict) -> ProjectSpec:
    """Raises pydantic.ValidationError on schema mismatch — caller is
    responsible for catching it and building a schema_error GenerationResult
    (see validator.py). Never silently coerces or drops fields."""
    return ProjectSpec(**raw_json)


# ---------------------------------------------------------------------------
# Day 3 — downstream artifact schemas. Each generated document from this
# point on is derived from an already-generated ProjectSpec (not the raw
# requirement text again), so every prompt in artifact_prompts.py takes the
# spec JSON as its source context.
# ---------------------------------------------------------------------------


class AcceptanceCriterion(BaseModel):
    story_id: str
    given: str
    when: str
    then: str


class AcceptanceCriteriaDoc(BaseModel):
    acceptance_criteria: List[AcceptanceCriterion] = Field(default_factory=list)


class ImplementationPlan(BaseModel):
    frontend: List[str] = Field(default_factory=list)
    backend: List[str] = Field(default_factory=list)
    data: List[str] = Field(default_factory=list)
    apis: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class ImplementationPlanDoc(BaseModel):
    implementation_plan: ImplementationPlan


class TestCase(BaseModel):
    test_id: str
    title: str
    preconditions: Optional[str] = None
    steps: List[str] = Field(default_factory=list)
    expected_result: str
    related_story_id: Optional[str] = None


class TestCasesDoc(BaseModel):
    test_cases: List[TestCase] = Field(default_factory=list)


class DeveloperPromptDoc(BaseModel):
    target_feature: Optional[str] = None
    developer_prompt: str


class ClientUpdate(BaseModel):
    summary: str
    progress_highlights: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    open_items_for_client: List[str] = Field(default_factory=list)


class ClientUpdateDoc(BaseModel):
    client_update: ClientUpdate


class ReleaseNotesBody(BaseModel):
    version: str
    date: str
    summary: str
    added: List[str] = Field(default_factory=list)
    changed: List[str] = Field(default_factory=list)
    fixed: List[str] = Field(default_factory=list)
    known_issues: List[str] = Field(default_factory=list)


class ReleaseNotesDoc(BaseModel):
    release_notes: ReleaseNotesBody


class UserStoriesDoc(BaseModel):
    """Standalone, more refined user-stories artifact — distinct from the
    inline user_stories already inside ProjectSpec. Generated from the spec
    as a dedicated pass so stories can be expanded/refined without
    regenerating the whole spec."""
    user_stories: List[UserStory] = Field(default_factory=list)
