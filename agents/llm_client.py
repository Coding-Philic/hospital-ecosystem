"""
MediFlow AI — Groq LLM Client Wrapper
=======================================
Wraps Groq API via langchain-groq (ChatGroq) with automatic model fallback.
When the primary model (openai/gpt-oss-120b) hits rate limits,
it automatically falls back to the next model in the chain.

Model Switching Guide:
    1. Change PRIMARY_MODEL in .env to switch the default model
    2. The fallback chain is: PRIMARY_MODEL → FALLBACK_MODEL_1 → FALLBACK_MODEL_2
    3. If all models fail, a descriptive error is raised
"""

import os
import time
import logging
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Groq LLM client with automatic model fallback.
    Uses langchain-groq's ChatGroq for compatibility with LangGraph.
    """

    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        if not self.api_key:
            # Try streamlit secrets
            try:
                import streamlit as st
                self.api_key = st.secrets["groq"]["GROQ_API_KEY"]
            except Exception:
                pass

        self.model_chain = config.MODEL_CHAIN
        self._clients = {}  # Cache of ChatGroq instances (stateless, safe to share)

    def _get_chat_model(self, model_name: str, temperature: float = 0.3) -> ChatGroq:
        """Get or create a ChatGroq instance for the given model."""
        cache_key = f"{model_name}_{temperature}"
        if cache_key not in self._clients:
            self._clients[cache_key] = ChatGroq(
                api_key=self.api_key,
                model=model_name,
                temperature=temperature,
                max_tokens=4096,
            )
        return self._clients[cache_key]

    def get_llm(self, temperature: float = 0.3) -> ChatGroq:
        """
        Get the primary ChatGroq LLM instance.
        Used by LangGraph nodes. Always returns the primary model.
        """
        model_name = self.model_chain[0]  # Always start with primary
        return self._get_chat_model(model_name, temperature)

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_retries: int = 3,
    ) -> str:
        """
        Send a message to the LLM with automatic model fallback.

        Args:
            system_prompt: System-level instructions for the LLM
            user_message: The user's message/query
            temperature: Sampling temperature (0.0 - 1.0)
            max_retries: Number of retries per model before falling back

        Returns:
            The LLM's response text
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        # Try each model in the fallback chain.
        # Fallback is per-invocation — does NOT mutate shared state.
        for model_idx, model_name in enumerate(self.model_chain):
            for attempt in range(max_retries):
                try:
                    llm = self._get_chat_model(model_name, temperature)
                    response = llm.invoke(messages)
                    return response.content

                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = "rate" in error_str or "429" in error_str or "limit" in error_str
                    is_model_error = "model" in error_str or "not found" in error_str

                    if is_rate_limit:
                        logger.warning(
                            f"Rate limit on {model_name} (attempt {attempt+1}/{max_retries}). "
                            f"Waiting before retry..."
                        )
                        time.sleep(2 ** attempt)  # Exponential backoff
                    elif is_model_error:
                        logger.warning(f"Model {model_name} not available: {e}")
                        break  # Skip to next model immediately
                    else:
                        logger.error(f"LLM error with {model_name}: {e}")
                        if attempt == max_retries - 1:
                            break  # Try next model
                        time.sleep(1)

            logger.info(f"Falling back from {model_name} to next model in chain...")

        # All models failed
        raise RuntimeError(
            f"All models in the fallback chain failed: {self.model_chain}. "
            "Please check your GROQ_API_KEY and model availability."
        )

    def invoke_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
    ) -> str:
        """
        Invoke the LLM and expect a JSON response.
        Adds explicit JSON formatting instructions to the system prompt.
        """
        json_system_prompt = (
            f"{system_prompt}\n\n"
            "IMPORTANT: You MUST respond with valid JSON only. "
            "Do not include any text, markdown, or code fences before or after the JSON. "
            "Your entire response must be parseable as JSON."
        )
        return self.invoke(json_system_prompt, user_message, temperature)

    def get_current_model(self) -> str:
        """Return the name of the primary model."""
        return self.model_chain[0]


# ── Module-level singleton ────────────────────────────────────

_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def get_llm(temperature: float = 0.3) -> ChatGroq:
    """Convenience function to get a ChatGroq instance for LangGraph nodes."""
    return get_llm_client().get_llm(temperature)
