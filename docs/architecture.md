# Architecture, data model, and workflow

These are Mermaid diagrams — GitHub renders them natively in any `.md`
file, no image export needed. If your reviewer wants PNGs, paste each
block into https://mermaid.live and export.

## 1. Logical architecture

```mermaid
flowchart TB
    subgraph UI["Streamlit UI (ui/streamlit_app.py)"]
        A1[Text / Image / Combined input]
        A2[Artifact tabs: Spec, Stories, Criteria, Plan, QA, Dev Prompt, Client Update, Release Notes]
        A3[Review controls: Approve / Edit / Reject]
        A4[Evaluation dashboard]
    end

    subgraph API["FastAPI service (app/main.py)"]
        B1["/spec/generate"]
        B2["/spec/generate-from-image"]
        B3["/artifacts/{type}/generate"]
        B4["/artifacts/{id}/review"]
        B5["/artifacts/{id}/export"]
    end

    subgraph Core["Core logic"]
        C1[Prompt builders — versioned, one per artifact type]
        C2[llm_client.py — the only place that calls Ollama]
        C3[validator.py — JSON extraction + schema validation]
        C4[artifact_registry.py — type -> schema + prompt mapping]
    end

    subgraph Model["Ollama runtime (local)"]
        D1[Text model — Qwen3-family]
        D2[Vision model — for Day 2 image input]
    end

    subgraph Storage["SQLite (app/storage.py)"]
        E1[(project)]
        E2[(input_document)]
        E3[(generation_run)]
        E4[(artifact)]
        E5[(review_feedback)]
        E6[(evaluation_test)]
    end

    UI -- HTTP --> API
    API --> Core
    Core --> Model
    API --> Storage
```

## 2. Entity relationship diagram

```mermaid
erDiagram
    PROJECT ||--o{ INPUT_DOCUMENT : has
    PROJECT ||--o{ GENERATION_RUN : has
    PROJECT ||--o{ ARTIFACT : has
    INPUT_DOCUMENT ||--o{ GENERATION_RUN : "used by"
    GENERATION_RUN ||--o{ ARTIFACT : produces
    ARTIFACT ||--o{ REVIEW_FEEDBACK : "reviewed via"
    ARTIFACT ||--o{ GENERATION_RUN : "source for (Day 3 downstream gen)"

    PROJECT {
        int project_id PK
        string name
        string description
        string created_at
    }
    INPUT_DOCUMENT {
        int input_id PK
        int project_id FK
        string input_type "text|image|combined"
        string source_text
        string file_path
        string created_at
    }
    GENERATION_RUN {
        int run_id PK
        int project_id FK
        int input_id FK
        int source_artifact_id FK
        string artifact_type
        string model_name
        string prompt_version
        string status
        string created_at
    }
    ARTIFACT {
        int artifact_id PK
        int run_id FK
        int project_id FK
        string type
        string content_json
        string review_status "draft|approved|edited|rejected"
        string created_at
    }
    REVIEW_FEEDBACK {
        int feedback_id PK
        int artifact_id FK
        string reviewer_note
        string label "approve|edit|reject"
        string created_at
    }
    EVALUATION_TEST {
        string test_id PK
        string scenario
        string category
        string expected_fields
        string status
        string score_json
        string notes
        string run_at
    }
```

## 3. End-to-end workflow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant API as FastAPI
    participant M as Ollama model
    participant DB as SQLite

    U->>UI: Create project
    UI->>API: POST /projects
    API->>DB: INSERT project
    U->>UI: Paste requirement text (or upload image)
    UI->>API: POST /spec/generate
    API->>DB: INSERT input_document (raw input preserved)
    API->>M: prompt (spec_prompt_v1)
    M-->>API: raw text
    API->>API: extract_json + schema validate
    API->>DB: INSERT generation_run, artifact (status: draft)
    API-->>UI: spec JSON or structured error
    U->>UI: Reviews spec; requests downstream artifact
    UI->>API: POST /artifacts/{type}/generate
    API->>DB: fetch latest approved/draft spec artifact
    API->>M: prompt (artifact-specific, spec as context)
    M-->>API: raw text
    API->>API: extract_json + schema validate
    API->>DB: INSERT generation_run, artifact
    API-->>UI: artifact JSON or structured error
    U->>UI: Approve / Edit / Reject
    UI->>API: POST /artifacts/{id}/review
    API->>DB: UPDATE artifact.review_status, INSERT review_feedback
    U->>UI: Export
    UI->>API: GET /artifacts/{id}/export?format=markdown|json
    API-->>UI: rendered export
```
