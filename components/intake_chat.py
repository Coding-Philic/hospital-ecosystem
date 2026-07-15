import streamlit as st
import base64
import os
import subprocess
import tempfile
from agents.intake_chat_agent import transcribe_audio
from agents.orchestrator import run_direct_queue_allocation
from database import queries as db


def text_to_speech_auto(text: str) -> bytes:
    """Generate TTS using gTTS with automatic language detection (en/hi)."""
    try:
        from gtts import gTTS
        import io
        import re
        
        # If the text contains Devanagari characters, default to Hindi TTS
        if re.search(r'[\u0900-\u097F]', text):
            lang = 'hi'
        else:
            # Otherwise use English (which handles English and Hinglish well)
            lang = 'en'
            
        fp = io.BytesIO()
        tts = gTTS(text, lang=lang)
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        return None


def render_intake_chat(patient: dict):
    from agents.intake_chat_agent import run_intake_chat_stream, parse_intake_completion
    
    # Initialize state
    if "intake_messages" not in st.session_state:
        st.session_state.intake_messages = [
            {"role": "assistant", "content": "Welcome! What's going on, how can I help you? / नमस्ते! मैं आपकी मदद कैसे कर सकती हूँ? आपको क्या समस्या हो रही है?"}
        ]
        
        # Fetch patient history ONCE when chat is initialized
        history_text = "No prior history available."
        try:
            consultations = db.get_consultations_by_patient(patient.get("id"))
            if consultations:
                lines = []
                for c in consultations[:5]:  # Limit to 5 most recent
                    date = c.get("created_at", "")[:10]
                    symptoms = c.get("symptoms") or "Not recorded"
                    diag = c.get("diagnosis") or "Not recorded"
                    notes = c.get("examination_notes") or "Not recorded"
                    
                    doc_info = c.get("doctors", {}) or {}
                    doc_user = doc_info.get("users", {}) or {}
                    doctor_name = doc_user.get("full_name", "Unknown Doctor")
                    
                    lines.append(f"- Date: {date} | Doctor: {doctor_name} | Symptoms: {symptoms} | Diagnosis: {diag} | Notes: {notes}")
                history_text = "\n".join(lines)
        except Exception:
            pass
        st.session_state.patient_history_context = history_text
        
    if "intake_completed" not in st.session_state:
        st.session_state.intake_completed = False
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False
    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()
    if "latest_tts" not in st.session_state:
        st.session_state.latest_tts = None
    if "voice_greeting_played" not in st.session_state:
        st.session_state.voice_greeting_played = False
    if "chat_input_val" not in st.session_state:
        st.session_state.chat_input_val = ""

    if st.session_state.intake_completed:
        st.success("Intake complete. You have been assigned to a doctor.")
        if st.button("Start New Visit"):
            del st.session_state.intake_messages
            if "patient_history_context" in st.session_state:
                del st.session_state.patient_history_context
            st.session_state.intake_completed = False
            st.session_state.latest_tts = None
            st.session_state.voice_mode = False
            st.session_state.voice_greeting_played = False
            st.rerun()
        return

    new_user_content = ""
    latest_image_base64 = None
    uploaded_image = None

    if st.session_state.voice_mode:
        from components.voice_component import continuous_voice
        
        # Immersive Full-Screen Voice Mode CSS
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #0f172a !important;
        }
        [data-testid="stAppViewContainer"] * {
            color: #f8fafc !important;
        }
        /* Restore Navbar Text Colors */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) *,
        .desktop-profile-box * {
            color: #1e293b !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="secondary"] p {
            color: #64748b !important;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        [data-testid="stSidebar"] {
            display: none !important;
        }
        .voice-text-container {
            margin-top: -2rem;
            text-align: center;
            font-size: 1.2rem;
            color: #f1f5f9;
            min-height: 80px;
            padding: 20px;
        }
        /* Hide AI audio player so it plays seamlessly in background */
        div[data-testid="stAudio"] {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 4, 1])
        with col3:
            if st.button("✖ Exit Voice", key="exit_voice_top"):
                st.session_state.voice_mode = False
                st.session_state.latest_tts = None
                st.session_state.voice_greeting_played = False
                st.rerun()

        # Automatic greeting
        if not st.session_state.voice_greeting_played:
            greeting = st.session_state.intake_messages[0]["content"]
            tts_audio = text_to_speech_auto(greeting)
            if tts_audio:
                st.session_state.latest_tts = tts_audio
            st.session_state.voice_greeting_played = True

        st.markdown("<div style='height: 5vh;'></div>", unsafe_allow_html=True)

        # Render the custom pulsing orb component
        b64_audio = None
        if st.session_state.latest_tts:
            b64_audio = base64.b64encode(st.session_state.latest_tts).decode("utf-8")
            
        transcript = continuous_voice(audio_b64=b64_audio, key="continuous_voice_comp")
            
        st.markdown("<div class='voice-text-container'>", unsafe_allow_html=True)
        # Show the most recent user text or AI streaming text
        last_msg = st.session_state.intake_messages[-1]
        if last_msg["role"] == "user":
            st.markdown(f"**You:** {last_msg['content']}")
        else:
            st.markdown(f"**Nurse:** {last_msg['content']}")
        st.markdown("</div>", unsafe_allow_html=True)

        # Handle the returned transcript
        if transcript and transcript != st.session_state.get("last_transcript"):
            st.session_state.last_transcript = transcript
            new_user_content = transcript
            st.session_state.latest_tts = None
            
    else:
        st.markdown("### AI Triage Nurse")
        
        # Display normal chat history
        for idx, message in enumerate(st.session_state.intake_messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # ChatGPT-like Input Area CSS
        st.markdown("""
        <style>
        .chat-pill-hook { display: none; }
        div:has(> .element-container .chat-pill-hook) > div[data-testid="stHorizontalBlock"] {
            border: 1px solid var(--border-color, #e2e8f0);
            border-radius: 24px;
            background-color: var(--card-bg, #ffffff);
            padding: 4px 12px;
            align-items: center;
            margin-top: 1rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
        div:has(> .element-container .chat-pill-hook) div[data-testid="stTextInput"] div[data-baseweb="input"] {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }
        div:has(> .element-container .chat-pill-hook) button[kind="secondary"] {
            border: none !important;
            background: transparent !important;
            color: var(--text-secondary, #64748b) !important;
            border-radius: 50% !important;
            padding: 8px !important;
            min-height: 0 !important;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }
        div:has(> .element-container .chat-pill-hook) button[kind="primary"] {
            border-radius: 50% !important;
            width: 40px;
            height: 40px;
            min-height: 0 !important;
            padding: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<span class="chat-pill-hook"></span>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([1, 8, 1, 1])
            with c1:
                with st.popover("➕", use_container_width=True):
                    uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="img_upload")
            with c2:
                def on_submit_text():
                    if st.session_state.chat_input_val:
                        st.session_state.submitted_text = st.session_state.chat_input_val
                        st.session_state.chat_input_val = ""
                st.text_input("Ask anything", label_visibility="collapsed", key="chat_input_val", on_change=on_submit_text, placeholder="Ask anything...")
            with c3:
                if st.button("🎤", use_container_width=True, help="Voice Mode"):
                    st.session_state.voice_mode = True
                    st.rerun()
            with c4:
                if st.button("➤", use_container_width=True, type="primary"):
                    if st.session_state.chat_input_val:
                        st.session_state.submitted_text = st.session_state.chat_input_val
                        st.session_state.chat_input_val = ""

        if "submitted_text" in st.session_state and st.session_state.submitted_text:
            new_user_content = st.session_state.submitted_text
            st.session_state.submitted_text = ""
        
        if uploaded_image:
            image_id = f"{uploaded_image.name}_{uploaded_image.size}"
            if image_id not in st.session_state.processed_files:
                bytes_data = uploaded_image.getvalue()
                latest_image_base64 = base64.b64encode(bytes_data).decode("utf-8")
                new_user_content = (new_user_content + "\n[Patient uploaded an image]").strip()
                st.session_state.processed_files.add(image_id)


    # --- Unified Processing Logic ---
    if new_user_content.strip() or latest_image_base64:
        msg = new_user_content.strip() if new_user_content.strip() else "[Uploaded an Image]"
        st.session_state.intake_messages.append({"role": "user", "content": msg})
        
        if not st.session_state.voice_mode:
            with st.chat_message("user"):
                st.markdown(msg)
                if uploaded_image:
                    st.image(uploaded_image, width=300)

        # Generate Streaming AI Response
        if st.session_state.voice_mode:
            # In voice mode, we just show a spinner placeholder or stream directly to the container
            st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
            full_response = st.write_stream(
                run_intake_chat_stream(
                    conversation_history=st.session_state.intake_messages,
                    latest_image_base64=latest_image_base64,
                    is_voice_mode=st.session_state.voice_mode,
                    patient_history=st.session_state.get("patient_history_context")
                )
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            with st.chat_message("assistant"):
                full_response = st.write_stream(
                    run_intake_chat_stream(
                        conversation_history=st.session_state.intake_messages,
                        latest_image_base64=latest_image_base64,
                        is_voice_mode=st.session_state.voice_mode,
                        patient_history=st.session_state.get("patient_history_context")
                    )
                )
                
        st.session_state.intake_messages.append({"role": "assistant", "content": full_response})

        # Generate TTS after streaming finishes if in voice mode
        if st.session_state.voice_mode:
            tts_audio = text_to_speech_auto(full_response)
            if tts_audio:
                st.session_state.latest_tts = tts_audio

        # Check for completion
        completion_data = parse_intake_completion(full_response)
        if completion_data["is_complete"]:
            st.session_state.intake_completed = True
            final_data = completion_data["final_data"]
            
            if not st.session_state.voice_mode:
                st.success("Analysis complete. Assigning you to the appropriate department...")

            queue_result = run_direct_queue_allocation(
                patient_id=patient["id"],
                patient_user_id=patient["user_id"],
                patient_report=final_data.get("patient_report", "No report provided"),
                department=final_data.get("recommended_department", "General Medicine"),
                urgency=final_data.get("urgency_level", "routine")
            )

            if queue_result.get("error"):
                st.error(f"Failed to assign queue: {queue_result['error']}")
            elif not st.session_state.voice_mode:
                st.info("Queue Assignment Successful")
                for msg in queue_result.get("messages", []):
                    st.markdown(msg)

        st.rerun()
