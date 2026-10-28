"""AI Service powered by Google Gemini: Full ChatGPT-style intelligence with Auto-Model Detection."""

import json
import logging
from typing import Dict, List
from config import GEMINI_API_KEY, PROFILE, get_owner_name

logger = logging.getLogger(__name__)

# In-memory conversation history per visitor: {user_id: [{"role": "user"|"model", "text": "..."}]}
_chat_histories: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_PER_USER = 10


def _build_system_instruction() -> str:
    owner_name = get_owner_name()
    profile_json_str = json.dumps(PROFILE, indent=2)

    return f"""You are an advanced, versatile AI assistant powered by Google Gemini, created by and representing {owner_name}.

You operate with TWO core capabilities:

1. 🌟 FULL CONVERSATIONAL INTELLIGENCE (Like ChatGPT & Gemini):
   - You can chat freely and intelligently on ANY topic.
   - Answer general knowledge questions, write code, explain technical concepts, draft sales pitches, brainstorm ideas, write stories, solve math/logic problems, and have natural, friendly conversations.
   - Be helpful, witty, smart, articulate, and engaging.

2. 👤 PERSONAL REPRESENTATIVE FOR {owner_name.upper()}:
   - Whenever a visitor asks about Brian, his experience, projects, skills, contact info, or hiring him, you represent him enthusiastically using this verified background:
{profile_json_str}

IMPORTANT GUIDELINES:
- Never say "I can only talk about Brian". If someone asks general questions (e.g. "How does DNS work?", "Write a Python script", "What is BANT in sales?"), answer thoroughly and brilliantly just like ChatGPT!
- For private personal details about Brian not in the profile, invite them to use '✉️ Leave a Message' to contact him directly.
- Format responses nicely using Markdown (bullet points, bold text, code blocks) so they are easy to read in Telegram.
- Keep responses engaging, helpful, and concise enough for a chat app.
"""


class AIService:
    def __init__(self):
        self.client = None
        self.provider = None
        self._active_model = None
        self._init_client()

    def _init_client(self):
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set.")
            return

        # Prefer google-genai SDK
        try:
            from google import genai
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.provider = "google-genai"
            logger.info("Initialized google-genai client.")
            return
        except Exception as e:
            logger.info(f"google-genai not available: {e}")

        # Fallback to google-generativeai SDK
        try:
            import google.generativeai as classic_genai
            classic_genai.configure(api_key=GEMINI_API_KEY)
            self.client = classic_genai
            self.provider = "google-generativeai"
            logger.info("Initialized google-generativeai client.")
            return
        except Exception as e:
            logger.warning(f"google-generativeai not available: {e}")

    def _find_available_model(self) -> str:
        """Auto-detects the best working model for this API key."""
        if self._active_model:
            return self._active_model

        candidates = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-001",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
        ]

        try:
            if self.provider == "google-genai":
                available = []
                for m in self.client.models.list():
                    name = getattr(m, "name", "") or str(m)
                    clean_name = name.replace("models/", "")
                    available.append(clean_name)

                # Pick the first matching candidate
                for cand in candidates:
                    if cand in available:
                        self._active_model = cand
                        logger.info(f"Selected Gemini model: {cand}")
                        return cand

                # If no direct match, find any gemini text model
                for m in available:
                    if "gemini" in m and "embed" not in m:
                        self._active_model = m
                        return m

            elif self.provider == "google-generativeai":
                available = []
                for m in self.client.list_models():
                    if "generateContent" in getattr(m, "supported_generation_methods", []):
                        clean_name = m.name.replace("models/", "")
                        available.append(clean_name)

                for cand in candidates:
                    if cand in available:
                        self._active_model = cand
                        logger.info(f"Selected Gemini model: {cand}")
                        return cand

                if available:
                    self._active_model = available[0]
                    return available[0]

        except Exception as e:
            logger.warning(f"Could not list models: {e}")

        # Fallback default
        self._active_model = "gemini-2.0-flash"
        return self._active_model

    async def generate_response(self, user_id: int, user_message: str) -> str:
        """Generates an intelligent AI response."""
        owner_name = get_owner_name()

        if not GEMINI_API_KEY or not self.client:
            return (
                f"👋 Hello! I am {owner_name}'s AI assistant.\n\n"
                "*(AI chat mode is waiting for GEMINI_API_KEY in .env)*\n\n"
                "Please use the buttons below to explore Brian's background or leave a direct message!"
            )

        system_instruction = _build_system_instruction()
        model_name = self._find_available_model()

        # Update in-memory history
        history = _chat_histories.setdefault(user_id, [])
        history.append({"role": "user", "text": user_message})
        if len(history) > MAX_HISTORY_PER_USER:
            history = history[-MAX_HISTORY_PER_USER:]
            _chat_histories[user_id] = history

        try:
            if self.provider == "google-genai":
                formatted_contents = []
                for turn in history:
                    role = "user" if turn["role"] == "user" else "model"
                    formatted_contents.append({
                        "role": role,
                        "parts": [{"text": turn["text"]}]
                    })

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=formatted_contents,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.8,
                        "max_output_tokens": 1200,
                    }
                )
                reply_text = response.text.strip()
                history.append({"role": "model", "text": reply_text})
                return reply_text

            elif self.provider == "google-generativeai":
                model = self.client.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction,
                )
                chat_history = []
                for turn in history[:-1]:
                    chat_history.append({
                        "role": turn["role"],
                        "parts": [turn["text"]]
                    })
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(user_message)
                reply_text = response.text.strip()
                history.append({"role": "model", "text": reply_text})
                return reply_text

        except Exception as e:
            logger.error(f"Error calling model {model_name}: {e}", exc_info=True)
            # Try single-turn direct prompt fallback
            try:
                full_prompt = f"{system_instruction}\n\nUser: {user_message}\nAssistant:"
                if self.provider == "google-genai":
                    resp = self.client.models.generate_content(
                        model=model_name,
                        contents=full_prompt,
                    )
                    return resp.text.strip()
                elif self.provider == "google-generativeai":
                    m = self.client.GenerativeModel(model_name)
                    resp = m.generate_content(full_prompt)
                    return resp.text.strip()
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")

            return f"⚠️ API Error ({model_name}): {e}"


# Singleton AI instance
ai_assistant = AIService()