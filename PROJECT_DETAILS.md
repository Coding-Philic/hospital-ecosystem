# MediFlow AI — Complete Project Details

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Database Schema](#database-schema)
5. [AI Agent Pipelines](#ai-agent-pipelines)
6. [LangGraph Orchestrator](#langgraph-orchestrator)
7. [Dashboard Features](#dashboard-features)
8. [Model Switching Guide](#model-switching-guide)
9. [API Reference](#api-reference)
10. [Deployment Guide](#deployment-guide)
11. [Safety & Compliance](#safety--compliance)

---

## 1. Project Overview

**MediFlow AI** is a multi-agent, AI-orchestrated hospital platform that connects patients, doctors, receptionists, and pharmacists into a single digital workflow. It replaces three broken manual processes:

| Problem | Solution |
|---------|----------|
| Blind Queue — patients wait randomly | AI symptom classification → smart doctor matching → queue token |
| Prescription-Pharmacy Gap — stock-outs | Auto-pharmacy routing + AI alternative suggestions |
| Paper-based Intake — lost records | Digital intake + workflow state machine with audit trail |

### Core Design Principle
> **AI recommends, licensed humans decide.** No AI output (symptom classification, drug substitution) reaches a patient without a human confirmation step.

---

## 2. Architecture

```
┌─────────────────────────────────────────┐
│            Streamlit Frontend            │
│  (5 Role-Based Dashboards + Auth)        │
├─────────────────────────────────────────┤
│          UI Components Layer             │
│  (Auth, Sidebar, Forms, Charts, etc.)    │
├─────────────────────────────────────────┤
│      LangGraph Orchestrator (Supervisor) │
│  ┌──────────┬──────────┬──────────────┐ │
│  │ Pipeline A│ Pipeline B│ Pipeline C  │ │
│  │ Symptom→  │ Rx→      │ Workflow    │ │
│  │ Queue     │ Pharmacy │ State Mach. │ │
│  └──────────┴──────────┴──────────────┘ │
├─────────────────────────────────────────┤
│           Agent Layer                    │
│  Symptom Classifier | Queue Manager     │
│  Prescription Agent | Pharmacy Agent    │
│  Workflow Agent     | Notification Agent│
├─────────────────────────────────────────┤
│         Groq LLM Client                 │
│  (Model Fallback Chain)                  │
│  openai/gpt-oss-120b → llama-3.3-70b   │
│  → llama-3.1-8b-instant                 │
├─────────────────────────────────────────┤
│     Database Layer (Supabase Client)     │
│  CRUD Operations | Pydantic Models       │
├─────────────────────────────────────────┤
│     Supabase PostgreSQL + Auth           │
│  13 Tables | RLS Policies | Seed Data    │
└─────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | **Streamlit** | Multi-page web app with role-based dashboards |
| Orchestration | **LangGraph** (StateGraph) | Multi-agent workflow orchestration (supervisor pattern) |
| AI / LLM | **Groq API** via `langchain-groq` | Symptom classification, prescription validation, alternative suggestions |
| Primary Model | `openai/gpt-oss-120b` | 131K context window, fast inference |
| Database | **Supabase PostgreSQL** | Relational database with Row-Level Security |
| Auth | **Supabase Auth** | Email/password authentication with role management |
| Validation | **Pydantic** | Input/output data validation |
| Charts | **Plotly** | Interactive analytics visualizations |
| Styling | Custom CSS | Dark theme with Inter font, gradients, glassmorphism |

---

## 4. Database Schema

### Tables (13 total)

| Table | Records | Purpose |
|-------|---------|---------|
| `users` | Auth-linked profiles | All users with role enum |
| `departments` | 15 pre-seeded | Hospital departments |
| `doctors` | Doctor profiles | Linked to users + departments, availability status |
| `patients` | Patient records | Medical history, allergies, insurance, permanent digital record |
| `appointments` | Queue tokens | Token number, position, urgency, AI classification results |
| `consultations` | Clinical records | Symptoms, vitals, diagnosis, examination notes |
| `medicines` | 20 pre-seeded | Medicine catalog with generic alternatives |
| `prescriptions` | Digital Rx | Linked to consultations, status tracking |
| `prescription_items` | Rx line items | Individual medicines with stock status |
| `pharmacy_inventory` | Stock levels | Batch, quantity, expiry, reorder levels |
| `workflow_states` | State transitions | Complete patient journey audit trail |
| `audit_log` | All actions | AI decisions, human overrides, timestamps |
| `notifications` | In-app alerts | Queue updates, Rx ready, pharmacy ready |

### Key Relationships
```
users ─┬── doctors ──── departments
       ├── patients
       └── notifications

patients ─── appointments ──┬── consultations ──── prescriptions ──── prescription_items
                            └── workflow_states

medicines ──── pharmacy_inventory
medicines ──── prescription_items
```

### Row-Level Security (RLS)
- **Patients** see only their own data
- **Doctors** see their patients + all departments
- **Receptionists** see all patients and appointments
- **Pharmacists** see prescriptions and inventory
- **Admins** see everything including audit log

---

## 5. AI Agent Pipelines

### Pipeline A — Smart Intake & Queue (Problems 1 & 3)
```
Patient describes symptoms (text)
    ↓
Symptom Classifier Agent (Groq LLM)
    ├── Analyzes symptoms with medical context
    ├── Red-flag detection (emergency bypass)
    ├── Returns: department, urgency, confidence
    └── Graceful degradation if AI fails
    ↓
Queue Manager Agent (Database)
    ├── Finds available doctors in department
    ├── Sorts by shortest queue
    ├── Assigns token number
    └── Estimates wait time
    ↓
Reception confirms AI recommendation (Human checkpoint)
    ↓
Patient gets queue token + live tracking
```

### Pipeline B — Prescription-to-Pharmacy (Problem 2)
```
Doctor writes structured prescription
    ↓
Prescription Agent (Groq LLM + DB)
    ├── Validates medicines against catalog
    ├── AI checks drug interactions, allergies
    └── Creates digital prescription
    ↓
Pharmacy Agent (DB + Groq LLM)
    ├── Checks each item against live inventory
    ├── In stock → auto-routes to pharmacy
    ├── Out of stock → AI suggests alternatives
    └── Alternatives flagged for pharmacist approval
    ↓
Pharmacist approves/rejects (Human checkpoint)
    ↓
Patient picks up medicine (single trip)
```

### Pipeline C — Digital Workflow (Problem 3)
```
State Machine: registered → triaged → queued → in_consultation
    → investigation_ordered → investigation_complete
    → prescribed → at_pharmacy → dispensed → billing → discharged

Each transition:
    ├── Validated (only allowed transitions proceed)
    ├── Logged with timestamp + responsible person
    ├── Triggers patient notification
    └── Recorded in audit trail
```

---

## 6. LangGraph Orchestrator

The orchestrator uses LangGraph's **StateGraph** with a **supervisor pattern**:

### Shared State (`MediFlowState`)
```python
class MediFlowState(TypedDict):
    messages: list[BaseMessage]    # Conversation history
    action: str                     # Current action
    patient_id: str                 # Patient context
    classification_result: dict     # Symptom AI output
    queue_result: dict              # Queue assignment output
    prescription_result: dict       # Prescription output
    pharmacy_result: dict           # Stock check output
    next_step: str                  # Routing control
```

### Pre-built Graphs
| Graph | Nodes | Use Case |
|-------|-------|----------|
| `intake_graph` | symptom_classifier → queue_manager | New patient visit |
| `prescription_graph` | prescription → pharmacy | Doctor writes Rx |
| `workflow_graph` | workflow | State transitions |
| `main_orchestrator` | All 5 nodes | Full pipeline (future) |

### Public API
```python
from agents.orchestrator import run_intake_pipeline, run_prescription_pipeline, run_workflow_transition

# Patient submits symptoms
result = run_intake_pipeline(symptom_text="headache for 3 days", patient_id="...")

# Doctor creates prescription
result = run_prescription_pipeline(consultation_id="...", items=[...])

# Receptionist transitions workflow
result = run_workflow_transition(appointment_id="...", target_state="triaged")
```

---

## 7. Dashboard Features

### 🏥 Patient Portal (5 tabs)
1. **New Visit** — Symptom input → AI analysis → queue token
2. **My Queue** — Live position tracking with workflow progress bar
3. **Prescriptions** — Complete prescription history with stock status
4. **Visit History** — Past consultations with diagnoses
5. **My Profile** — Intake form management

### 👩‍⚕️ Reception Dashboard (5 tabs)
1. **Live Queue** — Real-time queue with KPI metrics
2. **Triage Confirmation** — Approve/override AI department recommendations
3. **Register Patient** — Walk-in patient registration
4. **Search** — Patient lookup by ID or name
5. **Workflow Overview** — All patients grouped by current state

### 🩺 Doctor Dashboard (5 tabs)
1. **Patient Queue** — Pre-triaged list with "Start Consultation" buttons
2. **Consultation** — Vitals entry, diagnosis, examination notes
3. **Prescribe** — Structured Rx entry with AI drug interaction check
4. **Patient History** — Lookup any patient's history
5. **Settings** — Availability toggle, profile info

### 💊 Pharmacy Dashboard (4 tabs)
1. **Prescription Queue** — Incoming Rx with stock check + dispense
2. **Inventory** — Full stock management with inline editing
3. **Substitution Review** — Approve/reject AI-suggested alternatives
4. **Dispensing History** — Audit trail of dispensed medicines

### 📊 Admin Dashboard (5 tabs)
1. **Analytics** — KPIs, department load chart, urgency pie, doctor workload
2. **Doctors** — Doctor management + registration
3. **Users** — All user management with role filter
4. **Departments** — Department overview
5. **Audit Trail** — Complete filterable log of all actions

---

## 8. Model Switching Guide

### ⚠️ IMPORTANT — Read this when switching models

The system is designed with **automatic model fallback**. If the primary model hits rate limits, it automatically tries the next model.

### Current Model Chain
```
1. openai/gpt-oss-120b (Primary — 131K context, fastest)
2. llama-3.3-70b-versatile (Fallback 1 — good quality)
3. llama-3.1-8b-instant (Fallback 2 — always available)
```

### How to Change Models

**Method 1: Environment Variable (recommended)**
Edit `.env`:
```
PRIMARY_MODEL=your-new-model-name
FALLBACK_MODEL_1=another-model
FALLBACK_MODEL_2=yet-another-model
```

**Method 2: Config File**
Edit `config.py` → `Config.MODEL_CHAIN` list.

### When Model Limits Are Hit
1. The system **automatically** falls back to the next model
2. It logs which model was used (visible in audit trail)
3. You see no disruption — the fallback is seamless
4. If ALL models fail, the system **gracefully degrades**:
   - Symptom classification → defaults to "General Medicine" + "routine"
   - Prescription validation → skipped (marked as "manual review needed")
   - Alternative suggestions → database-only (no AI suggestions)

### Available Groq Models (as of 2025)
| Model | Context Window | Speed | Notes |
|-------|---------------|-------|-------|
| `openai/gpt-oss-120b` | 131K | Very fast | Primary choice |
| `llama-3.3-70b-versatile` | 128K | Fast | Great general purpose |
| `llama-3.1-8b-instant` | 128K | Fastest | Lighter, always available |
| `mixtral-8x7b-32768` | 32K | Fast | Good alternative |
| `gemma2-9b-it` | 8K | Fast | Lightweight |

### Testing Model Availability
```python
import requests
import os

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
response = requests.get(url, headers=headers)
print(response.json())
```

---

## 9. API Reference

### Agent Functions

| Function | Input | Output | Used By |
|----------|-------|--------|---------|
| `classify_symptoms(text, age, gender, allergies, conditions)` | Symptom text | `{department, urgency, confidence, reasoning}` | Patient Portal |
| `find_best_doctor(department, urgency)` | Department name | `{doctor_id, name, queue_position, wait}` | Queue Manager |
| `assign_queue_token(patient_id, doctor_id, ...)` | IDs + context | `{token, position, wait}` | Patient Portal |
| `process_prescription(consultation_id, items, ...)` | Items list | `{prescription_code, validation}` | Doctor Dashboard |
| `check_prescription_stock(prescription_id)` | Rx ID | `{all_in_stock, items[]}` | Pharmacy Dashboard |
| `dispense_prescription(prescription_id, pharmacist_id)` | IDs | `{success}` | Pharmacy Dashboard |
| `transition_state(appointment_id, patient_id, new_state)` | State | `{success, from, to}` | All Dashboards |

### Database Queries (queries.py)
- **Departments**: `get_all_departments()`, `get_department_by_name(name)`
- **Users**: `get_user_profile(id)`, `get_users_by_role(role)`
- **Doctors**: `get_available_doctors(dept_id)`, `update_doctor_status(id, status)`
- **Patients**: `get_patient_by_user_id(id)`, `search_patients(term)`
- **Appointments**: `get_today_appointments(dept_id)`, `get_queue_position(doctor_id)`
- **Consultations**: `create_consultation(data)`, `get_consultations_by_patient(id)`
- **Prescriptions**: `get_pending_prescriptions()`, `update_prescription(id, data)`
- **Inventory**: `get_pharmacy_inventory()`, `check_medicine_stock(id)`
- **Workflow**: `get_workflow_history(appt_id)`, `get_current_workflow_state(appt_id)`
- **Audit**: `get_audit_log(limit, entity_type)`
- **Notifications**: `get_notifications(user_id)`, `get_unread_count(user_id)`
- **Analytics**: `get_today_stats()`

---

## 10. Deployment Guide

### Local Development
```bash
streamlit run app.py
```

### Production Deployment (Streamlit Cloud)
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Set secrets in Streamlit Cloud dashboard (same as `.streamlit/secrets.toml`)
5. Deploy

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

---

## 11. Safety & Compliance

### Human Checkpoints (Non-Negotiable)
1. **Symptom triage** → Receptionist confirms before token is finalized
2. **Drug substitution** → Pharmacist/doctor approves before dispensing
3. **Emergency red flags** → Bypass queue automatically, alert all staff

### Audit Trail
- Every AI decision is logged with model name + confidence score
- Every human override is logged with reason
- Complete workflow state history with timestamps

### Data Privacy
- Supabase RLS ensures data isolation between roles
- Service role key used only server-side (never exposed)
- Environment variables for all sensitive credentials
- No patient data is sent to external services beyond Groq (for AI)

### Graceful Degradation
- If AI fails → defaults to standard routing (never guesses)
- If database fails → clear error messages (never silent failures)
- If model rate-limited → automatic fallback chain (3 models deep)
