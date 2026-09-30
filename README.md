# DevFlow Copilot

A local-first GenAI product for software houses: turn a client requirement
(text and/or a screenshot) into a reviewed, structured specification, then
into user stories, acceptance criteria, an implementation plan, QA test
cases, a developer prompt, a client update, and release notes — all
schema-validated, all traceable to source input and prompt version, all
gated behind human review before anything counts as approved. Built
entirely on a local Ollama model — **no paid API key anywhere.**

## Honesty note on what was actually verified

This was built in a sandboxed environment with no access to Ollama or
model downloads. What **was** actually run and passed, in this
environment:

- **31 automated `pytest` tests** covering schema validation, JSON
  extraction/repair, SQLite persistence, Markdown/JSON export, and the
  full FastAPI pipeline end-to-end (project → spec → downstream artifact
  → review → export → every documented error path) — all with the Ollama
  call mocked, since that part can't run here.
- **The Day 4 evaluation harness** (`eval/run_eval.py`), run against all
  35 scenarios (32 standard + 3 adversarial) with a mocked model, to
  confirm the harness itself works, produces a CSV, and saves per-scenario
  outputs correctly.

What was **not** run here and is genuinely yours to test: the actual
quality of what a real local model produces, the vision model's
screenshot-reading ability, and real-world latency. Run `pytest` yourself
first to confirm the environment is set up correctly, then move on to
real model testing — see `docs/limitations.md` for what to expect from
small local models specifically.

## Quick start

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull models sized to your hardware — start small
ollama pull qwen2.5:1.5b            # text model, try this first
ollama pull qwen2.5vl:7b            # vision model — check `ollama list`
                                     # for available multimodal tags on
                                     # your Ollama version; llava is a
                                     # fallback if no Qwen vision tag exists

# 3. Python setup
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt # to run the test suite

# 4. Point the app at your pulled model tags if different from the default
export DEVFLOW_MODEL=qwen2.5:1.5b
export DEVFLOW_VISION_MODEL=qwen2.5vl:7b

# 5. Confirm the environment works before touching the real model
pytest

# 6. Run it (two terminals)
uvicorn app.main:app --reload --port 8000
streamlit run ui/streamlit_app.py
```

Open the Streamlit URL (usually `http://localhost:8501`).

## Project structure

```
devflow-copilot/
  app/
    main.py                FastAPI service — every endpoint
    schemas.py               Pydantic models — spec + all 7 downstream artifacts
    validator.py               Generic JSON-extraction + schema validation
    llm_client.py               The only place that calls Ollama (text + vision)
    storage.py                   SQLite — Project/InputDocument/GenerationRun/
                                  Artifact/ReviewFeedback/EvaluationTest
    exporters.py                  Markdown + JSON rendering per artifact type
    artifact_registry.py           type -> {schema, prompt, version} mapping
    prompts/
      spec_prompt.py                Day 1 text + Day 2 vision prompts
      artifact_prompts.py            Day 3's seven downstream prompts
  ui/
    streamlit_app.py           Full UI: input tabs, artifact tabs, review,
                                export, evaluation dashboard
  eval/
    scenarios.json              32 standard + 3 adversarial scenarios
    run_eval.py                  Harness — runs every scenario, writes a
                                  scored CSV + raw outputs
  tests/
    conftest.py                  Shared fixtures (mocked LLM, temp SQLite)
    test_schemas.py, test_validator.py, test_storage.py,
    test_exporters.py, test_api.py         31 automated tests total
    test_requirements.md          Original 13 manual Day-1 test cases
                                   (kept — useful for quick spot-checks
                                   beyond the full eval set)
  docs/
    architecture.md              Architecture / ERD / workflow (Mermaid)
    demo_script.md                 Step-by-step demo script
    limitations.md                  Known limitations and failure modes
  data/                         SQLite DB + uploaded images (gitignored)
```

## What each day added

| Day | What it added | Where |
|---|---|---|
| 1 | Text → structured spec, schema validation, SQLite persistence | `app/main.py` `/spec/generate`, `app/schemas.py` `ProjectSpec` |
| 2 | Image/screenshot → spec (multimodal), combined text+image | `/spec/generate-from-image`, `llm_client.generate_raw_with_images`, `spec_prompt.build_prompt_vision_v1` |
| 3 | 7 downstream artifacts, all generic over one registry | `artifact_registry.py`, `prompts/artifact_prompts.py`, `/artifacts/{type}/generate` |
| 4 | 30+ scenario evaluation set incl. adversarial/prompt-injection cases | `eval/scenarios.json`, `eval/run_eval.py` |
| 5 | Review (approve/edit/reject), export (MD/JSON), combined UI, docs | `/artifacts/{id}/review`, `/artifacts/{id}/export`, `app/exporters.py`, `ui/streamlit_app.py` |

## Running the test suite

```bash
pytest -v
```

31 tests, no Ollama required — the model call is mocked so this checks
the pipeline logic (schema validation, persistence, export, every error
path) independent of model quality.

## Running the evaluation harness (Day 4)

With the API running (`uvicorn app.main:app --port 8000`) and a real
model pulled:

```bash
python eval/run_eval.py
```

Writes `eval/results/eval_run_<timestamp>.csv` and per-scenario raw
outputs to `eval/results/outputs/`. Open the CSV and fill in the six
manual 0-5 score columns (completeness, evidence fidelity, testability,
engineering usefulness, uncertainty handling, reviewer acceptance) after
reading each output — see `docs/limitations.md` for why this step can't
be automated away. Then check the Evaluation page in the Streamlit UI to
see it summarized.

## SRS Section 25 acceptance checklist

- [x] Create a project and submit text requirements — Day 1
- [x] Upload a screenshot/image and combine it with text — Day 2
- [x] Structured specification, schema-validated — Day 1
- [x] User stories, acceptance criteria, implementation plan, QA tests,
      developer prompt — Day 3 (plus client update and release notes,
      beyond the minimum list)
- [x] Unknown/missing information surfaced (assumptions/open_questions,
      never silently invented) — Days 1-3, enforced by every prompt's
      RULES + FAILURE BEHAVIOR sections
- [x] Human review mandatory before approval — Day 5 (`review_status`
      starts at `draft`, only changes via an explicit review action)
- [x] 30+ evaluation scenarios — Day 4 (32 standard + 3 adversarial)
- [x] Evaluation results saved and summarized — `eval/run_eval.py` +
      Evaluation page
- [x] Export to Markdown and JSON — Day 5
- [x] Runs without a paid API key — Ollama only, throughout
- [x] No production credentials, no autonomous deployment
- [x] README, architecture/ERD/workflow diagrams, prompts, tests,
      limitations — this file + `docs/`
- [ ] **You still need to:** actually pull models, run the app, work
      through the eval set with a real model, and fill in the manual
      score columns — that's real Day 4/5 work no one can do for you
      from a sandbox.

## Explaining the local-first trade-off (for the demo)

Local-first means zero marginal cost per generation and no client data
ever leaving the machine (NFR-002, NFR-007) — real advantages for a
software house handling confidential client requirements. The trade-off:
small local models are meaningfully less capable than frontier hosted
models at exactly the kind of disciplined, schema-following, "don't
invent facts" behavior this product depends on. The whole architecture —
strict schema validation, explicit null/empty failure behavior, mandatory
human review before approval — exists *because* of that trade-off, not
despite it. That's the answer if asked "why not just use GPT-4/Claude
here": the SRS's zero-paid-API constraint is real, but even without it,
a product touching real client requirements should validate and review
AI output rather than trust it blindly (SRS Section 2's research basis).
