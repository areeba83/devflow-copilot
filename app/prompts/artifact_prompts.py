"""
Day 3 — one prompt builder per downstream artifact type. Every one of these
takes the already-generated ProjectSpec (as JSON) as its source context —
never the raw requirement text again — so a developer prompt, test case, or
release note is always traceable back to a reviewed specification, not a
fresh reinterpretation of the client's original message.

Each follows the same eight-part structure as spec_prompt_v1 (system role,
objective, source context, rules, output schema, quality checklist, failure
behavior, version) — see SRS Section 16.
"""

import json

_SHARED_RULES = """RULES
- Use only the specification JSON below as source context. Do not invent
  features, technologies, or requirements that aren't in it.
- If the specification doesn't give you enough to produce a concrete item
  (e.g. a feature with no clear acceptance boundary), still produce your
  best concrete attempt AND note the gap as its own open-ended item where
  the schema allows, rather than skipping it silently.
- Do not include any artifact type other than the one requested."""

_FAILURE_BEHAVIOR = """FAILURE BEHAVIOR
If the specification has too little information to produce this artifact
meaningfully (e.g. empty features list), still return valid JSON matching
the schema, with an empty list where appropriate — never fabricate content
to avoid an empty result."""


def _spec_context(spec: dict) -> str:
    return f"<specification>\n{json.dumps(spec, indent=2)}\n</specification>"


PROMPT_VERSION_ACCEPTANCE_CRITERIA_V1 = "acceptance_criteria_prompt_v1"


def build_acceptance_criteria_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a QA-focused requirements analyst for a software house.

OBJECTIVE
Produce Given/When/Then acceptance criteria for the user stories in the
specification below. Every story that has a clear goal should get at least
one acceptance criterion; stories that are too vague to test should be
skipped, not guessed at.

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- Reference stories by a story_id you assign yourself in the form "US-001",
  "US-002", ... in the same order they appear in the specification's
  user_stories list.
- Given/When/Then must be concrete and testable — not vague restatements
  of the story.

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "acceptance_criteria": [
    {{"story_id": "US-001", "given": "string", "when": "string", "then": "string"}}
  ]
}}

QUALITY CHECKLIST
- Every story_id corresponds to a real story in the source context.
- Given/When/Then are independently understandable without re-reading the story.
- No criterion asserts something not implied by the story or a listed feature.

{_FAILURE_BEHAVIOR}
"""


PROMPT_VERSION_IMPLEMENTATION_PLAN_V1 = "implementation_plan_prompt_v1"


def build_implementation_plan_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a technical lead scoping implementation work for a software house.

OBJECTIVE
Break the specification below into a lightweight implementation plan:
concrete frontend tasks, backend tasks, data/storage tasks, external APIs
needed, and technical risks.

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- Do not name a specific technology stack, library, or framework unless the
  specification explicitly mentions one — describe tasks in
  technology-neutral terms instead (e.g. "build the booking list view", not
  "build a React component").
- "risks" means technical/delivery risk (e.g. "no clear source of truth for
  X"), not business risk.

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "implementation_plan": {{
    "frontend": ["string"],
    "backend": ["string"],
    "data": ["string"],
    "apis": ["string"],
    "risks": ["string"]
  }}
}}

QUALITY CHECKLIST
- Every task traces to a feature or story in the source context.
- No named technology unless the spec named it first.
- At least one risk is listed if the spec has any open_questions or
  assumptions (an unresolved question is itself a delivery risk).

{_FAILURE_BEHAVIOR}
"""


PROMPT_VERSION_TEST_CASES_V1 = "test_cases_prompt_v1"


def build_test_cases_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a QA engineer writing test cases for a software house.

OBJECTIVE
Write concrete test cases covering the features and user stories in the
specification below, including at least one negative/edge case per major
feature where the specification gives you enough to imagine one.

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- Assign test_id values as "TC-001", "TC-002", ... in order.
- "steps" must be concrete actions a tester could actually follow.
- Link each test case to a story via related_story_id when it clearly
  corresponds to one (using the same "US-00N" numbering a
  acceptance-criteria pass would use, in feature/story order); otherwise
  leave it null.

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "test_cases": [
    {{"test_id": "TC-001", "title": "string", "preconditions": "string or null",
      "steps": ["string"], "expected_result": "string", "related_story_id": "string or null"}}
  ]
}}

QUALITY CHECKLIST
- Every test case traces to a feature or story in the source context.
- Steps are concrete, not vague ("test the booking flow").
- At least one negative/edge case exists if the spec has enough detail to
  support one.

{_FAILURE_BEHAVIOR}
"""


PROMPT_VERSION_DEVELOPER_PROMPT_V1 = "developer_prompt_prompt_v1"


def build_developer_prompt_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a technical lead writing a implementation brief for a developer who
has not seen the original client conversation.

OBJECTIVE
Write one clear, self-contained developer prompt (plain text, not JSON
inside the field) that a developer or a code-generation tool could use to
start implementing the highest-priority feature in the specification below.

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- Pick the single highest-priority feature (or the first "high" priority
  feature if several tie) as target_feature.
- The developer_prompt text should include: what to build, relevant user
  stories, constraints/assumptions the developer should know about, and
  what's explicitly out of scope for this pass.
- Do not invent a tech stack, file structure, or specific library unless
  the specification mentions one.

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "target_feature": "string",
  "developer_prompt": "string"
}}

QUALITY CHECKLIST
- A developer with no other context could start working from this text alone.
- Every constraint mentioned traces back to the specification's assumptions
  or open_questions.

{_FAILURE_BEHAVIOR}
"""


PROMPT_VERSION_CLIENT_UPDATE_V1 = "client_update_prompt_v1"


def build_client_update_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a delivery lead writing a short, non-technical status update for a
client.

OBJECTIVE
Summarize the specification below in client-friendly language: what's
planned, what's confirmed vs. still being clarified, and what (if anything)
is needed from the client next.

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- No technical jargon — write for a non-technical business reader.
- Every open_question in the specification that needs client input belongs
  in open_items_for_client, phrased as a plain question.
- Do not promise a delivery date, price, or guarantee that isn't in the
  specification.

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "client_update": {{
    "summary": "string",
    "progress_highlights": ["string"],
    "next_steps": ["string"],
    "open_items_for_client": ["string"]
  }}
}}

QUALITY CHECKLIST
- No jargon (API, schema, backend, etc.) appears in the text.
- No date, price, or guarantee appears unless it was in the specification.
- Every specification open_question that needs the client appears in
  open_items_for_client.

{_FAILURE_BEHAVIOR}
"""


PROMPT_VERSION_RELEASE_NOTES_V1 = "release_notes_prompt_v1"


def build_release_notes_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a technical writer drafting release notes for a software house's
internal changelog.

OBJECTIVE
Draft a release-notes entry for the feature set described in the
specification below, written as if this were the first release covering
these features (version "0.1.0" unless the specification states a version).

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- "added" should list the features from the specification in plain
  release-note language.
- "known_issues" should include anything from the specification's
  assumptions or open_questions that a user could plausibly run into.
- Leave "changed" and "fixed" empty for a first release unless the
  specification explicitly describes a change to something pre-existing.
- Use today's context date as given; if no date is available, use
  "unspecified".

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "release_notes": {{
    "version": "string",
    "date": "string",
    "summary": "string",
    "added": ["string"],
    "changed": ["string"],
    "fixed": ["string"],
    "known_issues": ["string"]
  }}
}}

QUALITY CHECKLIST
- Every "added" item traces to a feature in the specification.
- No item claims something was "fixed" without the spec describing a
  pre-existing problem.

{_FAILURE_BEHAVIOR}
"""


PROMPT_VERSION_USER_STORIES_V1 = "user_stories_prompt_v1"


def build_user_stories_prompt(spec: dict) -> str:
    return f"""SYSTEM ROLE
You are a business analyst refining user stories for a software house.

OBJECTIVE
Produce a refined, complete set of user stories covering every feature in
the specification below — expanding on the specification's existing
user_stories where useful, and adding any that are clearly implied by a
feature but missing from the original list.

SOURCE CONTEXT
{_spec_context(spec)}

{_SHARED_RULES}
- Every feature in the specification should be covered by at least one
  story where a reasonable one exists.
- Do not invent a role, goal, or benefit that isn't supported by the
  specification's features, summary, or existing stories.

OUTPUT SCHEMA — return ONLY this JSON object:
{{
  "user_stories": [
    {{"role": "string", "goal": "string", "benefit": "string"}}
  ]
}}

QUALITY CHECKLIST
- Every feature is covered by at least one story where reasonably possible.
- No story invents a role or benefit unsupported by the specification.

{_FAILURE_BEHAVIOR}
"""
