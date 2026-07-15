import os
import streamlit.components.v1 as components

parent_dir = os.path.dirname(os.path.abspath(__file__))
_component_func = components.declare_component("continuous_voice", path=parent_dir)

def continuous_voice(audio_b64=None, key=None):
    """
    Renders a continuous voice listening component.
    Plays the audio_b64 (AI's voice) if provided, then automatically starts listening.
    Returns the recognized transcript when the user finishes speaking.
    """
    return _component_func(audio_b64=audio_b64, key=key, default=None)
