"""
Day 5 — export approved artifacts to Markdown (human-readable) and JSON
(machine-readable). Kept as pure functions with no I/O so they're easy to
unit test (see tests/test_exporters.py).
"""

import json


def to_json(content: dict) -> str:
    return json.dumps(content, indent=2)


def to_markdown(artifact_type: str, content: dict) -> str:
    """Dispatches to a per-type renderer. Falls back to a generic
    key/value dump for any type not explicitly handled, so export never
    hard-fails on an unrecognized artifact."""
    renderer = _RENDERERS.get(artifact_type, _render_generic)
    return renderer(content)


def _render_project_spec(c: dict) -> str:
    lines = [f"# Project Specification\n", f"{c.get('project_summary', '')}\n"]
    lines.append("## Features\n")
    for f in c.get("features", []):
        lines.append(f"- **{f['name']}** ({f['priority']}) — {f['description']}")
    lines.append("\n## User Stories\n")
    for s in c.get("user_stories", []):
        lines.append(f"- As a **{s['role']}**, I want {s['goal']}, so that {s['benefit']}.")
    lines.append("\n## Assumptions\n")
    for a in c.get("assumptions", []):
        lines.append(f"- {a}")
    lines.append("\n## Open Questions\n")
    for q in c.get("open_questions", []):
        lines.append(f"- {q}")
    return "\n".join(lines)


def _render_user_stories(c: dict) -> str:
    lines = ["# User Stories\n"]
    for s in c.get("user_stories", []):
        lines.append(f"- As a **{s['role']}**, I want {s['goal']}, so that {s['benefit']}.")
    return "\n".join(lines)


def _render_acceptance_criteria(c: dict) -> str:
    lines = ["# Acceptance Criteria\n"]
    for a in c.get("acceptance_criteria", []):
        lines.append(f"### {a['story_id']}")
        lines.append(f"- **Given** {a['given']}")
        lines.append(f"- **When** {a['when']}")
        lines.append(f"- **Then** {a['then']}\n")
    return "\n".join(lines)


def _render_implementation_plan(c: dict) -> str:
    plan = c.get("implementation_plan", {})
    lines = ["# Implementation Plan\n"]
    for section in ["frontend", "backend", "data", "apis", "risks"]:
        lines.append(f"## {section.capitalize()}")
        for item in plan.get(section, []):
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def _render_test_cases(c: dict) -> str:
    lines = ["# QA Test Cases\n"]
    for t in c.get("test_cases", []):
        lines.append(f"### {t['test_id']} — {t['title']}")
        if t.get("preconditions"):
            lines.append(f"**Preconditions:** {t['preconditions']}")
        lines.append("**Steps:**")
        for i, step in enumerate(t.get("steps", []), 1):
            lines.append(f"{i}. {step}")
        lines.append(f"**Expected result:** {t['expected_result']}")
        if t.get("related_story_id"):
            lines.append(f"**Related story:** {t['related_story_id']}")
        lines.append("")
    return "\n".join(lines)


def _render_developer_prompt(c: dict) -> str:
    lines = ["# Developer Prompt\n"]
    if c.get("target_feature"):
        lines.append(f"**Target feature:** {c['target_feature']}\n")
    lines.append(c.get("developer_prompt", ""))
    return "\n".join(lines)


def _render_client_update(c: dict) -> str:
    cu = c.get("client_update", {})
    lines = ["# Client Update\n", cu.get("summary", ""), "\n## Progress\n"]
    for i in cu.get("progress_highlights", []):
        lines.append(f"- {i}")
    lines.append("\n## Next Steps\n")
    for i in cu.get("next_steps", []):
        lines.append(f"- {i}")
    lines.append("\n## We Need From You\n")
    for i in cu.get("open_items_for_client", []):
        lines.append(f"- {i}")
    return "\n".join(lines)


def _render_release_notes(c: dict) -> str:
    rn = c.get("release_notes", {})
    lines = [f"# Release {rn.get('version', '')} — {rn.get('date', '')}\n", rn.get("summary", "")]
    for section, label in [("added", "Added"), ("changed", "Changed"),
                            ("fixed", "Fixed"), ("known_issues", "Known Issues")]:
        lines.append(f"\n## {label}\n")
        for i in rn.get(section, []):
            lines.append(f"- {i}")
    return "\n".join(lines)


def _render_generic(c: dict) -> str:
    lines = ["# Artifact\n"]
    for k, v in c.items():
        lines.append(f"## {k}\n{v}\n")
    return "\n".join(lines)


_RENDERERS = {
    "project_spec": _render_project_spec,
    "user_stories": _render_user_stories,
    "acceptance_criteria": _render_acceptance_criteria,
    "implementation_plan": _render_implementation_plan,
    "test_cases": _render_test_cases,
    "developer_prompt": _render_developer_prompt,
    "client_update": _render_client_update,
    "release_notes": _render_release_notes,
}
