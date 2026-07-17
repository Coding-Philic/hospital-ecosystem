# MediFlow AI — Complete Project Report & System Design

> **"AI recommends. Licensed humans decide."**
> The complete AI-powered operating system for modern hospitals.

MediFlow AI is a production-grade, multi-agent hospital orchestration ecosystem. It connects five roles — Patient, Receptionist, Doctor, Pharmacist, and Admin — into one seamless, real-time digital workflow. It eliminates three fundamental hospital problems: blind queuing, the prescription-pharmacy gap, and paper-based patient records.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Project File Structure](#2-project-file-structure)
3. [Technology Stack](#3-technology-stack)
4. [Database Schema (13 Tables)](#4-database-schema-13-tables)
5. [Authentication & Session System](#5-authentication--session-system)
6. [The AI Agent Layer](#6-the-ai-agent-layer)
7. [LangGraph Orchestrator — The Brain](#7-langgraph-orchestrator--the-brain)
8. [The Workflow State Machine](#8-the-workflow-state-machine)
9. [The Groq LLM Client & Model Fallback](#9-the-groq-llm-client--model-fallback)
10. [The Navigation System (Responsive Navbar)](#10-the-navigation-system-responsive-navbar)
11. [Role-Based Dashboards — Complete Button Guide](#11-role-based-dashboards--complete-button-guide)
    - [Landing Page](#landing-page)
    - [Patient Portal](#-patient-portal-5-tabs)
    - [Reception Dashboard](#-reception-dashboard-6-tabs)
    - [Doctor Dashboard](#-doctor-dashboard-5-tabs)
    - [Pharmacy Dashboard](#-pharmacy-dashboard-4-tabs)
    - [Admin Dashboard](#-admin-dashboard-5-tabs)
12. [Complete End-to-End Workflow (Patient Journey)](#12-complete-end-to-end-workflow-patient-journey)
13. [Safety, Compliance & Human Checkpoints](#13-safety-compliance--human-checkpoints)
14. [Configuration & Environment Variables](#14-configuration--environment-variables)
15. [Getting Started](#15-getting-started)

---

## 1. System Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                    BROWSER / CLIENT                           │
│  (Desktop / Tablet / Mobile — Responsive CSS Breakpoints)     │
└───────────────────────────┬───────────────────────────────────┘
                            │  HTTPS
┌───────────────────────────▼───────────────────────────────────┐
│                   STREAMLIT APPLICATION                        │
│   app.py  ──  Cookie Session Restore  ──  Role-Based Routing  │
├───────────────────────────────────────────────────────────────┤
│              UI / COMPONENT LAYER                             │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ auth.py │ │navbar.py │ │intake_chat│ │prescription_   │  │
│  │ Login / │ │Responsive│ │.py        │ │form.py         │  │
│  │ SignUp  │ │Top Nav   │ │Multi-Modal│ │Rx Entry Form   │  │
│  └─────────┘ └──────────┘ └───────────┘ └────────────────┘  │
│  ┌─────────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│  │ queue_display.py│ │workflow_     │ │charts.py           │ │
│  │ Queue Cards &   │ │tracker.py    │ │Plotly Analytics    │ │
│  │ Metric Widgets  │ │Progress Bar  │ │(Admin)             │ │
│  └─────────────────┘ └──────────────┘ └────────────────────┘ │
├───────────────────────────────────────────────────────────────┤
│              PAGE LAYER (5 Role-Based Pages)                  │
│  pages/1_Patient_Portal.py    pages/2_Reception_Dashboard.py  │
│  pages/3_Doctor_Dashboard.py  pages/4_Pharmacy_Dashboard.py   │
│  pages/5_Admin_Dashboard.py                                   │
├───────────────────────────────────────────────────────────────┤
│              AGENT LAYER (LangGraph Orchestrated)             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  orchestrator.py  (LangGraph StateGraph Supervisor)    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │  intake_graph│  │prescription_ │  │workflow_    │  │  │
│  │  │  Symptom →   │  │graph         │  │graph        │  │  │
│  │  │  Queue       │  │Rx → Pharmacy │  │State Trans. │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐   │
│  │symptom_      │ │prescription_ │ │pharmacy_agent.py    │   │
│  │classifier.py │ │agent.py      │ │Stock Check / Alt    │   │
│  │AI Triage     │ │AI Rx Valid.  │ │Suggestion           │   │
│  └──────────────┘ └──────────────┘ └─────────────────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐   │
│  │intake_chat_  │ │queue_manager │ │workflow_agent.py    │   │
│  │agent.py      │ │.py           │ │State Machine /      │   │
│  │Streaming AI  │ │Doctor Match  │ │Audit Logging        │   │
│  │Nurse + TTS   │ │& Token       │ │                     │   │
│  └──────────────┘ └──────────────┘ └─────────────────────┘   │
├───────────────────────────────────────────────────────────────┤
│              LLM LAYER                                        │
│  llm_client.py  ──  Groq API  ──  3-Model Fallback Chain     │
│  qwen/qwen3.6-27b → openai/gpt-oss-120b → llama-3.3-70b     │
│                    → llama-3.1-8b-instant                    │
│  intake_chat_agent.py uses raw Groq SDK (streaming + vision) │
├───────────────────────────────────────────────────────────────┤
│              DATABASE LAYER                                   │
│  database/supabase_client.py  (2 clients: anon + admin)      │
│  database/queries.py          (All CRUD operations, 681 lines)│
│  database/models.py           (Pydantic data models)         │
├───────────────────────────────────────────────────────────────┤
│              SUPABASE (PostgreSQL + Auth)                     │
│  13 Tables  ──  RLS Policies  ──  JWT Auth  ──  Seed Data    │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Project File Structure

```
hospital ecosystem/
│
├── app.py                      # Main entry point: theme CSS, session restore, role routing
├── config.py                   # Central config: API keys, departments, urgency levels,
│                               # workflow states, red-flag symptoms, model chain
├── requirements.txt            # Python dependencies
├── .env                        # Secret keys (never commit)
├── .streamlit/                 # Streamlit config (theme, server settings)
│
├── pages/                      # Role-based Streamlit pages (auto-routed)
│   ├── 1_Patient_Portal.py     # Patient dashboard (5 tabs)
│   ├── 2_Reception_Dashboard.py# Reception dashboard (6 tabs)
│   ├── 3_Doctor_Dashboard.py   # Doctor dashboard (5 tabs)
│   ├── 4_Pharmacy_Dashboard.py # Pharmacy dashboard (4 tabs)
│   └── 5_Admin_Dashboard.py    # Admin dashboard (5 tabs)
│
├── components/                 # Reusable UI components
│   ├── auth.py                 # Landing page, login form, signup form, logout button
│   ├── navbar.py               # Responsive top navigation (Desktop/Tablet/Mobile)
│   ├── intake_chat.py          # Multi-modal AI chat (text, voice, image), TTS
│   ├── prescription_form.py    # Structured Rx entry form (add/edit/remove items)
│   ├── patient_intake_form.py  # Patient health profile form
│   ├── queue_display.py        # Queue cards and metric widgets
│   ├── workflow_tracker.py     # Visual progress bar + timeline expander
│   ├── charts.py               # Plotly charts for Admin analytics
│   ├── chat_input_component/   # Custom chat input web component
│   └── voice_component/        # Custom voice/TTS web component (pulsing orb UI)
│
├── agents/                     # AI agent layer
│   ├── orchestrator.py         # LangGraph StateGraph (3 compiled graphs + public API)
│   ├── intake_chat_agent.py    # Streaming AI Triage Nurse (Groq SDK, Whisper, vision)
│   ├── symptom_classifier.py   # Symptom → Dept/Urgency + clinical note generation
│   ├── queue_manager.py        # Doctor matching + token assignment
│   ├── prescription_agent.py   # Rx validation (interactions, allergies) + AI auto-gen
│   ├── pharmacy_agent.py       # Stock check + AI alternative suggestion + dispense
│   ├── workflow_agent.py       # State machine transitions + audit + notifications
│   ├── notification_agent.py   # In-app patient notifications
│   └── llm_client.py           # Groq LLM wrapper with 3-model fallback chain
│
├── database/
│   ├── supabase_client.py      # 2-client pattern (anon + admin), cookie session auth
│   ├── queries.py              # All CRUD operations for all 13 tables (681 lines)
│   └── models.py               # Pydantic data validation models
│
└── utils/
    ├── constants.py            # Dosage frequencies, routes, investigation types,
    │                           # blood groups, workflow display config, color palette
    └── helpers.py              # Token generation, wait time estimation, patient ID
                                # generation (MF-XXXXXXXX), Rx ID (RX-XXXXXXXXXX),
                                # urgency badge HTML, age calculation
```

---

## 3. Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend Framework** | Streamlit (Python) | Multi-page app, wide layout, sidebar hidden |
| **UI Styling** | Custom CSS injection | Injected via `st.markdown()` — Inter font, CSS variables, dark/light theme tokens, glassmorphism navbar |
| **Responsive Design** | CSS Media Queries | Three layouts: Desktop (>1100px), Tablet (768–1100px), Mobile (<768px) |
| **AI Orchestration** | LangGraph `StateGraph` | Supervisor pattern, 3 compiled graphs, lazy-initialized singletons |
| **LLM Provider** | Groq API | Via `langchain-groq` (ChatGroq) for agents; raw `groq` SDK for streaming chat & Whisper ASR |
| **Primary Chat Model** | `qwen/qwen3.6-27b` | Multimodal (text + vision), used for intake chat |
| **Voice Mode Model** | `llama-3.3-70b-versatile` | Used for voice mode (no vision needed) |
| **Agent Models** | `openai/gpt-oss-120b` → `llama-3.3-70b` → `llama-3.1-8b-instant` | 3-model fallback chain for all non-chat agents |
| **Speech-to-Text** | Groq Whisper (`whisper-large-v3`) | Transcribes voice input to text |
| **Text-to-Speech** | gTTS (Google TTS) | Auto language detection (Hindi Devanagari vs English) |
| **Database** | Supabase PostgreSQL | 13 tables, Row-Level Security, seeded departments/medicines |
| **Auth** | Supabase Auth (JWT) | Email/password; sessions persisted in browser cookies (7-day TTL) |
| **Cookie Persistence** | `streamlit-cookies-controller` | Saves `access_token` + `refresh_token` to browser |
| **Data Validation** | Pydantic | Input/output models for all agent I/O |
| **Charts** | Plotly Express | Department load, urgency pie, status pie, doctor workload charts |

---

## 4. Database Schema (13 Tables)

### Entity Relationship Map

```
auth.users (Supabase managed)
    └── users (public profile: full_name, role, phone, is_active)
            ├── doctors (specialization, qualification, experience_years,
            │           license_number, consultation_fee, max_daily_patients,
            │           current_token, status: available/busy/on_break/offline)
            │       └── departments (name, description, floor_number, is_active)
            ├── patients (patient_id_code [MF-XXXXXXXX], date_of_birth,
            │            gender, blood_group, allergies[], chronic_conditions[],
            │            insurance_provider, emergency_contact)
            │       └── appointments (token_number, queue_position, urgency,
            │                        status, symptom_summary, ai_recommended_department,
            │                        ai_urgency_score, ai_confidence, receptionist_confirmed,
            │                        consultation_start_time, consultation_end_time)
            │               ├── consultations (symptoms, vitals{bp,temp,pulse,spo2,
            │               │               weight,height}, examination_notes, diagnosis,
            │               │               additional_notes, follow_up_date, follow_up_notes)
            │               │       └── prescriptions (prescription_code [RX-XXXXXXXXXX],
            │               │               status: created/sent_to_pharmacy/
            │               │               partially_available/dispensed/cancelled)
            │               │               └── prescription_items (medicine_name, dosage,
            │               │                   frequency, route, duration, quantity,
            │               │                   instructions, is_in_stock, substitute_approved)
            │               └── workflow_states (current_state, previous_state,
            │                                   transitioned_by, transitioned_by_role,
            │                                   notes, metadata{invoice})
            └── notifications (type, title, message, is_read)

medicines (name, generic_name, category, dosage_form, strength, unit_price)
    └── pharmacy_inventory (quantity_available, reorder_level, batch_number,
                           expiry_date, selling_price)

audit_log (actor_id, actor_role, action, entity_type, entity_id,
           details{}, was_overridden, override_reason, ai_model_used, ai_confidence)
```

### Row-Level Security (RLS) Policies

| Role | Data Access |
|---|---|
| `patient` | Own patient record, own appointments, own prescriptions, own notifications |
| `doctor` | All patients in their department, own consultations, all prescriptions they wrote |
| `receptionist` | All patients, all appointments, all departments |
| `pharmacist` | All prescriptions, all pharmacy inventory |
| `admin` | All tables including `audit_log` and `users` |

### Token Number Format (from `helpers.py`)
Tokens are generated per-department: `GEN-001`, `CARD-002`, `EMRG-003`, `DERM-004`, etc. The `current_token` counter on the `doctors` table is incremented atomically via a Supabase PostgreSQL RPC function (`increment_and_return_token`) to prevent duplicate tokens under concurrent submissions.

---

## 5. Authentication & Session System

### Flow

```
User visits app.py
    │
    ├── CookieController initializes (renders hidden iframe component)
    │
    ├── is_authenticated()? NO
    │       └── restore_session_from_cookies(cookie_controller)
    │               ├── Read mediflow_access_token + mediflow_refresh_token from cookies
    │               ├── set_session(access_token, refresh_token) on fresh Supabase client
    │               └── Populate st.session_state["authenticated", "user", "session", "profile", "role"]
    │
    └── is_authenticated()? YES
            └── role_page_map[role] → st.session_state["_pending_redirect"] → st.switch_page()
```

### Two-Client Supabase Pattern
- **`get_supabase_client()`** — `@st.cache_resource`, anon key, shared across all users. Never used for auth.
- **`get_supabase_admin_client()`** — `@st.cache_resource`, **service role key**, bypasses all RLS. Used for all CRUD in `queries.py`.
- **`_create_fresh_auth_client()`** — New instance per call. Used only for `sign_in`, `sign_out`, `set_session` so one user's auth state never leaks to another.

### Cookie Persistence
- Tokens stored with a **7-day max-age** under keys `mediflow_access_token` and `mediflow_refresh_token`.
- On every `require_auth()` call at the top of each page, the system checks the cookie and restores the session automatically — users stay logged in across page reloads.

### Sign-Up (Automatic Patient Record Creation)
When a user signs up with role `patient`, the `_render_signup_form()` function immediately calls `db.create_patient()` to generate a `MF-XXXXXXXX` patient ID code and create the linked patient record.

---

## 6. The AI Agent Layer

### 6.1 Intake Chat Agent (`agents/intake_chat_agent.py`)

**Role:** A conversational AI Triage Nurse.

**Model:**
- Text mode: `qwen/qwen3.6-27b` (multimodal — supports image vision)
- Voice mode: `llama-3.3-70b-versatile` (text-only, fast)

**Behavior:**
- Greets patient bilingually (English + Hindi)
- Automatically detects the language of every user message and **replies in that exact same language** (strict monolingual rule — never mixes)
- Loads the patient's last 5 consultation records into the system prompt as context
- Asks a maximum of **5–6 targeted follow-up questions** (onset, duration, severity, location)
- Strips `<think>...</think>` reasoning blocks from model output before streaming to the user
- When it has enough information, emits a final JSON block:
  ```json
  {"status": "complete", "patient_report": "...", "recommended_department": "...", "urgency_level": "..."}
  ```
- `parse_intake_completion()` watches for this JSON in every streamed response
- On completion: calls `run_direct_queue_allocation()` → bypasses the symptom classifier, directly calls the queue manager node with pre-set department and urgency

**Voice Transcription:** `transcribe_audio()` calls Groq's `whisper-large-v3` via the raw Groq SDK to convert voice recordings to text.

**TTS:** `text_to_speech_auto()` uses `gTTS` — detects Devanagari Unicode to choose `lang='hi'`, otherwise `lang='en'`.

---

### 6.2 Symptom Classifier Agent (`agents/symptom_classifier.py`)

**Role:** AI department router for the standard (non-chat) intake pipeline.

**Pre-Check:** Before the LLM call, performs an instant keyword scan against `config.RED_FLAG_SYMPTOMS` (chest pain, stroke symptoms, severe bleeding, anaphylaxis, etc.). If any red flag is found, forces `urgency_level = "emergency"` regardless of the LLM's response.

**LLM Prompt:** Receives available departments, red flags, patient age/gender/allergies/conditions. Returns structured JSON with `recommended_department`, `urgency_level` (routine/semi_urgent/urgent/emergency), `confidence_score` (0.0–1.0), `reasoning`, `is_emergency`, `red_flags_detected[]`, `suggested_investigations[]`.

**Graceful Degradation:** If JSON parsing fails or the LLM is unavailable, defaults to `General Medicine` + `routine` (or `emergency` if pre-check flagged red flags).

**Secondary Function:** `generate_clinical_notes_from_triage()` — Called by the Doctor's "AI Auto-Fill" button. Takes the triage summary + current vitals + patient info and generates a structured `{symptoms, examination_notes, diagnosis, additional_notes}` JSON for the doctor to review.

---

### 6.3 Queue Manager Agent (`agents/queue_manager.py`)

**Role:** Matches the classified department to the best available doctor and assigns a numbered queue token.

**Logic:**
1. `find_best_doctor(department, urgency)` — Queries `get_available_doctors()` filtered by department. Sorts by shortest queue (lowest `current_token`). For `emergency` urgency, may select any available doctor.
2. `assign_queue_token(patient_id, doctor_id, ...)` — Atomically increments the doctor's `current_token` via the PostgreSQL RPC, creates an `appointments` record with `status = "waiting"`, sets `receptionist_confirmed = False` (pending triage confirmation), and creates the first `workflow_states` entry (`registered`).

---

### 6.4 Prescription Agent (`agents/prescription_agent.py`)

**Role:** Validates doctor prescriptions and creates structured digital prescriptions in the database.

**Steps:**
1. Generate unique `RX-XXXXXXXXXX` prescription code
2. Match each medicine name against the `medicines` catalog in the database
3. Fetch current `pharmacy_inventory` for all prescribed medicines
4. Call the LLM with the full prescription, patient allergies/conditions, and inventory status — checks for:
   - Incorrect dosage/route combinations
   - Drug-drug interactions
   - Allergy conflicts
   - Out-of-stock medicines (flags and suggests in-stock alternatives)
5. If `is_valid = true` and no critical warnings: create `prescriptions` record + `prescription_items` records in DB
6. If validation fails: return error details to the doctor dashboard

**Secondary Function:** `generate_prescription_from_consult(consult_data)` — Called by "✨ Auto-Generate Prescription" button. Takes the consultation diagnosis/symptoms and generates an initial medicine list for the doctor to review and edit.

---

### 6.5 Pharmacy Agent (`agents/pharmacy_agent.py`)

**Role:** Manages the prescription-to-dispense pipeline.

**`check_prescription_stock(prescription_id, patient_allergies)`:**
- Iterates each `prescription_item`, queries `pharmacy_inventory` for current `quantity_available`
- Marks each item as `in_stock`, `low_stock`, or `out_of_stock`
- For out-of-stock items: calls LLM with the medicine details and available inventory alternatives → LLM suggests generic/therapeutic substitutes with reasoning
- Updates each `prescription_item.is_in_stock` flag in the database

**`dispense_prescription(prescription_id, pharmacist_id)`:**
- Deducts dispensed quantities from `pharmacy_inventory.quantity_available`
- Updates `prescriptions.status = "dispensed"`
- Creates an `audit_log` entry with `action = "prescription_dispensed"` and the pharmacist's user ID
- Returns success/failure

**`approve_substitute(item_id, alt_medicine_id, pharmacist_id)`:**
- Sets `prescription_item.substitute_approved = True` and records the chosen alternative medicine ID
- Logs the human approval action in `audit_log`

**`generate_medicine_details(medicine_name)`:**
- Called by "✨ Auto-Fill" in the Pharmacy Inventory tab
- Sends the medicine name to the LLM to fetch: generic name, category, use case, strength, dosage form, estimated price

---

### 6.6 Workflow Agent (`agents/workflow_agent.py`)

**Role:** The state machine controller for the entire patient journey.

**Valid State Transitions:**
```
registered → triaged → queued → in_consultation
           ↘        ↘        ↘        ├── investigation_ordered → investigation_complete → in_consultation
                                      ├── prescribed → at_pharmacy → dispensed → billing → discharged
                                      └── billing → discharged
```

**On every `transition_state()` call:**
1. Validates the transition is allowed (rejects invalid jumps)
2. Inserts a new `workflow_states` record with `current_state`, `previous_state`, `transitioned_by`, `transitioned_by_role`, `notes`, and optional `metadata` (e.g., invoice JSON)
3. Syncs the `appointments.status` field (`queued→waiting`, `in_consultation→in_progress`, `discharged→completed`)
4. Creates an `audit_log` entry
5. Sends an in-app notification to the patient with a human-readable status message

---

### 6.7 Notification Agent (`agents/notification_agent.py`)

Inserts records into the `notifications` table. Each state change triggers a tailored message:
- `queued` → "You've been added to the doctor's queue. Please wait for your turn."
- `in_consultation` → "The doctor is ready to see you now!"
- `prescribed` → "Your prescription is ready and has been sent to the pharmacy."
- `dispensed` → "Your medicines are ready for pickup!"
- `discharged` → "Your visit is complete. Thank you for choosing MediFlow!"

---

## 7. LangGraph Orchestrator — The Brain

**File:** `agents/orchestrator.py`

The orchestrator uses LangGraph's `StateGraph` with a **supervisor routing pattern**. Three specialized graphs are compiled at startup (lazy-initialized as module-level singletons).

### Shared State (`MediFlowState` TypedDict)

```python
class MediFlowState(TypedDict):
    messages: list[BaseMessage]      # Conversation history (add_messages reducer)
    action: str                      # "full_intake" | "process_prescription" | "transition_workflow"
    patient_id: str
    patient_user_id: str
    doctor_id: str
    doctor_user_id: str
    appointment_id: str
    consultation_id: str
    prescription_id: str
    symptom_text: str
    patient_age: int
    patient_gender: str
    patient_allergies: list
    patient_conditions: list
    prescription_items: list
    classification_result: dict      # Output of symptom_classifier_node
    queue_result: dict               # Output of queue_manager_node
    prescription_result: dict        # Output of prescription_node
    pharmacy_result: dict            # Output of pharmacy_node
    workflow_result: dict            # Output of workflow_node
    target_workflow_state: str
    transitioned_by: str
    transitioned_by_role: str
    transition_notes: str
    next_step: str                   # "queue_manager" | "pharmacy" | "end"
    error: str
    completed: bool
```

### The Three Graphs

**Graph 1: `intake_graph`**
```
START → symptom_classifier_node → queue_manager_node → END
```
Called by `run_intake_pipeline()`.

**Graph 2: `prescription_graph`**
```
START → prescription_node ──(success)──→ pharmacy_node → END
                          └──(failure)──→ END
```
Called by `run_prescription_pipeline()`.

**Graph 3: `workflow_graph`**
```
START → workflow_node → END
```
Called by `run_workflow_transition()`.

**Special Direct-Call Function: `run_direct_queue_allocation()`**
Used by the intake chat agent. Bypasses the full intake graph — constructs a synthetic pre-classified state and calls `queue_manager_node` directly with the AI triage nurse's output.

---

## 8. The Workflow State Machine

**File:** `agents/workflow_agent.py` (VALID_TRANSITIONS dict) & `config.py` (WORKFLOW_STATES list)

| State | Label | Who Triggers It | How |
|---|---|---|---|
| `registered` | Registered | System | On `assign_queue_token()` |
| `triaged` | Triaged | System/Reception | Optional intermediate |
| `queued` | In Queue | Receptionist | **Confirm Button** in Triage Confirmation tab |
| `in_consultation` | With Doctor | Doctor | **Start Consultation Button** in Patient Queue tab |
| `investigation_ordered` | Investigation | Doctor | Can be triggered from Consultation tab |
| `investigation_complete` | Results Ready | Lab/System | Results returned |
| `prescribed` | Prescribed | Doctor | Prescription submitted via **Submit Prescription Button** |
| `at_pharmacy` | At Pharmacy | System | Triggered after Rx sent to pharmacy |
| `dispensed` | Medicine Dispensed | Pharmacist | **Dispense Button** in Prescription Queue tab |
| `billing` | Billing | Receptionist | Auto-triggered before discharge |
| `discharged` | Discharged | Receptionist | **Settle Bill & Discharge Button** |

The `workflow_tracker.py` component renders this as a horizontal colored progress bar visible on the Patient Portal and in the Reception Workflow Overview.

---

## 9. The Groq LLM Client & Model Fallback

**File:** `agents/llm_client.py`

The `LLMClient` class wraps `langchain-groq`'s `ChatGroq` with an automatic three-level fallback:

```
Attempt 1: openai/gpt-oss-120b  (131K context, fastest)
    │  Rate limit (429) / Model error?
    ↓
Attempt 2: llama-3.3-70b-versatile  (128K context, great quality)
    │  Rate limit / Model error?
    ↓
Attempt 3: llama-3.1-8b-instant  (128K context, lightweight, always available)
    │  All fail?
    ↓
RuntimeError raised → Graceful degradation in each agent
```

**Retry Logic:** On a rate limit error, applies exponential backoff (`2^attempt` seconds). On a model error, immediately skips to the next model. Caches `ChatGroq` instances per `(model_name, temperature)` pair.

**`invoke_json()`:** Appends strict JSON-only instructions to the system prompt before calling `invoke()`, ensuring parseable responses for structured agent outputs.

**Changing Models:** Edit `.env`:
```env
PRIMARY_MODEL=llama-3.3-70b-versatile
FALLBACK_MODEL_1=llama-3.1-8b-instant
FALLBACK_MODEL_2=gemma2-9b-it
```

---

## 10. The Navigation System (Responsive Navbar)

**File:** `components/navbar.py`

The navbar replaces Streamlit's native sidebar entirely (`display: none !important`). It is rendered three times with CSS media queries controlling visibility:

| Layout | Breakpoint | Features |
|---|---|---|
| **Desktop** | > 1100px | Full logo, profile box (avatar + name + role), Refresh button, Sign Out button, all tab buttons in a row |
| **Tablet** | 768–1100px | Same as desktop, slightly narrower columns |
| **Mobile** | < 768px | Logo only + hamburger `☰` button → CSS-animated slide-in right drawer (320px wide) with profile, nav links, Refresh, Sign Out |

**Mobile Drawer Animation:** A JavaScript injection (`components.html`) attaches click handlers to all nav buttons inside the popover, plays a `drawerSlideOut` CSS animation (0.25s), then programmatically clicks the popover toggle button to close it — creating a native app-like feel.

**Role-Based Tab Sets:**
```python
ROLE_TABS = {
    "patient":      ["New Visit", "My Queue", "Prescriptions", "Visit History", "My Profile"],
    "receptionist": ["Live Queue", "Triage Confirmation", "Register Patient", "Search",
                     "Workflow Overview", "Billing & Discharge"],
    "doctor":       ["Patient Queue", "Consultation", "Prescribe", "Patient History", "Settings"],
    "pharmacist":   ["Prescription Queue", "Inventory", "Substitutions", "Dispense"],
    "admin":        ["Analytics", "Doctors", "Users", "Departments", "Audit Trail"]
}
```

**Active Tab State:** Stored in `st.session_state["active_tab"]`. Clicking a tab button calls `st.rerun()`, and each page re-renders the correct content block based on this value.

**Quick Action Bar (below navbar):**
- **Doctors:** Shows a live status dropdown (`available / busy / on_break / offline`) — changes instantly update `doctors.status` in the DB
- **Receptionists:** Shows live "Today's Overview: Waiting: X | Completed: Y"
- **Pharmacists:** Shows a `st.warning()` if any items are below reorder level

---

## 11. Role-Based Dashboards — Complete Button Guide

### Landing Page

The unauthenticated landing page renders trust metrics and two primary actions:

| Button | Action |
|---|---|
| **Log In** | Sets `st.session_state.auth_view = "login"`, reruns to show login form |
| **Sign Up** | Sets `st.session_state.auth_view = "signup"`, reruns to show signup form |
| **Login Form → Login Button** | Calls `sign_in(email, password)` on a fresh Supabase auth client, saves JWT tokens to browser cookies via `save_session_to_cookies()`, sets `_pending_redirect` to role's page |
| **Signup Form → Register Button** | Calls `sign_up(email, password, full_name, role, phone)`. If role is `patient`, immediately calls `db.create_patient()` with a generated `MF-XXXXXXXX` code |
| **"Don't have an account?"** | Switches to signup view |
| **"Already have an account?"** | Switches to login view |

---

### 🏥 Patient Portal (5 Tabs)

**Tab 1: New Visit**

> Entry point: Patient describes symptoms to the AI Triage Nurse

| Control | What it Does |
|---|---|
| **Text input field** | The chat input bar. On `Enter` or clicking `➤`, sets `submitted_text` in session state, triggers AI response generation |
| **`➤` Send Button** | Manually submits the text in the chat input |
| **`➕` Attachment Popover** | Opens a file uploader. Accepts `png`, `jpg`, `jpeg`. The image bytes are base64-encoded and sent to `qwen/qwen3.6-27b` as a vision message alongside the text |
| **`🎤` Voice Mode Button** | Sets `st.session_state.voice_mode = True`, reruns into immersive full-screen voice mode (dark background, pulsing orb, hidden chat messages) |
| **`✖ Exit Voice` Button** | Exits voice mode, clears TTS state, returns to text chat |
| **Voice Orb (voice mode)** | Custom web component — records microphone audio, sends to `transcribe_audio()` via Groq Whisper (`whisper-large-v3`), returns transcript as new user message |
| **AI Response (streaming)** | `st.write_stream()` with `run_intake_chat_stream()` generator — streams text tokens in real time, strips `<think>` blocks |
| **TTS Playback (voice mode)** | After streaming completes, `text_to_speech_auto()` generates audio bytes with `gTTS`, sent back to the voice component for automatic playback |
| **After Completion** | `parse_intake_completion()` detects the JSON block → calls `run_direct_queue_allocation()` → assigns token → shows success |
| **Start New Visit Button** | Clears `intake_messages`, `patient_history_context`, `intake_completed` from session state, reruns to start fresh |

**Tab 2: My Queue**

| Control | What it Does |
|---|---|
| **Queue Card** | Shows token number (e.g., `GEN-007`), doctor name, department, urgency badge, current status |
| **Workflow Tracker** | Horizontal progress bar showing 11 states. Completed states = green. Current = teal highlighted. Pending = gray |
| **"View Detailed Timeline" Expander** | Shows each state transition with timestamp, who performed it, and notes |

**Tab 3: Prescriptions**

| Control | What it Does |
|---|---|
| **Prescription Cards** | Read-only view for each prescription — shows prescription code, prescribing doctor, status badge (color-coded), and all medicine items with dosage, frequency, route, quantity, stock status |

**Tab 4: Visit History**

| Control | What it Does |
|---|---|
| **Visit Expanders** | Each past consultation in a collapsible expander — shows date, doctor, symptoms, diagnosis, examination notes, follow-up date, and vitals as metric cards |

**Tab 5: My Profile**

| Control | What it Does |
|---|---|
| **Patient Intake Form** | Full health profile — date of birth, gender, blood group, allergies, chronic conditions, insurance provider, emergency contact. `Save Profile` button upserts to `patients` table |

---

### 👩‍💼 Reception Dashboard (6 Tabs)

**Tab 1: Live Queue**

| Control | What it Does |
|---|---|
| **4 KPI Metric Cards** | Live counts: Waiting, In Progress, Completed, Total Today — from `db.get_today_stats()` |
| **Filter by Department Dropdown** | Filters `appointments` query by `department_id`. "All Departments" = no filter |
| **Queue Table / Cards** | Shows all today's appointments with token, patient name, urgency, status |
| **Refresh Queue Button** | Calls `st.rerun()` to force re-fetch all data |

**Tab 2: Triage Confirmation**

The most critical human checkpoint in the system.

| Control | What it Does |
|---|---|
| **Appointment Expander** | One card per unconfirmed appointment — shows patient name, symptom summary, AI-recommended department, AI urgency, AI confidence % |
| **"Confirm/Override Department" Dropdown** | Pre-set to the AI's recommendation. Receptionist can select any department from the database |
| **"Confirm/Override Urgency" Dropdown** | Pre-set to the AI's urgency. Options: Routine / Semi-Urgent / Urgent / Emergency |
| **Confirm Button** | Sets `receptionist_confirmed = True`, saves chosen `urgency` and `department_id` to `appointments`. If the department was changed, creates an `audit_log` entry with `was_overridden = True` and records the original vs overridden department. Then calls `transition_state(..., "queued")` — this moves the patient into the active queue |
| **Auto-collapse** | On confirm, `st.rerun()` re-fetches the list — confirmed patients disappear from this tab |

**Tab 3: Register Patient**

| Control | What it Does |
|---|---|
| **Full Name, Email, Phone** | Required fields for the new account |
| **Gender, Blood Group, DOB** | Medical profile data from `constants.py` option lists |
| **Known Allergies** | Comma-separated text; parsed into a list before saving |
| **Chronic Conditions** | Comma-separated text; parsed into a list before saving |
| **Register Patient Button** | Generates a random 10-character temp password. Calls `sign_up()` via Supabase Auth to create the user account. Calls `db.create_patient()` with `MF-XXXXXXXX` code. Displays the patient's temp password on screen for the receptionist to share |

**Tab 4: Search**

| Control | What it Does |
|---|---|
| **Search Text Input** | Real-time search by patient ID (`MF-XXXXXXXX`) or full name via `db.search_patients()` — PostgreSQL `ilike` query |
| **Results** | Each result shows name, patient ID, phone, blood group, allergies |

**Tab 5: Workflow Overview**

| Control | What it Does |
|---|---|
| **State-Grouped View** | For each workflow state (registered, queued, in_consultation, etc.), shows all patients currently in that state |
| **Mini Workflow Tracker** | Each patient shows a compact horizontal progress bar at their current step |

**Tab 6: Billing & Discharge**

| Control | What it Does |
|---|---|
| **"Select Patient to Bill/Discharge" Dropdown** | Lists all active patients who have completed their pharmacy stop. Populated from `db.get_active_appointments_for_billing()` |
| **Invoice Details (auto-calculated)** | Consultation fee from `doctors.consultation_fee` + pharmacy charges (each medicine: quantity × `medicines.unit_price`). Displays line items and grand total |
| **Settle Bill & Discharge Button** | Moves state to `billing` (if not already), then inserts a `discharged` workflow state with the full `invoice` JSON in `metadata`. Updates `appointments.status = "completed"`. Displays confirmation with total amount |

---

### 🩺 Doctor Dashboard (5 Tabs)

**Tab 1: Patient Queue**

| Control | What it Does |
|---|---|
| **3 KPI Metrics** | Waiting / In Progress / Completed counts for today |
| **Current Patient Card** | Shows the patient currently `in_progress` — token number, name, symptom summary excerpt, phone number |
| **Waiting Patients List** | Each row: token, urgency badge, patient name, symptom preview |
| **Start Consultation Button** | Updates `appointments.status = "in_progress"` and `consultation_start_time`. Updates `doctors.status = "busy"`. Calls `transition_state(..., "in_consultation")` → patient's workflow advances. `st.rerun()` refreshes the queue |

**Tab 2: Consultation**

| Control | What it Does |
|---|---|
| **Patient Info Header** | Patient ID, blood group, allergies displayed at top |
| **AI Triage Report Card** | Displays `appointments.symptom_summary` in a highlighted card — the full AI intake nurse summary — so the doctor has complete context before asking the first question |
| **Vitals Form** | 6 input fields: Blood Pressure, Temperature (°F), Pulse (bpm), SpO2 (%), Weight (kg), Height (cm). Stored as JSON in `consultations.vitals` |
| **Symptoms / Chief Complaint** | Pre-filled with the AI triage summary. Doctor edits as needed |
| **Examination Notes** | Free text field for physical exam findings |
| **Diagnosis** | Single-line field for the primary diagnosis |
| **Additional Notes** | Extra observations, recommendations, warnings |
| **Follow-up Date** | Optional date picker |
| **Follow-up Instructions** | Free text for follow-up instructions |
| **✨ AI Auto-Fill Clinical Notes Button** | Calls `generate_clinical_notes_from_triage(triage_summary, vitals, patient_info)`. The LLM generates a draft of `{symptoms, examination_notes, diagnosis, additional_notes}` based on the triage report and current vitals. Results placed in `st.session_state.temp_ai_notes` and applied to form fields on rerun |
| **Save Consultation Button** | Calls `db.create_consultation()` (or `db.update_consultation()` if one already exists for this appointment). Stores all form data in the `consultations` table |
| **Complete Consultation & Discharge Button** | Outside the form. Calls `db.update_appointment(status="completed")`, `db.update_doctor_status("available")`, and `transition_state(..., "discharged")`. Bypasses the pharmacy pipeline entirely — for cases with no prescription |

**Tab 3: Prescribe**

| Control | What it Does |
|---|---|
| **✨ Auto-Generate Prescription Button** | Calls `generate_prescription_from_consult(consult_data)`. LLM analyzes the diagnosis and symptoms, generates an initial list of suggested medicines. Appended to `st.session_state.prescription_items` |
| **"Add Medicine" Expander** | Expanded by default. Contains the full medicine entry form |
| **Medicine Name Dropdown** | Populated from `db.get_all_medicines()`. Allows selecting from the hospital's catalog OR typing a custom name |
| **Dosage Field** | Free text: "500mg", "10ml", etc. |
| **Frequency Dropdown** | 13 options: OD, BD, TDS, QDS, SOS, etc. (from `constants.DOSAGE_FREQUENCIES`) |
| **Route Dropdown** | 11 options: Oral, Topical, IV, IM, Inhalation, etc. (from `constants.MEDICINE_ROUTES`) |
| **Duration** | Number input (1–∞) + unit dropdown (days/weeks/months) |
| **Quantity** | Number of tablets/units to dispense |
| **Special Instructions** | Free text: "Take after meals", "Avoid sunlight" |
| **Add to Prescription Button** | Appends the item to `st.session_state.prescription_items`, clears the form fields |
| **Edit Button** (per item) | Populates the form with that item's data for editing. Becomes "Editing..." (disabled) while active |
| **Remove Button** (per item) | Removes the item from the list. Adjusts edit index if needed |
| **Clear All Button** | Clears `st.session_state.prescription_items` entirely |
| **Submit Prescription Button** | Calls `handle_prescription_submit(items)` → calls `run_prescription_pipeline()` → LangGraph: `prescription_node` (AI validation) → `pharmacy_node` (stock check). On success: shows prescription code, clears form, shows stock status, calls `transition_state(..., "prescribed")` |

**Tab 4: Patient History**

| Control | What it Does |
|---|---|
| **Search Input** | Search by patient ID or name via `db.search_patients()` |
| **Search Button** | Triggers search query |
| **Result Expanders** | Each patient: allergies, conditions, and last 5 consultation records (date, doctor, diagnosis) in nested expanders |

**Tab 5: Settings**

| Control | What it Does |
|---|---|
| **Profile Display** | Shows: Department, Specialization, Qualification, Experience, Max Daily Patients, Consultation Fee, License Number (read-only) |
| **Set Status Dropdown** | `on_change` callback — immediately calls `db.update_doctor_status()` on selection. Options: Available, Busy, On Break, Offline. This directly affects queue manager routing (only "available" doctors get new patients assigned) |

---

### 💊 Pharmacy Dashboard (4 Tabs)

**Tab 1: Prescription Queue**

| Control | What it Does |
|---|---|
| **Prescription Count Banner** | Shows count of pending prescriptions |
| **Prescription Expander** (per Rx) | Shows: patient name/ID/phone, prescribing doctor, date, prescription code, all medicine items with stock status badges (`[In Stock]` / `[Out of Stock]` / `[Unchecked]`) |
| **Check Stock Button** | Calls `check_prescription_stock(rx_id)` → Pharmacy Agent queries live inventory for each item, updates `prescription_items.is_in_stock` in DB. Shows per-item `[OK]` or `[LOW/OUT]` with available vs required quantities. If any out of stock → alert to check Substitutions tab |
| **Dispense Button** | Calls `dispense_prescription(rx_id, pharmacist_id)` → deducts quantities from `pharmacy_inventory`, sets `prescriptions.status = "dispensed"`, logs in `audit_log`. Calls `transition_state(..., "dispensed")`. On success: `st.rerun()` removes the Rx from the queue |

**Tab 2: Inventory**

| Control | What it Does |
|---|---|
| **2 KPI Cards** | Low Stock Items count (red) + Total Products count (teal) |
| **Search Input** | Client-side filter — `if search.lower() not in med_name.lower(): continue` |
| **Inventory Rows** | Each row: medicine name + strength, category + dosage form, Use Case (highlighted in blue if present), current quantity (color-coded: red=0, amber=low, green=ok), selling price |
| **Update Qty Number Input** | Inline number input per item. Shows current quantity as default |
| **Update Button** | Appears only when the number input differs from current quantity. Calls `db.update_inventory(inv_id, {"quantity_available": new_qty})` |
| **"Add New Medicine to Catalog" Expander** | |
| **Medicine Name Input** | Name for AI auto-fill or manual entry |
| **✨ Auto-Fill Button** | Calls `generate_medicine_details(search_name)` → LLM returns generic name, category, use case, strength, dosage form, estimated price. Populates all session state variables, triggers rerun to fill the form |
| **Add Medicine Form** | Medicine Name, Generic Name, Category, Use Case (optional), Dosage Form (10 options), Strength, Unit Price (₹) |
| **Add Medicine Button** | Creates medicine in `medicines` table. Category + Use Case concatenated as `"Category \| Use Case: ..."` for parsing |

**Tab 3: Substitutions**

| Control | What it Does |
|---|---|
| **Out-of-Stock Item Cards** | Shows each `prescription_item` where `is_in_stock = False` and `substitute_approved = False` |
| **Available Alternatives List** | Fetches from `db.get_medicine_alternatives(medicine_id)` — medicines in the same generic family. Shows each alternative with its current stock quantity |
| **Approve Button** (per alternative) | Calls `approve_substitute(item_id, alt_medicine_id, pharmacist_id)` — sets `substitute_approved = True` on the `prescription_item`, logs the human approval in `audit_log` |

**Tab 4: Dispense (History)**

| Control | What it Does |
|---|---|
| **Dispensing History** | Reads `audit_log` filtered by `entity_type = "prescription"` and `action = "prescription_dispensed"`. Shows timestamp, pharmacist name, and truncated Rx ID |

---

### 📊 Admin Dashboard (5 Tabs)

**Tab 1: Analytics**

| Control | What it Does |
|---|---|
| **KPI Row 1** | `render_kpi_row(stats)` — Today's stats from `db.get_today_stats()`: Total Patients, Consultations, Prescriptions, Revenue (estimated) |
| **KPI Row 2** | `render_kpi_row_extended(stats)` — Waiting Patients, In Progress, Avg Wait Time, etc. |
| **Department Load Chart** | `render_department_load_chart(today_appts)` — Plotly horizontal bar chart: appointment count per department |
| **Urgency Pie Chart** | `render_urgency_pie_chart(today_appts)` — Plotly donut: routine / semi-urgent / urgent / emergency distribution |
| **Status Pie Chart** | `render_status_pie_chart(today_appts)` — Plotly donut: waiting / in_progress / completed |
| **Doctor Workload Chart** | `render_doctor_workload_chart(doctors)` — Plotly bar: `current_token / max_daily_patients` per doctor |
| **Refresh Analytics Button** | Calls `st.rerun()` to reload all stats and charts |

**Tab 2: Doctors**

| Control | What it Does |
|---|---|
| **Doctor List** | Each doctor row: name, specialization/qualification, department, experience + fee, current status, patient load (`current_token/max_daily_patients`) |
| **"Register New Doctor" Expander** | |
| **Select User Dropdown** | Populated from `db.get_users_by_role("doctor")` — only users with role `doctor` who don't already have a `doctors` record |
| **Department Dropdown** | All active departments from `db.get_all_departments()` |
| **Specialization, Qualification, Experience, License, Fee, Max Patients** | Doctor profile fields |
| **Register Doctor Button** | Calls `db.create_doctor({user_id, department_id, ...})` — creates the `doctors` record linking the user to a department |

**Tab 3: Users**

| Control | What it Does |
|---|---|
| **5 Role Metric Cards** | Count per role: patient, doctor, receptionist, pharmacist, admin |
| **Filter by Role Dropdown** | Client-side filter over `db.get_all_users()` |
| **User List** | Each row: name, email, phone, role badge, active/inactive status |

**Tab 4: Departments**

| Control | What it Does |
|---|---|
| **Department List** | Each row: name, description, floor number, active/inactive status |

**Tab 5: Audit Trail**

| Control | What it Does |
|---|---|
| **Filter by Entity Dropdown** | Options: All, appointment, prescription, prescription_item, workflow — filters `db.get_audit_log(limit=100, entity_type)` |
| **Audit Entries** | Each entry: action name, timestamp, actor name + role, entity type, AI model used (if applicable), AI confidence score (if applicable). `[OVERRIDE]` badge appears prominently when `was_overridden = True` |
| **"Details" Expander** | Shows the raw `details` JSON for the audit entry (e.g., `{from_state, to_state, notes}` or `{ai_recommended, overridden_to}`) |
| **Override Reason** | If `override_reason` is set, displayed as `st.warning()` |

---

## 12. Complete End-to-End Workflow (Patient Journey)

```
STEP 1 — REGISTRATION
Patient visits app.py → landing page → Sign Up
  └── Supabase Auth creates user + patient record (MF-XXXXXXXX)

STEP 2 — AI TRIAGE (Patient Portal → "New Visit")
Patient types/speaks/uploads symptoms to AI Triage Nurse
  └── qwen/qwen3.6-27b streams a response (5–6 clarifying questions max)
  └── On completion: outputs JSON {department, urgency, patient_report}
  └── run_direct_queue_allocation():
        └── queue_manager_node():
              └── find_best_doctor(department, urgency) → available doctor with shortest queue
              └── assign_queue_token() → atomically increment doctor.current_token
              └── Create appointments record (status=waiting, receptionist_confirmed=False)
              └── Create workflow_states record (registered)
              └── Notify patient: "You've been added to the queue"

STEP 3 — TRIAGE CONFIRMATION (Reception → "Triage Confirmation")
Receptionist sees appointment with [AI: Cardiology | Urgent | 87% confidence]
  └── Can override department or urgency using dropdowns
  └── Clicks "Confirm":
        └── appointments.receptionist_confirmed = True
        └── If department changed → audit_log entry (was_overridden=True)
        └── transition_state(appointment_id, patient_id, "queued")
              └── workflow_states: registered → queued
              └── appointments.status = "waiting"
              └── Notify patient: "You've been added to the doctor's queue"

STEP 4 — CONSULTATION (Doctor → "Patient Queue")
Doctor sees patient in Waiting list
  └── Clicks "Start Consultation":
        └── appointments.status = "in_progress"
        └── doctors.status = "busy"
        └── transition_state(..., "in_consultation")
        └── Notify patient: "The doctor is ready to see you now!"

Doctor → "Consultation" tab:
  └── AI Triage Report visible
  └── Optionally clicks "✨ AI Auto-Fill Clinical Notes" → LLM drafts notes
  └── Enters/edits vitals + symptoms + examination + diagnosis + follow-up
  └── Clicks "Save Consultation" → db.create_consultation() or update_consultation()

STEP 5 — PRESCRIPTION (Doctor → "Prescribe")
  └── Optionally clicks "✨ Auto-Generate Prescription" → LLM suggests medicines
  └── Adds/edits/removes medicine items
  └── Clicks "Submit Prescription":
        └── run_prescription_pipeline():
              └── prescription_node:
                    └── Generate RX-XXXXXXXXXX code
                    └── AI validation (interactions, allergies, dosage correctness)
                    └── db.create_prescription() + create_prescription_items()
                    └── send_to_pharmacy(prescription_id)
              └── pharmacy_node:
                    └── check_prescription_stock() → flag each item in/out of stock
                    └── If out of stock → LLM suggests alternatives
        └── transition_state(..., "prescribed")
        └── Notify patient: "Your prescription has been sent to the pharmacy"

STEP 6 — PHARMACY (Pharmacist → "Prescription Queue")
Pharmacist sees incoming Rx
  └── Clicks "Check Stock":
        └── pharmacy_agent.check_prescription_stock() → updates is_in_stock per item
        └── Shows [OK] / [LOW/OUT] for each item
  └── If items out of stock → goes to "Substitutions" tab:
        └── Reviews AI-suggested alternatives (in-stock only shown)
        └── Clicks "Approve" → approve_substitute() → audit_log (human approval recorded)
  └── Clicks "Dispense":
        └── dispense_prescription():
              └── Deducts qty from pharmacy_inventory
              └── prescriptions.status = "dispensed"
              └── audit_log (action: prescription_dispensed)
        └── transition_state(..., "dispensed")
        └── Notify patient: "Your medicines are ready for pickup!"

STEP 7 — BILLING & DISCHARGE (Reception → "Billing & Discharge")
Receptionist selects patient
  └── Invoice auto-calculated: consultation_fee + (qty × unit_price per medicine)
  └── Clicks "Settle Bill & Discharge":
        └── transition_state(..., "billing")
        └── Create workflow_state "discharged" with invoice JSON in metadata
        └── appointments.status = "completed"
        └── Notify patient: "Your visit is complete. Thank you for choosing MediFlow!"
```

---

## 13. Safety, Compliance & Human Checkpoints

### Three Non-Negotiable Human Approval Gates

1. **Triage Confirmation (Reception):** No patient enters a doctor's queue without a human receptionist reviewing and confirming the AI's department/urgency recommendation. Overrides are logged with `was_overridden = True`.

2. **Drug Substitution (Pharmacist):** AI-suggested medicine alternatives are **never applied automatically**. Each alternative requires a pharmacist's explicit "Approve" button click, which is logged in the audit trail.

3. **Emergency Red Flag Detection:** Before the LLM call, a fast keyword scan checks for 14 critical symptoms (chest pain, stroke, seizure, anaphylaxis, severe bleeding, etc.). If detected, `urgency_level` is forced to `"emergency"` regardless of the LLM's output.

### Complete Audit Trail
The `audit_log` table records:
- Every AI decision: model name, confidence score, input/output details
- Every human override: original AI recommendation, what it was changed to
- Every workflow transition: from_state, to_state, who did it, timestamp
- Every prescription dispensed: pharmacist ID, timestamp

### Data Privacy
- Supabase RLS ensures strict data isolation between roles
- Service role key is only used server-side (never in browser)
- All credentials in environment variables (never hardcoded)
- Patient data sent to Groq only for triage purposes — clearly scoped

---

## 14. Configuration & Environment Variables

**File:** `config.py` — All loaded from `.env` via `python-dotenv` with `override=True`.

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | — | Required. All AI features fail without this |
| `PRIMARY_MODEL` | `openai/gpt-oss-120b` | First model in fallback chain |
| `FALLBACK_MODEL_1` | `llama-3.3-70b-versatile` | Second in chain |
| `FALLBACK_MODEL_2` | `llama-3.1-8b-instant` | Third (always available) |
| `SUPABASE_URL` | — | Your Supabase project URL |
| `SUPABASE_KEY` | — | Supabase anon key (public) |
| `SUPABASE_SERVICE_KEY` | — | Supabase service role key (server-only) |

**Also configurable in `config.py`:**
- `DEPARTMENTS` list (15 departments including Emergency)
- `URGENCY_LEVELS` with color codes and priority scores
- `WORKFLOW_STATES` list (11 states)
- `RED_FLAG_SYMPTOMS` list (14 critical symptoms)
- `SLOT_DURATION_MINUTES` (default 15) — used for wait time estimation
- `MAX_QUEUE_SIZE` (default 50)
- `WORKING_HOURS_START/END` (8 AM – 8 PM)

---

## 15. Getting Started

### Prerequisites
- Python 3.9+
- Supabase account with a project
- Groq API key (free tier sufficient for development)

### Installation

```bash
git clone https://github.com/Coding-Philic/hospital-ecosystem.git
cd "hospital ecosystem"

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Environment Setup

Create `.env` in the project root:

```env
# AI Models
GROQ_API_KEY=your_groq_api_key_here
PRIMARY_MODEL=openai/gpt-oss-120b
FALLBACK_MODEL_1=llama-3.3-70b-versatile
FALLBACK_MODEL_2=llama-3.1-8b-instant

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
```

Alternatively, use `.streamlit/secrets.toml` for Streamlit Cloud deployment:
```toml
[groq]
GROQ_API_KEY = "..."

[supabase]
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
SUPABASE_SERVICE_KEY = "..."
```

### Database Setup

Run the provided `setup_database.sql` in your Supabase SQL Editor to create all 13 tables, configure RLS policies, and insert seed data (15 departments, 20 medicines, sample users).

### Run

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Streamlit Cloud Deployment
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the entry point
4. Add secrets in the Streamlit Cloud dashboard
5. Deploy

> ⚠️ **Security Warning:** Never commit your `.env` file. If you accidentally push API keys or the Supabase Service Role key to GitHub, immediately rotate them in your provider dashboards.

---

*MediFlow AI v1.0.0 — Built for the future of healthcare.*
