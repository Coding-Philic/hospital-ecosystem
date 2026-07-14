import streamlit as st
import base64
from agents.intake_chat_agent import run_intake_chat, transcribe_audio
from agents.orchestrator import run_direct_queue_allocation
from database import queries as db

def render_intake_chat(patient: dict):
    st.markdown("### 💬 AI Triage Nurse")
    st.info("I'm here to help understand your symptoms. Please type, upload an image of your symptom, or use voice recording below.")

    # Initialize chat history if not exists
    if "intake_messages" not in st.session_state:
        st.session_state.intake_messages = [
            {"role": "assistant", "content": f"Hi {patient.get('first_name', '')}! I'm the AI Triage Nurse. What brings you to the hospital today? You can type, speak, or upload an image."}
        ]
    
    if "intake_completed" not in st.session_state:
        st.session_state.intake_completed = False

    # Display chat messages from history
    for message in st.session_state.intake_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # If already completed, show success and return
    if st.session_state.intake_completed:
        st.success("✅ Intake complete! You have been assigned to a doctor.")
        if st.button("Start New Visit"):
            del st.session_state.intake_messages
            st.session_state.intake_completed = False
            st.rerun()
        return

    # User Input Area
    user_text = st.chat_input("Describe your symptoms...")
    
    # Optional multimodal inputs (columns)
    col1, col2 = st.columns(2)
    with col1:
        # File uploader for images
        uploaded_image = st.file_uploader("Upload an image (optional)", type=["png", "jpg", "jpeg"])
    with col2:
        # Audio input for voice
        audio_bytes = st.audio_input("Record a voice message (optional)")

    # Process Inputs
    new_user_content = ""
    latest_image_base64 = None

    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()

    if user_text:
        new_user_content += user_text + "\n"

    if audio_bytes:
        # Use name and size as a unique identifier for the file
        audio_id = f"{audio_bytes.name}_{audio_bytes.size}"
        if audio_id not in st.session_state.processed_files:
            with st.spinner("Transcribing audio..."):
                transcription = transcribe_audio(audio_bytes.getvalue())
                new_user_content += f"[Voice Message Transcription]: {transcription}\n"
                st.session_state.processed_files.add(audio_id)

    if uploaded_image:
        image_id = f"{uploaded_image.name}_{uploaded_image.size}"
        if image_id not in st.session_state.processed_files:
            # Encode image to base64
            bytes_data = uploaded_image.getvalue()
            latest_image_base64 = base64.b64encode(bytes_data).decode("utf-8")
            new_user_content += "[Patient uploaded an image]\n"
            st.session_state.processed_files.add(image_id)

    # If any input was provided, process it
    if new_user_content.strip():
        # Display user message
        st.session_state.intake_messages.append({"role": "user", "content": new_user_content.strip()})
        with st.chat_message("user"):
            st.markdown(new_user_content.strip())
            if latest_image_base64:
                st.image(uploaded_image, width=300)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                result = run_intake_chat(
                    conversation_history=st.session_state.intake_messages,
                    latest_image_base64=latest_image_base64
                )
                
                # Display AI response
                st.markdown(result["response_text"])
                st.session_state.intake_messages.append({"role": "assistant", "content": result["response_text"]})

                # If the AI is satisfied, finalize the intake!
                if result["is_complete"] and result["final_data"]:
                    st.session_state.intake_completed = True
                    final_data = result["final_data"]
                    
                    st.success("Analysis complete! Assigning you to the appropriate department...")
                    
                    queue_result = run_direct_queue_allocation(
                        patient_id=patient["id"],
                        patient_user_id=patient["user_id"],
                        patient_report=final_data.get("patient_report", "No report provided"),
                        department=final_data.get("recommended_department", "General Medicine"),
                        urgency=final_data.get("urgency_level", "routine")
                    )

                    if queue_result.get("error"):
                        st.error(f"Failed to assign queue: {queue_result['error']}")
                    else:
                        st.info("Queue Assignment Successful!")
                        for msg in queue_result.get("messages", []):
                            st.markdown(msg)
                    
                    # Refresh to show final state
                    st.rerun()
