import os
import streamlit.components.v1 as components

parent_dir = os.path.dirname(os.path.abspath(__file__))
_component_func = components.declare_component("continuous_voice", path=parent_dir)

def continuous_voice(text_to_speak=None, timestamp=None, key=None):
    """
    Renders a continuous voice listening component.
    Plays the text_to_speak (AI's voice) using browser TTS if provided, then automatically starts listening.
    Returns the recognized transcript when the user finishes speaking.
    """
    # Cache busted again!
    return _component_func(text_to_speak=text_to_speak, timestamp=timestamp, key=key, default=None)
