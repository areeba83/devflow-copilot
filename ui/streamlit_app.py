"""
DevFlow Copilot — combined UI for Days 1-5. Talks only to the FastAPI
service at API_BASE — never imports app/ directly, so UI and business
logic stay separated per the SRS.

Run with:
    streamlit run ui/streamlit_app.py
(with `uvicorn app.main:app --reload --port 8000` already running)
"""

import csv
import glob
from pathlib import Path

import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

ARTIFACT_TABS = [
    ("project_spec", "Specification"),
    ("user_stories", "Stories"),
    ("acceptance_criteria", "Criteria"),
    ("implementation_plan", "Plan"),
    ("test_cases", "QA"),
    ("developer_prompt", "Dev Prompt"),
    ("client_update", "Client Update"),
    ("release_notes", "Release Notes"),
]

st.set_page_config(page_title="DevFlow Copilot", layout="wide")


def api_get(path, **kwargs):
    return requests.get(f"{API_BASE}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)


def api_post(path, **kwargs):
    return requests.post(f"{API_BASE}{path}", timeout=kwargs.pop("timeout", 240), **kwargs)


# ---------------------------------------------------------------------------
# Sidebar: page + project selector
# ---------------------------------------------------------------------------

st.sidebar.title("DevFlow Copilot")
page = st.sidebar.radio("View", ["Workspace", "Evaluation"])

try:
    health = api_get("/health").json()
    st.sidebar.success(f"Text model: {health['text_model']}\n\nVision model: {health['vision_model']}")
except Exception:
    st.sidebar.error("Cannot reach the API service. Is `uvicorn app.main:app` running on port 8000?")
    st.stop()

# ===========================================================================
# EVALUATION PAGE (Day 4)
# ===========================================================================

if page == "Evaluation":
    st.title("Evaluation results")
    st.caption("Run `python eval/run_eval.py` from the project root to generate a report, then reload this page.")

    result_files = sorted(glob.glob("eval/results/eval_run_*.csv"), reverse=True)
    if not result_files:
        st.info("No evaluation runs found yet. Run `python eval/run_eval.py` first.")
        st.stop()

    chosen = st.selectbox("Evaluation run", result_files)
    with open(chosen) as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok_count = sum(1 for r in rows if r["status"] == "ok")
    st.metric("Structure-valid results", f"{ok_count} / {total}")

    adversarial_rows = [r for r in rows if r["group"] == "adversarial"]
    if adversarial_rows:
        adv_ok = sum(1 for r in adversarial_rows if r["status"] == "ok")
        st.metric("Prompt-injection cases resisted (still valid JSON)", f"{adv_ok} / {len(adversarial_rows)}")
        st.caption("A status other than 'ok' here needs manual inspection of the raw output — "
                   "it might mean the model broke schema *because* it complied with the injected "
                   "instruction, not just an unrelated failure.")

    st.subheader("Failed / needs review")
    failed = [r for r in rows if r["status"] != "ok"]
    if failed:
        st.dataframe(failed, use_container_width=True)
    else:
        st.caption("No structure_validity failures in this run.")

    st.subheader("All results")
    st.dataframe(rows, use_container_width=True)
    st.stop()

# ===========================================================================
# WORKSPACE PAGE (Days 1, 2, 3, 5)
# ===========================================================================

try:
    projects = api_get("/projects").json()
except Exception:
    projects = []

project_names = {p["name"]: p["project_id"] for p in projects}
selected_name = st.sidebar.selectbox("Project", options=["— new project —"] + list(project_names.keys()))

if selected_name == "— new project —":
    with st.sidebar.form("new_project"):
        new_name = st.text_input("Project name")
        new_desc = st.text_area("Description (optional)")
        if st.form_submit_button("Create project") and new_name.strip():
            resp = api_post("/projects", json={"name": new_name, "description": new_desc})
            if resp.ok:
                st.sidebar.success("Created — select it above.")
                st.rerun()
            else:
                st.sidebar.error(f"Could not create project: {resp.text}")
    st.title("DevFlow Copilot")
    st.info("Create a project on the left to get started.")
    st.stop()

project_id = project_names[selected_name]
st.title(f"DevFlow Copilot — {selected_name}")
st.caption("AI-generated drafts — every artifact requires human review before it's considered approved.")

# ---------- Input: Text / Image / Combined (Day 1 + Day 2) ----------

input_tab, artifacts_tab = st.tabs(["1. Generate specification", "2. Downstream artifacts & review"])

with input_tab:
    text_tab, image_tab, combined_tab = st.tabs(["Text", "Image", "Combined"])

    with text_tab:
        requirement_text = st.text_area("Requirement text", height=200, key="text_only", placeholder=(
            "e.g. \"We need a mobile app where customers can book appointments with "
            "our stylists...\""
        ))
        if st.button("Generate from text", type="primary", disabled=not requirement_text.strip()):
            with st.spinner("Generating..."):
                try:
                    resp = api_post("/spec/generate", json={"project_id": project_id, "requirement_text": requirement_text})
                    st.session_state["last_result"] = resp.json() if resp.ok else {"status": "http_error", "error_message": resp.text}
                except Exception as e:
                    st.session_state["last_result"] = {"status": "model_error", "error_message": str(e)}

    with image_tab:
        image_file = st.file_uploader("Upload a screenshot or wireframe (PNG/JPEG/WebP, max 8MB)",
                                       type=["png", "jpg", "jpeg", "webp"], key="image_only")
        if st.button("Generate from image", type="primary", disabled=image_file is None):
            with st.spinner("Analyzing image..."):
                try:
                    files = {"image": (image_file.name, image_file.getvalue(), image_file.type)}
                    data = {"project_id": str(project_id), "requirement_text": ""}
                    resp = requests.post(f"{API_BASE}/spec/generate-from-image", files=files, data=data, timeout=240)
                    st.session_state["last_result"] = resp.json() if resp.ok else {"status": "http_error", "error_message": resp.text}
                except Exception as e:
                    st.session_state["last_result"] = {"status": "model_error", "error_message": str(e)}

    with combined_tab:
        combined_text = st.text_area("Supporting text", height=120, key="combined_text")
        combined_image = st.file_uploader("Upload a screenshot or wireframe", type=["png", "jpg", "jpeg", "webp"], key="combined_image")
        if st.button("Generate from text + image", type="primary", disabled=combined_image is None):
            with st.spinner("Analyzing..."):
                try:
                    files = {"image": (combined_image.name, combined_image.getvalue(), combined_image.type)}
                    data = {"project_id": str(project_id), "requirement_text": combined_text}
                    resp = requests.post(f"{API_BASE}/spec/generate-from-image", files=files, data=data, timeout=240)
                    st.session_state["last_result"] = resp.json() if resp.ok else {"status": "http_error", "error_message": resp.text}
                except Exception as e:
                    st.session_state["last_result"] = {"status": "model_error", "error_message": str(e)}

    result = st.session_state.get("last_result")
    if result:
        status = result.get("status")
        if status == "ok":
            spec = result["spec"]
            st.success(f"Generated · model {result.get('model_name')} · prompt {result.get('prompt_version')}")

            st.subheader("Summary")
            st.write(spec["project_summary"])

            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Features ({len(spec['features'])})")
                for f in spec["features"]:
                    st.markdown(f"- **{f['name']}** ({f['priority']}) — {f['description']}")
                st.subheader(f"User stories ({len(spec['user_stories'])})")
                for s in spec["user_stories"]:
                    st.markdown(f"- As a **{s['role']}**, I want {s['goal']}, so that {s['benefit']}.")
            with col2:
                st.subheader(f"Assumptions ({len(spec['assumptions'])})")
                for a in spec["assumptions"]:
                    st.markdown(f"- ⚠️ {a}")
                st.subheader(f"Open questions ({len(spec['open_questions'])})")
                for q in spec["open_questions"]:
                    st.markdown(f"- ❓ {q}")

            with st.expander("Raw model output"):
                st.code(result.get("raw_model_output", ""), language="json")

            st.info("Switch to the **Downstream artifacts & review** tab to review this specification "
                    "and generate stories, criteria, plans, tests, and more from it.")

        elif status in ("invalid_json", "schema_error"):
            st.error(f"The model's output couldn't be used: {result.get('error_message')}")
            st.code(result.get("raw_model_output", ""), language="text")
        else:
            st.error(f"Generation failed: {result.get('error_message', result)}")

# ---------- Downstream artifacts + review (Day 3 + Day 5) ----------

with artifacts_tab:
    try:
        all_artifacts = api_get(f"/projects/{project_id}/artifacts").json()
    except Exception:
        all_artifacts = []

    spec_artifacts = [a for a in all_artifacts if a["type"] == "project_spec"]
    if not spec_artifacts:
        st.info("No specification generated yet for this project — use the first tab.")
        st.stop()

    tabs = st.tabs([label for _, label in ARTIFACT_TABS])

    for (artifact_type, label), tab in zip(ARTIFACT_TABS, tabs):
        with tab:
            existing = [a for a in all_artifacts if a["type"] == artifact_type]

            if artifact_type != "project_spec":
                if st.button(f"Generate {label}", key=f"gen_{artifact_type}"):
                    with st.spinner(f"Generating {label}..."):
                        try:
                            resp = api_post(f"/artifacts/{artifact_type}/generate", json={"project_id": project_id})
                            gen_result = resp.json() if resp.ok else {"status": "http_error", "error_message": resp.text}
                        except Exception as e:
                            gen_result = {"status": "model_error", "error_message": str(e)}

                        if gen_result.get("status") == "ok":
                            st.success("Generated.")
                        else:
                            st.error(f"Could not generate {label}: {gen_result.get('error_message', gen_result)}")
                            if gen_result.get("raw_model_output"):
                                st.code(gen_result["raw_model_output"], language="text")
                    st.rerun()

            existing = sorted(existing, key=lambda a: a["created_at"], reverse=True)
            if not existing:
                st.caption(f"No {label.lower()} generated yet.")
                continue

            for artifact in existing:
                with st.container(border=True):
                    st.caption(f"Artifact #{artifact['artifact_id']} · status: **{artifact['review_status']}** · {artifact['created_at']}")
                    import json as _json
                    content = _json.loads(artifact["content_json"])
                    st.json(content, expanded=False)

                    rcol1, rcol2, rcol3, rcol4 = st.columns(4)
                    if rcol1.button("Approve", key=f"approve_{artifact['artifact_id']}"):
                        api_post(f"/artifacts/{artifact['artifact_id']}/review", json={"action": "approve", "note": ""})
                        st.rerun()
                    if rcol2.button("Reject", key=f"reject_{artifact['artifact_id']}"):
                        api_post(f"/artifacts/{artifact['artifact_id']}/review", json={"action": "reject", "note": ""})
                        st.rerun()
                    if rcol3.button("Export MD", key=f"md_{artifact['artifact_id']}"):
                        exp = api_get(f"/artifacts/{artifact['artifact_id']}/export", params={"format": "markdown"}).json()
                        st.download_button("Download .md", exp["content"], file_name=f"{artifact_type}_{artifact['artifact_id']}.md",
                                            key=f"dlmd_{artifact['artifact_id']}")
                    if rcol4.button("Export JSON", key=f"json_{artifact['artifact_id']}"):
                        exp = api_get(f"/artifacts/{artifact['artifact_id']}/export", params={"format": "json"}).json()
                        st.download_button("Download .json", exp["content"], file_name=f"{artifact_type}_{artifact['artifact_id']}.json",
                                            key=f"dljson_{artifact['artifact_id']}")

                    with st.expander("Edit and resubmit"):
                        edited_text = st.text_area("Edit the JSON content directly", value=_json.dumps(content, indent=2),
                                                     height=200, key=f"edit_{artifact['artifact_id']}")
                        if st.button("Save edit", key=f"save_edit_{artifact['artifact_id']}"):
                            try:
                                edited_content = _json.loads(edited_text)
                                api_post(f"/artifacts/{artifact['artifact_id']}/review",
                                          json={"action": "edit", "edited_content": edited_content, "note": "manual edit"})
                                st.success("Saved.")
                                st.rerun()
                            except _json.JSONDecodeError as e:
                                st.error(f"Not valid JSON: {e}")
