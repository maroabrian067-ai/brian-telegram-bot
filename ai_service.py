"""AI Service powered by Google Gemini (3.8 generation) with Smart Retry & Pro Fallback."""

import asyncio
import json
import logging
from typing import Dict, List
from config import GEMINI_API_KEY, PROFILE, get_owner_name

logger = logging.getLogger(__name__)

# Available models for your API key
MODELS = ["gemini-3.8-flash", "gemini-3.8-pro"]

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
        self._init_client()

    def _init_client(self):
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.provider = "google-genai"
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
        """Executes a single API call to Gemini."""
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
            return response.text.strip()

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
            response = chat.send_message(history[-1]["text"])
            return response.text.strip()

        raise RuntimeError("No Gemini SDK provider initialized.")

    async def generate_response(self, user_id: int, user_message: str) -> str:
        """Generates an AI response with smart retries and Pro fallback."""
        owner_name = get_owner_name()

        if not GEMINI_API_KEY or not self.client:
            return (
                f"👋 Hello! I am {owner_name}'s AI assistant.\n\n"
                "*(AI chat mode is waiting for GEMINI_API_KEY in .env)*\n\n"
                "Please use the buttons below to explore Brian's background or leave a direct message!"
            )

        system_instruction = _build_system_instruction()

        # Update in-memory history
        history = _chat_histories.setdefault(user_id, [])
        history.append({"role": "user", "text": user_message})
        if len(history) > MAX_HISTORY_PER_USER:
            history = history[-MAX_HISTORY_PER_USER:]
            _chat_histories[user_id] = history

        # Try models in order: gemini-3.8-flash -> gemini-3.8-pro
        for model in MODELS:
            # Retry up to 3 times if 503 high demand spike occurs
            for attempt in range(3):
                try:
                    reply_text = self._call_model(model, history, system_instruction)
                    if reply_text:
                        history.append({"role": "model", "text": reply_text})
                        return reply_text
                except Exception as e:
                    err = str(e)
                    logger.warning(f"Model {model} attempt {attempt+1} error: {err}")

                    # If temporary 503 high demand spike, wait and retry
                    if "503" in err or "UNAVAILABLE" in err:
                        wait_seconds = 1.5 * (attempt + 1)
                        logger.info(f"Retrying {model} in {wait_seconds}s...")
                        await asyncio.sleep(wait_seconds)
                        continue

                    # If model not found (404), break to next model immediately
                    break

        return "Google's Gemini servers are experiencing a brief traffic spike right now. Please send your message again in a few seconds!"


# Singleton AI instance
ai_assistant = AIService()