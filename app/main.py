"""
FastAPI service — the layer Streamlit talks to. UI never touches Ollama or
SQLite directly (SRS Section 11: separate UI / service / model / storage).

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from . import storage, exporters
from .llm_client import generate_raw, generate_raw_with_images, LLMError, DEFAULT_MODEL, VISION_MODEL
from .prompts.spec_prompt import build_prompt_v1, PROMPT_VERSION_V1, build_prompt_vision_v1, PROMPT_VERSION_VISION_V1
from .validator import build_result, build_generic_result
from .artifact_registry import ARTIFACT_TYPES

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    yield


app = FastAPI(title="DevFlow Copilot", lifespan=lifespan)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Health / projects
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "text_model": DEFAULT_MODEL, "vision_model": VISION_MODEL}


@app.post("/projects")
def create_project(req: CreateProjectRequest):
    project_id = storage.create_project(req.name, req.description, now_iso())
    return {"project_id": project_id, "name": req.name}


@app.get("/projects")
def list_projects():
    return storage.list_projects()


# ---------------------------------------------------------------------------
# Day 1 — text-only spec generation
# ---------------------------------------------------------------------------

class GenerateSpecRequest(BaseModel):
    project_id: int
    requirement_text: str


@app.post("/spec/generate")
def generate_spec(req: GenerateSpecRequest):
    if not req.requirement_text.strip():
        raise HTTPException(status_code=400, detail="requirement_text is empty.")

    ts = now_iso()
    input_id = storage.save_input_document(req.project_id, "text", req.requirement_text, ts)
    prompt = build_prompt_v1(req.requirement_text)

    try:
        raw = generate_raw(prompt)
    except LLMError as e:
        storage.save_generation_run(req.project_id, DEFAULT_MODEL, PROMPT_VERSION_V1,
                                     "model_error", ts, "project_spec", input_id=input_id)
        raise HTTPException(status_code=502, detail=str(e))

    result = build_result(raw, DEFAULT_MODEL, PROMPT_VERSION_V1)
    run_id = storage.save_generation_run(req.project_id, DEFAULT_MODEL, PROMPT_VERSION_V1,
                                          result.status, ts, "project_spec", input_id=input_id)

    artifact_id = None
    if result.status == "ok":
        artifact_id = storage.save_artifact(run_id, req.project_id, "project_spec",
                                             result.spec.model_dump(), ts)

    payload = result.model_dump()
    payload["artifact_id"] = artifact_id
    return payload


# ---------------------------------------------------------------------------
# Day 2 — image / combined multimodal spec generation
# ---------------------------------------------------------------------------

@app.post("/spec/generate-from-image")
async def generate_spec_from_image(
    project_id: int = Form(...),
    requirement_text: str = Form(""),
    image: UploadFile = File(...),
):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{image.content_type}'. Allowed: {sorted(ALLOWED_IMAGE_TYPES)}",
        )

    contents = await image.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds the 8 MB size limit.")

    ts = now_iso()
    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    # sanitize filename: keep extension only, generate a safe stem
    ext = Path(image.filename or "upload.png").suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    safe_path = project_dir / f"{ts.replace(':', '-')}{ext}"
    with open(safe_path, "wb") as f:
        f.write(contents)

    input_type = "combined" if requirement_text.strip() else "image"
    input_id = storage.save_input_document(
        project_id, input_type, requirement_text, ts, file_path=str(safe_path)
    )

    prompt = build_prompt_vision_v1(requirement_text)

    try:
        raw = generate_raw_with_images(prompt, [str(safe_path)])
    except LLMError as e:
        storage.save_generation_run(project_id, VISION_MODEL, PROMPT_VERSION_VISION_V1,
                                     "model_error", ts, "project_spec", input_id=input_id)
        raise HTTPException(status_code=502, detail=str(e))

    result = build_result(raw, VISION_MODEL, PROMPT_VERSION_VISION_V1)
    run_id = storage.save_generation_run(project_id, VISION_MODEL, PROMPT_VERSION_VISION_V1,
                                          result.status, ts, "project_spec", input_id=input_id)

    artifact_id = None
    if result.status == "ok":
        artifact_id = storage.save_artifact(run_id, project_id, "project_spec",
                                             result.spec.model_dump(), ts)

    payload = result.model_dump()
    payload["artifact_id"] = artifact_id
    return payload


# ---------------------------------------------------------------------------
# Day 3 — downstream artifacts, generic over the registry
# ---------------------------------------------------------------------------

class GenerateArtifactRequest(BaseModel):
    project_id: int
    source_artifact_id: Optional[int] = None  # defaults to latest project_spec


@app.get("/artifact-types")
def list_artifact_types():
    return {key: d.display_name for key, d in ARTIFACT_TYPES.items()}


@app.post("/artifacts/{artifact_type}/generate")
def generate_artifact(artifact_type: str, req: GenerateArtifactRequest):
    if artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(status_code=404, detail=f"Unknown artifact type '{artifact_type}'.")

    if req.source_artifact_id:
        source = storage.get_artifact(req.source_artifact_id)
    else:
        source = storage.get_latest_artifact(req.project_id, "project_spec")

    if not source:
        raise HTTPException(
            status_code=400,
            detail="No project specification exists yet for this project — generate one first (Day 1/2).",
        )

    import json as _json
    spec_dict = _json.loads(source["content_json"])

    type_def = ARTIFACT_TYPES[artifact_type]
    prompt = type_def.prompt_builder(spec_dict)
    ts = now_iso()

    try:
        raw = generate_raw(prompt)
    except LLMError as e:
        storage.save_generation_run(req.project_id, DEFAULT_MODEL, type_def.prompt_version,
                                     "model_error", ts, artifact_type,
                                     source_artifact_id=source["artifact_id"])
        raise HTTPException(status_code=502, detail=str(e))

    result = build_generic_result(raw, type_def.schema_cls, DEFAULT_MODEL,
                                   type_def.prompt_version, artifact_type)
    run_id = storage.save_generation_run(req.project_id, DEFAULT_MODEL, type_def.prompt_version,
                                          result.status, ts, artifact_type,
                                          source_artifact_id=source["artifact_id"])

    artifact_id = None
    if result.status == "ok":
        artifact_id = storage.save_artifact(run_id, req.project_id, artifact_type, result.content, ts)

    payload = result.model_dump()
    payload["artifact_id"] = artifact_id
    return payload


@app.get("/projects/{project_id}/artifacts")
def list_project_artifacts(project_id: int, artifact_type: Optional[str] = None):
    return storage.list_artifacts_for_project(project_id, artifact_type)


# ---------------------------------------------------------------------------
# Day 5 — human review + export
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    action: str  # "approve" | "edit" | "reject"
    edited_content: Optional[dict] = None
    note: str = ""


@app.post("/artifacts/{artifact_id}/review")
def review_artifact(artifact_id: int, req: ReviewRequest):
    artifact = storage.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    if req.action not in {"approve", "edit", "reject"}:
        raise HTTPException(status_code=400, detail="action must be approve, edit, or reject.")

    ts = now_iso()
    if req.action == "approve":
        storage.update_artifact_status(artifact_id, "approved")
    elif req.action == "reject":
        storage.update_artifact_status(artifact_id, "rejected")
    elif req.action == "edit":
        if req.edited_content is None:
            raise HTTPException(status_code=400, detail="edited_content is required for action=edit.")
        storage.update_artifact_content(artifact_id, req.edited_content, "edited")

    storage.save_review_feedback(artifact_id, req.action, req.note, ts)
    return storage.get_artifact(artifact_id)


@app.get("/artifacts/{artifact_id}/export")
def export_artifact(artifact_id: int, format: str = "markdown"):
    import json as _json
    artifact = storage.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    content = _json.loads(artifact["content_json"])
    if format == "json":
        return {"format": "json", "content": exporters.to_json(content)}
    elif format == "markdown":
        return {"format": "markdown", "content": exporters.to_markdown(artifact["type"], content)}
    else:
        raise HTTPException(status_code=400, detail="format must be 'markdown' or 'json'.")
