def test_create_and_list_project(temp_db):
    pid = temp_db.create_project("Test Project", "desc", "2026-01-01T00:00:00Z")
    projects = temp_db.list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Test Project"
    assert projects[0]["project_id"] == pid


def test_input_document_roundtrip(temp_db):
    pid = temp_db.create_project("P", "", "2026-01-01T00:00:00Z")
    input_id = temp_db.save_input_document(pid, "text", "some requirement", "2026-01-01T00:00:01Z")
    assert input_id is not None


def test_artifact_and_latest_lookup(temp_db):
    pid = temp_db.create_project("P", "", "2026-01-01T00:00:00Z")
    input_id = temp_db.save_input_document(pid, "text", "req", "2026-01-01T00:00:00Z")
    run_id = temp_db.save_generation_run(pid, "qwen2.5:7b", "spec_prompt_v1", "ok",
                                          "2026-01-01T00:00:00Z", "project_spec", input_id=input_id)
    temp_db.save_artifact(run_id, pid, "project_spec", {"project_summary": "x"}, "2026-01-01T00:00:00Z")

    latest = temp_db.get_latest_artifact(pid, "project_spec")
    assert latest is not None
    assert latest["type"] == "project_spec"


def test_get_latest_artifact_prefers_approved_over_draft(temp_db):
    pid = temp_db.create_project("P", "", "2026-01-01T00:00:00Z")
    run_id = temp_db.save_generation_run(pid, "m", "v1", "ok", "2026-01-01T00:00:00Z", "project_spec")
    a1 = temp_db.save_artifact(run_id, pid, "project_spec", {"project_summary": "draft one"}, "2026-01-01T00:00:00Z")
    a2 = temp_db.save_artifact(run_id, pid, "project_spec", {"project_summary": "draft two"}, "2026-01-01T00:00:01Z")
    # a2 is newer, but a1 gets approved — approved should win regardless of recency
    temp_db.update_artifact_status(a1, "approved")

    latest = temp_db.get_latest_artifact(pid, "project_spec")
    assert latest["artifact_id"] == a1


def test_review_feedback_recorded(temp_db):
    pid = temp_db.create_project("P", "", "2026-01-01T00:00:00Z")
    run_id = temp_db.save_generation_run(pid, "m", "v1", "ok", "2026-01-01T00:00:00Z", "project_spec")
    aid = temp_db.save_artifact(run_id, pid, "project_spec", {"project_summary": "x"}, "2026-01-01T00:00:00Z")

    temp_db.save_review_feedback(aid, "approve", "looks good", "2026-01-01T00:00:02Z")
    feedback = temp_db.get_feedback_for_artifact(aid)
    assert len(feedback) == 1
    assert feedback[0]["label"] == "approve"


def test_evaluation_upsert_and_rerun(temp_db):
    temp_db.upsert_evaluation_result("T-001", "some scenario", "crud", ["summary"], "ok", "2026-01-01T00:00:00Z")
    temp_db.upsert_evaluation_result("T-001", "some scenario", "crud", ["summary"], "invalid_json", "2026-01-02T00:00:00Z")
    results = temp_db.list_evaluation_results()
    assert len(results) == 1  # upsert, not duplicate
    assert results[0]["status"] == "invalid_json"
