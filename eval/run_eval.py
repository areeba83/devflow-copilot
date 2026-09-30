"""
Day 4 evaluation harness. Runs every scenario in scenarios.json through the
live API (spec generation), records automated signals (structure validity,
latency), and writes a CSV with placeholder columns for the manual 0-5
metrics from SRS Section 21 (completeness, evidence fidelity, testability,
engineering usefulness, uncertainty handling, reviewer acceptance) — those
require a human actually reading the output, so this script sets up the
scoring sheet rather than faking the scores.

Usage (with the API already running on port 8000):
    python eval/run_eval.py

This creates eval/results/eval_run_<timestamp>.csv — open it, read each
generated spec (also saved to eval/results/outputs/), and fill in the six
score columns plus notes.
"""

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE = "http://127.0.0.1:8000"
SCENARIOS_PATH = Path(__file__).parent / "scenarios.json"
RESULTS_DIR = Path(__file__).parent / "results"

SCORE_COLUMNS = [
    "requirement_completeness_0_5", "evidence_fidelity_0_5", "testability_0_5",
    "engineering_usefulness_0_5", "uncertainty_handling_0_5", "reviewer_acceptance_0_5",
]


def run_all(post_fn=None):
    """post_fn(url, json=...) -> response-like object with .status_code and
    .json(). Defaults to requests.post against the live API; tests pass in
    a FastAPI TestClient's .post instead so this logic runs without a
    server or Ollama."""
    post_fn = post_fn or requests.post

    data = json.loads(SCENARIOS_PATH.read_text())
    scenarios = data["scenarios"]
    adversarial = data["adversarial_scenarios"]

    RESULTS_DIR.mkdir(exist_ok=True)
    outputs_dir = RESULTS_DIR / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    # one throwaway project holds every eval run so results don't pollute
    # real project data
    proj_resp = post_fn(f"{API_BASE}/projects", json={"name": "Evaluation Run", "description": "Day 4 eval harness"})
    project_id = proj_resp.json()["project_id"]

    rows = []

    for group_name, group in [("standard", scenarios), ("adversarial", adversarial)]:
        for scenario in group:
            start = time.time()
            resp = post_fn(f"{API_BASE}/spec/generate", json={
                "project_id": project_id,
                "requirement_text": scenario["text"],
            })
            latency = round(time.time() - start, 2)

            try:
                body = resp.json()
                status = body.get("status", f"http_{resp.status_code}")
                artifact_id = body.get("artifact_id")
            except Exception:
                status = f"http_{resp.status_code}"
                artifact_id = None
                body = {}

            (outputs_dir / f"{scenario['id']}.json").write_text(json.dumps(body, indent=2))

            row = {
                "test_id": scenario["id"],
                "group": group_name,
                "category": scenario.get("category", ""),
                "deliberately_missing_info": scenario.get("deliberately_missing_info", ""),
                "status": status,
                "latency_seconds": latency,
                "artifact_id": artifact_id,
                "output_file": f"outputs/{scenario['id']}.json",
                "notes": "",
            }
            for col in SCORE_COLUMNS:
                row[col] = ""
            rows.append(row)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"eval_run_{ts}.csv"
    fieldnames = ["test_id", "group", "category", "deliberately_missing_info", "status",
                  "latency_seconds", "artifact_id", "output_file"] + SCORE_COLUMNS + ["notes"]

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    ok_count = sum(1 for r in rows if r["status"] == "ok")
    print(f"Ran {len(rows)} scenarios ({len(scenarios)} standard, {len(adversarial)} adversarial).")
    print(f"Structure-valid ('ok') results: {ok_count}/{len(rows)}")
    print(f"Results written to: {out_path}")
    print(f"Per-scenario raw outputs: {outputs_dir}/")
    print("\nNext step: open the CSV, read each output, and fill in the six "
          "score columns (0-5) plus notes — especially for the 'adversarial' "
          "group, where 'ok' status means the model kept returning a valid "
          "spec instead of complying with the injected instruction.")

    return out_path, rows


if __name__ == "__main__":
    run_all()
