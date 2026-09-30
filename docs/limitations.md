# Known limitations and failure modes

Required by SRS Section 27. Written honestly — SRS Section 18 explicitly
says not to claim a hallucination-free system or hide uncertainty.

## Architectural / scope limitations

- **No retrieval (Sentence Transformers + FAISS).** Every generation
  works from a single input or a single prior artifact — there's no
  cross-document retrieval across a project's history yet. Fine for the
  5-day MVP scope; would matter for a project with many linked documents.
- **No authentication or multi-user access control.** Local-first, single
  user, matches SRS Section 6.2 (enterprise SSO/RBAC explicitly out of
  scope).
- **SQLite, not a production database.** Fine for local-first use;
  concurrent multi-writer access is not handled.
- **Downstream artifacts (Day 3) always derive from the latest
  approved-or-draft `project_spec`**, never from an arbitrary older
  version. If you need to compare artifacts generated from two different
  spec revisions, you'd need to track `source_artifact_id` manually from
  the `generation_run` table.

## Model / GenAI limitations

- **Local models are not immune to hallucination.** The prompts and
  schema validation reduce fabricated facts and catch some structural
  nonsense, but they do not guarantee zero hallucination — that's why
  human review is mandatory before any artifact counts as approved.
- **Small local models (1.5B-3B range) will be noticeably less reliable**
  at following the "don't invent, use null/empty, ask instead" rules than
  a larger model. If you're running on modest hardware and using a small
  model, expect to see more `schema_error`/`invalid_json` results and
  weaker assumption/open-question discipline — this is a real, documented
  trade-off (NFR-010), not a bug to silently work around.
- **Vision model quality varies a lot more than text model quality**
  across Ollama's available multimodal tags. Screenshot analysis (Day 2)
  is the least reliable part of the pipeline; expect to need a few
  prompt-tuning passes specific to your chosen vision model.
- **Consistency across repeated runs is not guaranteed.** Local models at
  default sampling settings can phrase the same requirement differently
  each run. The eval harness's consistency-check scenario is designed to
  surface this — see `eval/scenarios.json`.
- **Prompt injection resistance is prompt-based, not guaranteed.** The
  prompts instruct the model to treat embedded instruction-like text as
  data, and the adversarial eval scenarios test this, but this is not a
  formal security boundary — don't feed genuinely untrusted/adversarial
  content into a deployment of this tool without further hardening.

## Known failure modes to expect and how they surface

| Failure | How it shows up | Where it's handled |
|---|---|---|
| Model returns prose instead of JSON | `status: invalid_json`, raw text shown | `validator.py` / UI error banner |
| Model returns JSON with wrong types/enum | `status: schema_error`, error message shown | `validator.py` / UI error banner |
| Ollama not running / model not pulled | HTTP 502 with a clear message | `llm_client.py` `LLMError` |
| Empty/whitespace-only requirement text | HTTP 400 before any model call | `main.py` input validation |
| Downstream artifact requested with no spec yet | HTTP 400, clear message | `main.py` |
| Uploaded file isn't an allowed image type / too large | HTTP 400 | `main.py` upload validation |
| Vague input ("make it faster") | Should produce mostly-empty features + real open_questions, not invented specifics | Prompt `FAILURE BEHAVIOR` clause — verify manually per scenario |

## What "done" does not mean here

Passing the automated test suite (`pytest`) and the structure-validity
checks in the eval harness means the *pipeline* is reliable — JSON in,
JSON out, schema respected, no crashes. It does **not** mean the
*content* the model generates is always good. That's exactly why SRS
Section 21's qualitative metrics (completeness, evidence fidelity,
testability, engineering usefulness, uncertainty handling, reviewer
acceptance) require a human to actually read the outputs — no script in
this repo can fill those columns in for you.
