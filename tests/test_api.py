"""
These are the same checks that were run manually against a live TestClient
during development — formalized as pytest so they run in CI / on any
machine with `pytest` installed, without needing Ollama.
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "text_model" in r.json()


def test_full_pipeline_spec_to_downstream_artifact_to_review_to_export(client):
    r = client.post("/projects", json={"name": "Salon Booking App"})
    project_id = r.json()["project_id"]

    r = client.post("/spec/generate", json={
        "project_id": project_id,
        "requirement_text": "We need a mobile app for booking salon appointments.",
    })
    assert r.status_code == 200
    spec_result = r.json()
    assert spec_result["status"] == "ok"
    spec_artifact_id = spec_result["artifact_id"]

    r = client.post("/artifacts/acceptance_criteria/generate", json={"project_id": project_id})
    assert r.status_code == 200
    ac_result = r.json()
    assert ac_result["status"] == "ok"
    ac_artifact_id = ac_result["artifact_id"]

    r = client.get(f"/projects/{project_id}/artifacts")
    assert len(r.json()) == 2

    r = client.post(f"/artifacts/{spec_artifact_id}/review", json={"action": "approve", "note": "looks good"})
    assert r.json()["review_status"] == "approved"

    r = client.get(f"/artifacts/{spec_artifact_id}/export?format=markdown")
    assert "Appointment booking" in r.json()["content"]

    r = client.get(f"/artifacts/{ac_artifact_id}/export?format=json")
    assert "acceptance_criteria" in r.json()["content"]

    r = client.post(f"/artifacts/{ac_artifact_id}/review",
                     json={"action": "edit", "edited_content": {"acceptance_criteria": []}, "note": "cleared"})
    assert r.json()["review_status"] == "edited"


def test_unknown_artifact_type_returns_404(client):
    r = client.post("/projects", json={"name": "P"})
    project_id = r.json()["project_id"]
    r = client.post("/artifacts/not_a_real_type/generate", json={"project_id": project_id})
    assert r.status_code == 404


def test_empty_requirement_text_returns_400(client):
    r = client.post("/projects", json={"name": "P"})
    project_id = r.json()["project_id"]
    r = client.post("/spec/generate", json={"project_id": project_id, "requirement_text": "   "})
    assert r.status_code == 400


def test_downstream_generation_without_a_spec_returns_400(client):
    r = client.post("/projects", json={"name": "Empty Project"})
    project_id = r.json()["project_id"]
    r = client.post("/artifacts/test_cases/generate", json={"project_id": project_id})
    assert r.status_code == 400


def test_review_with_invalid_action_returns_400(client):
    r = client.post("/projects", json={"name": "P"})
    project_id = r.json()["project_id"]
    r = client.post("/spec/generate", json={"project_id": project_id, "requirement_text": "some requirement text"})
    artifact_id = r.json()["artifact_id"]

    r = client.post(f"/artifacts/{artifact_id}/review", json={"action": "not_a_real_action"})
    assert r.status_code == 400


def test_review_nonexistent_artifact_returns_404(client):
    r = client.post("/artifacts/999999/review", json={"action": "approve"})
    assert r.status_code == 404
