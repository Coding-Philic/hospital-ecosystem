"""
MediFlow AI — LangGraph Orchestrator (Supervisor Pattern)
==========================================================
The central brain of MediFlow AI. Uses LangGraph's StateGraph to
orchestrate all agents through a supervisor pattern.

Architecture:
  Orchestrator (Supervisor)
    ├── Symptom Classifier Agent
    ├── Queue Manager Agent
    ├── Prescription Agent
    ├── Pharmacy Agent
    ├── Workflow Agent
    └── Notification Agent

The supervisor decides which agent to invoke based on the current
workflow state and user action.
"""

import logging
from typing import Annotated, TypedDict, Optional, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from agents.symptom_classifier import classify_symptoms
from agents.queue_manager import find_best_doctor, assign_queue_token
from agents.prescription_agent import process_prescription, send_to_pharmacy
from agents.pharmacy_agent import check_prescription_stock, dispense_prescription
from agents.workflow_agent import transition_state
from agents.notification_agent import notify_user

logger = logging.getLogger(__name__)


# ╔══════════════════════════════════════════════════════════╗
# ║  SHARED STATE                                             ║
# ╚══════════════════════════════════════════════════════════╝

class MediFlowState(TypedDict):
    """Shared state for the MediFlow AI agent pipeline."""
    messages: Annotated[list[BaseMessage], add_messages]

    # Action context
    action: str                        # Current action to perform
    patient_id: Optional[str]          # Patient record ID
    patient_user_id: Optional[str]     # Patient's auth user ID
    doctor_user_id: Optional[str]      # Doctor's auth user ID
    appointment_id: Optional[str]      # Current appointment ID
    doctor_id: Optional[str]           # Assigned doctor ID
    consultation_id: Optional[str]     # Current consultation ID
    prescription_id: Optional[str]     # Current prescription ID

    # Patient context
    symptom_text: Optional[str]
    patient_age: Optional[int]
    patient_gender: Optional[str]
    patient_allergies: Optional[list]
    patient_conditions: Optional[list]

    # Agent outputs
    classification_result: Optional[dict]
    queue_result: Optional[dict]
    prescription_result: Optional[dict]
    pharmacy_result: Optional[dict]
    workflow_result: Optional[dict]

    # Prescription items (for doctor submission)
    prescription_items: Optional[list]

    # Workflow
    current_workflow_state: Optional[str]
    target_workflow_state: Optional[str]
    transitioned_by: Optional[str]
    transitioned_by_role: Optional[str]
    transition_notes: Optional[str]

    # Control flow
    next_step: Optional[str]           # Which agent to invoke next
    error: Optional[str]
    completed: bool


# ╔══════════════════════════════════════════════════════════╗
# ║  AGENT NODES                                              ║
# ╚══════════════════════════════════════════════════════════╝

def symptom_classifier_node(state: MediFlowState) -> dict:
    """Node: Classify patient symptoms."""
    try:
        result = classify_symptoms(
            symptom_text=state.get("symptom_text", ""),
            patient_age=state.get("patient_age"),
            patient_gender=state.get("patient_gender"),
            allergies=state.get("patient_allergies"),
            chronic_conditions=state.get("patient_conditions"),
        )

        return {
            "classification_result": result,
            "messages": [AIMessage(content=(
                f"Symptom Analysis Complete:\n"
                f"• Department: {result['recommended_department']}\n"
                f"• Urgency: {result['urgency_level']}\n"
                f"• Confidence: {result['confidence_score']:.0%}\n"
                f"• Emergency: {'YES ⚠️' if result['is_emergency'] else 'No'}\n"
                f"• Reasoning: {result['reasoning']}"
            ))],
            "next_step": "queue_manager",
        }
    except Exception as e:
        logger.error(f"Symptom classifier node error: {e}")
        return {
            "error": str(e),
            "messages": [AIMessage(content=f"Symptom classification failed: {e}")],
            "next_step": "end",
        }


def queue_manager_node(state: MediFlowState) -> dict:
    """Node: Find best doctor and assign queue token."""
    try:
        classification = state.get("classification_result", {})
        department = classification.get("recommended_department", "General Medicine")
        urgency = classification.get("urgency_level", "routine")

        # Find best doctor
        doctor = find_best_doctor(department, urgency)

        if not doctor:
            return {
                "queue_result": {"success": False, "message": "No doctors available."},
                "messages": [AIMessage(content=(
                    f"⚠️ No doctors currently available in {department}. "
                    "Please check with reception for assistance."
                ))],
                "next_step": "end",
            }

        # Assign queue token
        patient_id = state.get("patient_id")
        if patient_id:
            queue = assign_queue_token(
                patient_id=patient_id,
                doctor_id=doctor["doctor_id"],
                department_id=doctor["department_id"],
                urgency=urgency,
                symptom_summary=state.get("symptom_text", ""),
                ai_recommended_department=department,
                ai_urgency_score=urgency,
                ai_confidence=classification.get("confidence_score", 0),
            )
        else:
            queue = {
                "success": True,
                "doctor": doctor,
                "message": "Doctor matched (token not assigned — patient not registered).",
            }

        return {
            "queue_result": {**queue, "doctor": doctor},
            "doctor_id": doctor["doctor_id"],
            "appointment_id": queue.get("appointment_id"),
            "messages": [AIMessage(content=(
                f"Queue Assignment:\n"
                f"• Doctor: Dr. {doctor['doctor_name']}\n"
                f"• Department: {doctor['department_name']}\n"
                f"• Token: {queue.get('token_number', 'N/A')}\n"
                f"• Position: #{queue.get('queue_position', 'N/A')}\n"
                f"• Est. Wait: {queue.get('estimated_wait', doctor.get('estimated_wait', 'N/A'))}"
            ))],
            "next_step": "end",
            "completed": True,
        }
    except Exception as e:
        logger.error(f"Queue manager node error: {e}")
        return {
            "error": str(e),
            "messages": [AIMessage(content=f"Queue assignment failed: {e}")],
            "next_step": "end",
        }


def prescription_node(state: MediFlowState) -> dict:
    """Node: Process a prescription from doctor."""
    try:
        result = process_prescription(
            consultation_id=state.get("consultation_id", ""),
            patient_id=state.get("patient_id", ""),
            doctor_id=state.get("doctor_id", ""),
            doctor_user_id=state.get("doctor_user_id", ""),
            items=state.get("prescription_items", []),
            patient_allergies=state.get("patient_allergies"),
            patient_conditions=state.get("patient_conditions"),
        )

        if result.get("success"):
            # Auto-send to pharmacy
            send_to_pharmacy(result["prescription_id"])

        return {
            "prescription_result": result,
            "prescription_id": result.get("prescription_id"),
            "messages": [AIMessage(content=(
                f"Prescription Processed:\n"
                f"• Code: {result.get('prescription_code', 'N/A')}\n"
                f"• Items: {result.get('item_count', 0)}\n"
                f"• Status: {'Sent to pharmacy ✅' if result.get('success') else '❌ Failed'}"
            ))],
            "next_step": "pharmacy" if result.get("success") else "end",
        }
    except Exception as e:
        logger.error(f"Prescription node error: {e}")
        return {
            "error": str(e),
            "messages": [AIMessage(content=f"Prescription processing failed: {e}")],
            "next_step": "end",
        }


def pharmacy_node(state: MediFlowState) -> dict:
    """Node: Check pharmacy stock and handle alternatives."""
    try:
        prescription_id = state.get("prescription_id")
        if not prescription_id:
            return {
                "error": "No prescription ID provided.",
                "messages": [AIMessage(content="No prescription to check.")],
                "next_step": "end",
            }

        result = check_prescription_stock(
            prescription_id=prescription_id,
            patient_allergies=state.get("patient_allergies"),
        )

        return {
            "pharmacy_result": result,
            "messages": [AIMessage(content=(
                f"Pharmacy Stock Check:\n"
                f"• All in stock: {'Yes ✅' if result.get('all_in_stock') else 'No ⚠️'}\n"
                f"• Status: {result.get('status', 'unknown')}\n"
                f"• Message: {result.get('message', '')}"
            ))],
            "next_step": "end",
            "completed": True,
        }
    except Exception as e:
        logger.error(f"Pharmacy node error: {e}")
        return {
            "error": str(e),
            "messages": [AIMessage(content=f"Pharmacy check failed: {e}")],
            "next_step": "end",
        }


def workflow_node(state: MediFlowState) -> dict:
    """Node: Handle workflow state transitions."""
    try:
        result = transition_state(
            appointment_id=state.get("appointment_id", ""),
            patient_id=state.get("patient_id", ""),
            new_state=state.get("target_workflow_state", ""),
            transitioned_by=state.get("transitioned_by"),
            transitioned_by_role=state.get("transitioned_by_role"),
            notes=state.get("transition_notes", ""),
        )

        return {
            "workflow_result": result,
            "current_workflow_state": state.get("target_workflow_state") if result.get("success") else state.get("current_workflow_state"),
            "messages": [AIMessage(content=(
                f"Workflow Update: {result.get('message', 'Unknown')}"
            ))],
            "next_step": "end",
            "completed": True,
        }
    except Exception as e:
        logger.error(f"Workflow node error: {e}")
        return {
            "error": str(e),
            "messages": [AIMessage(content=f"Workflow transition failed: {e}")],
            "next_step": "end",
        }


# ╔══════════════════════════════════════════════════════════╗
# ║  SUPERVISOR / ROUTER                                      ║
# ╚══════════════════════════════════════════════════════════╝

def supervisor_router(state: MediFlowState) -> str:
    """
    Supervisor routing logic — decides which agent to invoke.
    Routes based on the 'action' field in state.
    """
    action = state.get("action", "")
    next_step = state.get("next_step")

    # If a next_step is explicitly set, use it
    if next_step == "end" or state.get("completed"):
        return END
    if next_step == "queue_manager":
        return "queue_manager"
    if next_step == "pharmacy":
        return "pharmacy"

    # Route based on action
    action_routes = {
        "classify_symptoms": "symptom_classifier",
        "assign_queue": "queue_manager",
        "process_prescription": "prescription",
        "check_pharmacy": "pharmacy",
        "transition_workflow": "workflow",
        "full_intake": "symptom_classifier",  # Full pipeline: classify → queue
    }

    route = action_routes.get(action, END)
    logger.info(f"Supervisor routing: action='{action}' → node='{route}'")
    return route


def post_classifier_router(state: MediFlowState) -> str:
    """Route after symptom classification."""
    if state.get("error"):
        return END
    return "queue_manager"


def post_prescription_router(state: MediFlowState) -> str:
    """Route after prescription processing."""
    next_step = state.get("next_step", "end")
    if next_step == "pharmacy":
        return "pharmacy"
    return END


# ╔══════════════════════════════════════════════════════════╗
# ║  BUILD GRAPHS                                             ║
# ╚══════════════════════════════════════════════════════════╝

def build_intake_graph() -> StateGraph:
    """
    Build the Patient Intake pipeline graph.
    Flow: classify symptoms → match doctor → assign queue token
    """
    builder = StateGraph(MediFlowState)

    builder.add_node("symptom_classifier", symptom_classifier_node)
    builder.add_node("queue_manager", queue_manager_node)

    builder.add_edge(START, "symptom_classifier")
    builder.add_edge("symptom_classifier", "queue_manager")
    builder.add_edge("queue_manager", END)

    return builder.compile()


def build_prescription_graph() -> StateGraph:
    """
    Build the Prescription-to-Pharmacy pipeline graph.
    Flow: process prescription → check pharmacy stock
    """
    builder = StateGraph(MediFlowState)

    builder.add_node("prescription", prescription_node)
    builder.add_node("pharmacy", pharmacy_node)

    builder.add_edge(START, "prescription")
    builder.add_conditional_edges(
        "prescription",
        post_prescription_router,
        {"pharmacy": "pharmacy", END: END},
    )
    builder.add_edge("pharmacy", END)

    return builder.compile()


def build_workflow_graph() -> StateGraph:
    """
    Build the Workflow transition graph.
    Simple single-node graph for state transitions.
    """
    builder = StateGraph(MediFlowState)

    builder.add_node("workflow", workflow_node)

    builder.add_edge(START, "workflow")
    builder.add_edge("workflow", END)

    return builder.compile()


def build_main_orchestrator() -> StateGraph:
    """
    Build the main MediFlow orchestrator graph.
    Supervisor pattern — routes to appropriate agent based on action.
    """
    builder = StateGraph(MediFlowState)

    # Add all agent nodes
    builder.add_node("symptom_classifier", symptom_classifier_node)
    builder.add_node("queue_manager", queue_manager_node)
    builder.add_node("prescription", prescription_node)
    builder.add_node("pharmacy", pharmacy_node)
    builder.add_node("workflow", workflow_node)

    # Supervisor routing from START
    builder.add_conditional_edges(
        START,
        supervisor_router,
        {
            "symptom_classifier": "symptom_classifier",
            "queue_manager": "queue_manager",
            "prescription": "prescription",
            "pharmacy": "pharmacy",
            "workflow": "workflow",
            END: END,
        },
    )

    # Post-node routing
    builder.add_conditional_edges(
        "symptom_classifier",
        post_classifier_router,
        {"queue_manager": "queue_manager", END: END},
    )
    builder.add_edge("queue_manager", END)

    builder.add_conditional_edges(
        "prescription",
        post_prescription_router,
        {"pharmacy": "pharmacy", END: END},
    )
    builder.add_edge("pharmacy", END)

    builder.add_edge("workflow", END)

    return builder.compile()


# ╔══════════════════════════════════════════════════════════╗
# ║  PUBLIC API                                               ║
# ╚══════════════════════════════════════════════════════════╝

# Pre-compiled graphs (lazy initialization)
_intake_graph = None
_prescription_graph = None
_workflow_graph = None
_main_graph = None


def get_intake_graph():
    """Get the cached intake pipeline graph."""
    global _intake_graph
    if _intake_graph is None:
        _intake_graph = build_intake_graph()
    return _intake_graph


def get_prescription_graph():
    """Get the cached prescription pipeline graph."""
    global _prescription_graph
    if _prescription_graph is None:
        _prescription_graph = build_prescription_graph()
    return _prescription_graph


def get_workflow_graph():
    """Get the cached workflow graph."""
    global _workflow_graph
    if _workflow_graph is None:
        _workflow_graph = build_workflow_graph()
    return _workflow_graph


def get_main_orchestrator():
    """Get the cached main orchestrator graph."""
    global _main_graph
    if _main_graph is None:
        _main_graph = build_main_orchestrator()
    return _main_graph


def run_intake_pipeline(
    symptom_text: str,
    patient_id: str = None,
    patient_user_id: str = None,
    patient_age: int = None,
    patient_gender: str = None,
    patient_allergies: list = None,
    patient_conditions: list = None,
) -> dict:
    """
    Run the full patient intake pipeline.
    Classifies symptoms → finds best doctor → assigns queue token.
    """
    graph = get_intake_graph()

    initial_state = {
        "messages": [HumanMessage(content=f"Patient symptoms: {symptom_text}")],
        "action": "full_intake",
        "symptom_text": symptom_text,
        "patient_id": patient_id,
        "patient_user_id": patient_user_id,
        "patient_age": patient_age,
        "patient_gender": patient_gender,
        "patient_allergies": patient_allergies or [],
        "patient_conditions": patient_conditions or [],
        "classification_result": None,
        "queue_result": None,
        "next_step": None,
        "error": None,
        "completed": False,
    }

    result = graph.invoke(initial_state)

    return {
        "classification": result.get("classification_result"),
        "queue": result.get("queue_result"),
        "appointment_id": result.get("appointment_id"),
        "doctor_id": result.get("doctor_id"),
        "error": result.get("error"),
        "messages": [m.content for m in result.get("messages", []) if isinstance(m, AIMessage)],
    }


def run_direct_queue_allocation(
    patient_id: str,
    patient_user_id: str,
    patient_report: str,
    department: str,
    urgency: str,
) -> dict:
    """
    Directly allocate a queue token using a pre-generated patient report.
    Used by the conversational AI intake agent.
    """
    # Create a synthetic state simulating the output of the classifier
    state = {
        "symptom_text": patient_report,
        "patient_id": patient_id,
        "patient_user_id": patient_user_id,
        "classification_result": {
            "recommended_department": department,
            "urgency_level": urgency,
            "confidence_score": 0.95,
        }
    }
    
    # Run the queue manager node directly
    result = queue_manager_node(state)
    
    return {
        "queue": result.get("queue_result"),
        "doctor_id": result.get("doctor_id"),
        "appointment_id": result.get("appointment_id"),
        "messages": [m.content for m in result.get("messages", []) if isinstance(m, AIMessage)],
        "error": result.get("error"),
    }


def run_prescription_pipeline(
    consultation_id: str,
    patient_id: str,
    doctor_id: str,
    doctor_user_id: str,
    prescription_items: list,
    patient_allergies: list = None,
    patient_conditions: list = None,
) -> dict:
    """
    Run the prescription-to-pharmacy pipeline.
    Processes prescription → checks stock → suggests alternatives if needed.
    """
    graph = get_prescription_graph()

    initial_state = {
        "messages": [HumanMessage(content="Process prescription")],
        "action": "process_prescription",
        "consultation_id": consultation_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "doctor_user_id": doctor_user_id,
        "prescription_items": prescription_items,
        "patient_allergies": patient_allergies or [],
        "patient_conditions": patient_conditions or [],
        "prescription_result": None,
        "pharmacy_result": None,
        "prescription_id": None,
        "next_step": None,
        "error": None,
        "completed": False,
    }

    result = graph.invoke(initial_state)

    return {
        "prescription": result.get("prescription_result"),
        "pharmacy": result.get("pharmacy_result"),
        "prescription_id": result.get("prescription_id"),
        "error": result.get("error"),
        "messages": [m.content for m in result.get("messages", []) if isinstance(m, AIMessage)],
    }


def run_workflow_transition(
    appointment_id: str,
    patient_id: str,
    target_state: str,
    transitioned_by: str = None,
    transitioned_by_role: str = None,
    notes: str = "",
) -> dict:
    """
    Run a workflow state transition.
    """
    graph = get_workflow_graph()

    initial_state = {
        "messages": [HumanMessage(content=f"Transition to {target_state}")],
        "action": "transition_workflow",
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "target_workflow_state": target_state,
        "transitioned_by": transitioned_by,
        "transitioned_by_role": transitioned_by_role,
        "transition_notes": notes,
        "workflow_result": None,
        "next_step": None,
        "error": None,
        "completed": False,
    }

    result = graph.invoke(initial_state)

    return {
        "workflow": result.get("workflow_result"),
        "current_state": result.get("current_workflow_state"),
        "error": result.get("error"),
        "messages": [m.content for m in result.get("messages", []) if isinstance(m, AIMessage)],
    }
