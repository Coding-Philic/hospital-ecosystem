"""
MediFlow AI — Symptom Classifier Agent (Pipeline A)
=====================================================
Analyzes patient-reported symptoms and produces:
  - Recommended department/specialty
  - Urgency score (routine / semi-urgent / urgent / emergency)
  - Red-flag symptom detection for emergency escalation
  - Confidence score

This agent RECOMMENDS — it does NOT diagnose. A human (nurse/receptionist)
must confirm the routing before it becomes final.
"""

import json
import logging
from typing import Optional
from config import config
from agents.llm_client import get_llm_client

logger = logging.getLogger(__name__)

SYMPTOM_CLASSIFIER_PROMPT = """You are MediFlow AI's Medical Triage Assistant. Your role is to help route patients to the correct hospital department based on their reported symptoms. You are NOT making a diagnosis — you are recommending which department should see the patient, and how urgently.

AVAILABLE DEPARTMENTS:
{departments}

URGENCY LEVELS:
- "routine": Non-urgent, standard queue (common cold, minor ache, follow-up visit)
- "semi_urgent": Needs attention within a few hours (persistent fever, moderate pain, worsening symptoms)
- "urgent": Needs prompt attention (high fever with symptoms, acute pain, significant injury)
- "emergency": IMMEDIATE attention required — bypass queue (chest pain, breathing difficulty, stroke signs, severe bleeding, loss of consciousness, seizure, anaphylaxis, severe trauma)

RED-FLAG SYMPTOMS (always classify as "emergency"):
{red_flags}

PATIENT INFORMATION:
- Age: {age}
- Gender: {gender}
- Known Allergies: {allergies}
- Chronic Conditions: {chronic_conditions}

INSTRUCTIONS:
1. Analyze the patient's symptom description
2. Determine the most appropriate department
3. Assign an urgency level
4. Check for ANY red-flag symptoms — if present, urgency MUST be "emergency"
5. Provide your reasoning
6. Suggest any immediate investigations if relevant
7. Assign a confidence score (0.0 to 1.0)

Respond ONLY with valid JSON in this exact format:
{{
    "recommended_department": "Department Name",
    "urgency_level": "routine|semi_urgent|urgent|emergency",
    "confidence_score": 0.85,
    "reasoning": "Brief explanation of why this department and urgency level",
    "is_emergency": false,
    "red_flags_detected": [],
    "suggested_investigations": []
}}"""


def classify_symptoms(
    symptom_text: str,
    patient_age: Optional[int] = None,
    patient_gender: Optional[str] = None,
    allergies: Optional[list] = None,
    chronic_conditions: Optional[list] = None,
) -> dict:
    """
    Classify patient symptoms using AI to recommend department and urgency.

    Args:
        symptom_text: Patient's description of their symptoms
        patient_age: Patient's age (if known)
        patient_gender: Patient's gender (if known)
        allergies: Known allergies
        chronic_conditions: Known chronic conditions

    Returns:
        dict with: recommended_department, urgency_level, confidence_score,
                   reasoning, is_emergency, red_flags_detected, suggested_investigations
    """
    if not symptom_text or not symptom_text.strip():
        return {
            "recommended_department": "General Medicine",
            "urgency_level": "routine",
            "confidence_score": 0.0,
            "reasoning": "No symptoms provided. Defaulting to General Medicine.",
            "is_emergency": False,
            "red_flags_detected": [],
            "suggested_investigations": [],
        }

    # Check for obvious red-flag keywords before AI call
    symptom_lower = symptom_text.lower()
    pre_check_emergency = any(flag in symptom_lower for flag in config.RED_FLAG_SYMPTOMS)

    # Format the system prompt
    system_prompt = SYMPTOM_CLASSIFIER_PROMPT.format(
        departments=", ".join(config.DEPARTMENTS),
        red_flags=", ".join(config.RED_FLAG_SYMPTOMS),
        age=patient_age or "Unknown",
        gender=patient_gender or "Unknown",
        allergies=", ".join(allergies) if allergies else "None known",
        chronic_conditions=", ".join(chronic_conditions) if chronic_conditions else "None known",
    )

    user_message = f"Patient's symptom description:\n\n{symptom_text}"

    try:
        llm_client = get_llm_client()
        response_text = llm_client.invoke_json(system_prompt, user_message, temperature=0.1)

        # Parse JSON response
        # Clean up response if it has markdown code fences
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # Validate department
        if result.get("recommended_department") not in config.DEPARTMENTS:
            # Find closest match
            dept_lower = result.get("recommended_department", "").lower()
            for dept in config.DEPARTMENTS:
                if dept_lower in dept.lower() or dept.lower() in dept_lower:
                    result["recommended_department"] = dept
                    break
            else:
                result["recommended_department"] = "General Medicine"

        # Override: if pre-check found red flags, force emergency
        if pre_check_emergency and result.get("urgency_level") != "emergency":
            result["urgency_level"] = "emergency"
            result["is_emergency"] = True
            result["red_flags_detected"] = [
                flag for flag in config.RED_FLAG_SYMPTOMS if flag in symptom_lower
            ]

        # Ensure is_emergency matches urgency
        if result.get("urgency_level") == "emergency":
            result["is_emergency"] = True

        # Clamp confidence score
        result["confidence_score"] = max(0.0, min(1.0, float(result.get("confidence_score", 0.5))))

        logger.info(
            f"Symptom classification: {result['recommended_department']} "
            f"({result['urgency_level']}, confidence: {result['confidence_score']})"
        )

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Graceful degradation: default to General Medicine
        return {
            "recommended_department": "General Medicine",
            "urgency_level": "emergency" if pre_check_emergency else "routine",
            "confidence_score": 0.0,
            "reasoning": "AI classification failed. Defaulting to safe routing. Please review manually.",
            "is_emergency": pre_check_emergency,
            "red_flags_detected": [flag for flag in config.RED_FLAG_SYMPTOMS if flag in symptom_lower] if pre_check_emergency else [],
            "suggested_investigations": [],
        }

    except Exception as e:
        logger.error(f"Symptom classification error: {e}")
        return {
            "recommended_department": "General Medicine",
            "urgency_level": "emergency" if pre_check_emergency else "routine",
            "confidence_score": 0.0,
            "reasoning": f"AI service temporarily unavailable. Default routing applied. Error: {str(e)}",
            "is_emergency": pre_check_emergency,
            "red_flags_detected": [],
            "suggested_investigations": [],
        }


def generate_clinical_notes_from_triage(triage_summary: str, vitals: dict, patient_info: dict) -> dict:
    """
    Generate initial clinical notes (Symptoms, Exam, Diagnosis, Additional Notes) 
    based on the triage summary, vitals, and patient history.
    """
    try:
        system_prompt = f"""You are MediFlow AI's Clinical Assistant. Your job is to draft the doctor's consultation notes based on the patient's triage report, vitals, and history.

PATIENT INFO:
- Age: {patient_info.get('users', {}).get('age', 'Unknown')}
- Gender: {patient_info.get('users', {}).get('gender', 'Unknown')}
- Allergies: {', '.join(patient_info.get('allergies') or []) or 'None'}
- Chronic Conditions: {', '.join(patient_info.get('chronic_conditions') or []) or 'None'}

VITALS:
- BP: {vitals.get('bp', 'Not recorded')}
- Temp: {vitals.get('temperature', 'Not recorded')}
- Pulse: {vitals.get('pulse', 'Not recorded')}
- SpO2: {vitals.get('spo2', 'Not recorded')}
- Weight: {vitals.get('weight', 'Not recorded')}

TRIAGE SUMMARY / CHIEF COMPLAINT:
{triage_summary}

INSTRUCTIONS:
Generate a draft of the clinical notes.
1. "symptoms": Summarize the chief complaint clearly and concisely in medical terms.
2. "examination_notes": Propose standard examination notes that the doctor would typically write for these symptoms (e.g., "Patient appears in mild distress. Oropharynx clear. Chest clear to auscultation."). Leave placeholders like [Examine X] if physical exam is strictly necessary.
3. "diagnosis": Propose a provisional diagnosis based heavily on the symptoms. Use standard medical terminology.
4. "additional_notes": Any warnings based on vitals or chronic conditions, or suggestions for lab tests.

Respond ONLY with valid JSON in this exact format:
{{
    "symptoms": "...",
    "examination_notes": "...",
    "diagnosis": "...",
    "additional_notes": "..."
}}"""
        from agents.llm_client import get_llm_client
        llm_client = get_llm_client()
        response = llm_client.invoke_json(system_prompt, "Generate clinical notes draft.")
        
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
        result = json.loads(response)
        return {
            "symptoms": result.get("symptoms", ""),
            "examination_notes": result.get("examination_notes", ""),
            "diagnosis": result.get("diagnosis", ""),
            "additional_notes": result.get("additional_notes", "")
        }
    except Exception as e:
        logger.error(f"Failed to generate clinical notes: {e}")
        return {}
