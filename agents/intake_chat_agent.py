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

IMPORTANT LANGUAGE RULES: 
- You MUST detect the language the user is speaking (e.g., English, Hindi, or Hinglish) and reply in the EXACT SAME language.
- If the user speaks English, reply in English. If they speak Hindi, reply in Hindi. If they speak Hinglish, reply in Hinglish.
- By default, assume a bilingual English/Hindi context.

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


def run_intake_chat_stream(conversation_history: list, latest_image_base64: str = None, is_voice_mode: bool = False, patient_history: str = None):
    """
    Generator that yields the AI's response chunks.
    Automatically strips out <think>...</think> blocks.
    """
    client = get_raw_groq_client()
    
    if is_voice_mode:
        model_name = "llama-3.3-70b-versatile"
    else:
        model_name = "qwen/qwen3.6-27b"
        
    system_message = SYSTEM_PROMPT.format(
        departments=", ".join(config.DEPARTMENTS)
    )
    
    if patient_history:
        system_message += f"\n\nPATIENT PAST MEDICAL HISTORY:\n{patient_history}\n(Use this context to inform your questions and understand their background, but focus on the CURRENT issue they report.)"

    groq_messages = [{"role": "system", "content": system_message}]

    for msg in conversation_history:
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
        stream = client.chat.completions.create(
            model=model_name,
            messages=groq_messages,
            temperature=0.3,
            stream=True
        )
        
        in_think_block = False
        buffer = ""
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                buffer += content
                
                if not in_think_block:
                    if "<think>" in buffer:
                        parts = buffer.split("<think>", 1)
                        if parts[0]:
                            yield parts[0]
                        buffer = "<think>" + parts[1]
                        in_think_block = True
                    else:
                        if len(buffer) > 7:
                            yield buffer[:-7]
                            buffer = buffer[-7:]
                
                if in_think_block:
                    if "</think>" in buffer:
                        parts = buffer.split("</think>", 1)
                        buffer = parts[1]
                        in_think_block = False

        if buffer and not in_think_block:
            yield buffer

    except Exception as e:
        logger.error(f"Groq chat error: {e}")
        yield "मुझे क्षमा करें, मुझे अभी नेटवर्क से कनेक्ट करने में परेशानी हो रही है। क्या आप दोहरा सकते हैं? (I'm having trouble connecting right now. Could you repeat that?)"

def parse_intake_completion(ai_response: str) -> dict:
    """Parses the final completed response to see if intake is complete."""
    import re
    text_to_parse = ai_response.strip()
    if "```json" in ai_response:
        text_to_parse = ai_response.split("```json")[1].split("```")[0].strip()
    elif "```" in ai_response:
        text_to_parse = ai_response.split("```")[1].split("```")[0].strip()
        
    if text_to_parse.startswith("{") and "complete" in text_to_parse:
        try:
            import json
            final_data = json.loads(text_to_parse)
            if final_data.get("status") == "complete":
                return {
                    "is_complete": True,
                    "final_data": final_data
                }
        except Exception:
            pass

    return {
        "is_complete": False,
        "final_data": None
    }
