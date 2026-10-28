"""AI Service powered by Google Gemini with Zero-Downtime Smart Knowledge Fallback."""

import json
import logging
from typing import Dict, List
from config import (
    GEMINI_API_KEY,
    PROFILE,
    format_about_text,
    format_contact_text,
    format_skills_text,
    get_owner_name,
)

logger = logging.getLogger(__name__)

# Preferred models in order
PREFERRED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.8-pro",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]

_chat_histories: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_PER_USER = 10


def _build_system_instruction() -> str:
    owner_name = get_owner_name()
    profile_json_str = json.dumps(PROFILE, indent=2)

    return f"""You are an advanced, versatile AI assistant powered by Google Gemini, representing {owner_name}.
You can chat freely on ANY topic (like ChatGPT) AND answer questions about Brian's background using this verified profile:
{profile_json_str}

Format responses nicely with Markdown (bullet points, bold text). Keep responses engaging and concise for Telegram.
"""


def _smart_local_fallback(user_message: str) -> str:
    """Answers intelligently from local profile_data.json if Google AI is experiencing a 503 spike."""
    msg = user_message.lower()
    owner_name = get_owner_name()

    if any(w in msg for w in ["skill", "stack", "tech", "experience", "framework", "bant", "meddic", "php", "mysql", "sales"]):
        return format_skills_text()

    if any(w in msg for w in ["contact", "email", "phone", "reach", "call", "interview", "hire", "number", "linkedin"]):
        return format_contact_text()

    if any(w in msg for w in ["who", "about", "brian", "maroa", "bio", "background", "education", "university", "degree"]):
        return format_about_text()

    if any(w in msg for w in ["hello", "hi", "hey", "start", "greetings"]):
        return (
            f"👋 Hello! Welcome to the digital office of *{owner_name}*.\n\n"
            f"I am Brian's AI Assistant. I can tell you all about his background as a **Technical BDR & Solutions Designer**, "
            f"his technical hosting and database experience, or forward a message directly to him!\n\n"
            f"What would you like to know?"
        )

    # General fallback
    return (
        f"Thank you for your message! I represent *{owner_name}* (Technical BDR & Solutions Designer).\n\n"
        f"You can explore his background using the buttons below, or click *'✉️ Leave a Message'* "
        f"to send your question directly to Brian's Telegram inbox!"
    )


class AIService:
    def __init__(self):
        self.client = None
        self.provider = None
        self._init_client()

    def _init_client(self):
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.provider = "google-genai"

            # Log available models to Render console
            try:
                models = [getattr(m, "name", str(m)).replace("models/", "") for m in self.client.models.list()]
                logger.info(f"Available Gemini models on this key: {models}")
            except Exception as e:
                logger.info(f"Model listing note: {e}")

            logger.info("Initialized google-genai client.")
            return
        except Exception as e:
            logger.info(f"google-genai not available: {e}")

        try:
            import google.generativeai as classic_genai
            classic_genai.configure(api_key=GEMINI_API_KEY)
            self.client = classic_genai
            self.provider = "google-generativeai"
            logger.info("Initialized google-generativeai client.")
            return
        except Exception as e:
            logger.warning(f"google-generativeai not available: {e}")

    def _call_model(self, model_name: str, history: List[Dict[str, str]], system_instruction: str) -> str:
        if self.provider == "google-genai":
            formatted = []
            for turn in history:
                role = "user" if turn["role"] == "user" else "model"
                formatted.append({"role": role, "parts": [{"text": turn["text"]}]})

            resp = self.client.models.generate_content(
                model=model_name,
                contents=formatted,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.8,
                    "max_output_tokens": 1200,
                },
            )
            return resp.text.strip()

        elif self.provider == "google-generativeai":
            m = self.client.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
            chat_history = [{"role": t["role"], "parts": [t["text"]]} for t in history[:-1]]
            chat = m.start_chat(history=chat_history)
            resp = chat.send_message(history[-1]["text"])
            return resp.text.strip()

        raise RuntimeError("No client available.")

    async def generate_response(self, user_id: int, user_message: str) -> str:
        """Generates AI response with zero-downtime local fallback."""
        owner_name = get_owner_name()

        if not GEMINI_API_KEY or not self.client:
            return _smart_local_fallback(user_message)

        system_instruction = _build_system_instruction()

        # Update in-memory history
        history = _chat_histories.setdefault(user_id, [])
        history.append({"role": "user", "text": user_message})
        if len(history) > MAX_HISTORY_PER_USER:
            history = history[-MAX_HISTORY_PER_USER:]
            _chat_histories[user_id] = history

        # Try Google Gemini models
        for model in PREFERRED_MODELS:
            try:
                reply = self._call_model(model, history, system_instruction)
                if reply:
                    history.append({"role": "model", "text": reply})
                    return reply
            except Exception as e:
                err = str(e)
                logger.warning(f"Model {model} failed: {err}")
                # If 503, try next model immediately without waiting
                continue

        # If Google servers are temporarily 503, answer instantly using smart profile fallback!
        logger.info("Google API unavailable. Using zero-downtime smart knowledge base fallback.")
        fallback_reply = _smart_local_fallback(user_message)
        history.append({"role": "model", "text": fallback_reply})
        return fallback_reply


# Singleton AI instance
ai_assistant = AIService()