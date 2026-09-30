"""
Single source of truth for every downstream (Day 3) artifact type. Adding a
new artifact type later means adding one entry here — main.py's generic
/artifacts/{type}/generate endpoint doesn't need to change.
"""

from dataclasses import dataclass
from typing import Callable, Type

from pydantic import BaseModel

from . import schemas
from .prompts import artifact_prompts as p


@dataclass(frozen=True)
class ArtifactTypeDef:
    schema_cls: Type[BaseModel]
    prompt_builder: Callable[[dict], str]
    prompt_version: str
    display_name: str


ARTIFACT_TYPES: dict[str, ArtifactTypeDef] = {
    "user_stories": ArtifactTypeDef(
        schemas.UserStoriesDoc, p.build_user_stories_prompt,
        p.PROMPT_VERSION_USER_STORIES_V1, "User Stories",
    ),
    "acceptance_criteria": ArtifactTypeDef(
        schemas.AcceptanceCriteriaDoc, p.build_acceptance_criteria_prompt,
        p.PROMPT_VERSION_ACCEPTANCE_CRITERIA_V1, "Acceptance Criteria",
    ),
    "implementation_plan": ArtifactTypeDef(
        schemas.ImplementationPlanDoc, p.build_implementation_plan_prompt,
        p.PROMPT_VERSION_IMPLEMENTATION_PLAN_V1, "Implementation Plan",
    ),
    "test_cases": ArtifactTypeDef(
        schemas.TestCasesDoc, p.build_test_cases_prompt,
        p.PROMPT_VERSION_TEST_CASES_V1, "QA Test Cases",
    ),
    "developer_prompt": ArtifactTypeDef(
        schemas.DeveloperPromptDoc, p.build_developer_prompt_prompt,
        p.PROMPT_VERSION_DEVELOPER_PROMPT_V1, "Developer Prompt",
    ),
    "client_update": ArtifactTypeDef(
        schemas.ClientUpdateDoc, p.build_client_update_prompt,
        p.PROMPT_VERSION_CLIENT_UPDATE_V1, "Client Update",
    ),
    "release_notes": ArtifactTypeDef(
        schemas.ReleaseNotesDoc, p.build_release_notes_prompt,
        p.PROMPT_VERSION_RELEASE_NOTES_V1, "Release Notes",
    ),
}
