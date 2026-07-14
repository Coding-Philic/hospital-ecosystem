import os
import json
import logging
import base64
from groq import Groq
from config import config

logger = logging.getLogger(__name__)

# Initialize raw Groq client
def get_raw_groq_client():
    api_key = config.GROQ_API_KEY
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets["groq"]["GROQ_API_KEY"]
        except Exception:
            pass
    return Groq(api_key=api_key)

SYSTEM_PROMPT = """You are MediFlow AI's Medical Triage Nurse. 
Your goal is to understand the patient's symptoms by asking clarifying cross-questions (e.g., onset, duration, severity, location).
You MUST be empathetic, concise, and professional.

If the patient uploads an image, analyze the image to help determine the condition and ask relevant questions based on what you see.

Keep asking one question at a time until you have a clear picture of their issue.
Once you are completely satisfied that you have enough information to allocate them to a doctor, you MUST output a JSON block with the final patient report and recommended routing. 

When outputting the final JSON, format your entire response EXACTLY like this (and nothing else):
```json
{{
    "status": "complete",
    "patient_report": "<GENERATE_A_COMPREHENSIVE_SUMMARY_OF_ALL_SYMPTOMS_AND_ANSWERS_HERE>",
    "recommended_department": "General Medicine",
    "urgency_level": "routine"
}}
```
If you still need more information, simply reply with your next question in plain text. (Do NOT output JSON if you are still asking questions).

Available Departments: {departments}
Urgency Levels: routine, semi_urgent, urgent, emergency
"""

def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio bytes using Groq Whisper."""
    try:
        client = get_raw_groq_client()
        # Groq's whisper model expects a tuple (filename, file_content)
        file = ("audio.wav", audio_bytes)
        transcription = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3",
            response_format="text"
        )
        return transcription
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        return f"[Audio transcription failed: {e}]"


def run_intake_chat(conversation_history: list, latest_image_base64: str = None) -> dict:
    """
    Runs the intake chat.
    conversation_history: List of dicts [{"role": "user"|"assistant", "content": "text"}]
    Returns a dict with:
      - is_complete: bool
      - response_text: str (the next question or the final report)
      - final_data: dict (if complete, contains the JSON data)
    """
    client = get_raw_groq_client()
    
    # We will use qwen3.6-27b for both text and vision
    model_name = "qwen/qwen3.6-27b"

    system_message = SYSTEM_PROMPT.format(
        departments=", ".join(config.DEPARTMENTS)
    )

    # Build the Groq messages array
    groq_messages = [{"role": "system", "content": system_message}]

    # Append history
    for msg in conversation_history:
        # If the last user message has an image, format it accordingly
        if msg == conversation_history[-1] and msg["role"] == "user" and latest_image_base64:
            groq_messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg["content"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{latest_image_base64}"
                        }
                    }
                ]
            })
        else:
            groq_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=groq_messages,
            temperature=0.3,
        )
        
        ai_response = completion.choices[0].message.content.strip()

        # Check if AI outputted the completion JSON
        # We look for ```json ... ``` or just { "status": "complete" }
        text_to_parse = ai_response
        if "```json" in ai_response:
            text_to_parse = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            text_to_parse = ai_response.split("```")[1].split("```")[0].strip()
            
        if text_to_parse.startswith("{") and "complete" in text_to_parse:
            try:
                final_data = json.loads(text_to_parse)
                if final_data.get("status") == "complete":
                    return {
                        "is_complete": True,
                        "response_text": "Intake complete.",
                        "final_data": final_data
                    }
            except json.JSONDecodeError:
                pass # Fallback to standard chat response if parsing fails

        return {
            "is_complete": False,
            "response_text": ai_response,
            "final_data": None
        }

    except Exception as e:
        logger.error(f"Groq chat error: {e}")
        return {
            "is_complete": False,
            "response_text": "I'm having trouble connecting to the medical network right now. Could you repeat that?",
            "final_data": None
        }
