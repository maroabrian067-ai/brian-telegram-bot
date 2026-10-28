"""AI Service powered by Google Gemini: Full ChatGPT-style intelligence + Personal Representative for Maroa Brian Robare."""

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
- Never say "I can only talk about Brian". If someone asks general questions (e.g., "How does DNS work?", "Write a Python script for web scraping", "What is BANT in sales?"), answer them thoroughly and brilliantly just like ChatGPT!
- For private personal details about Brian not in the profile (like home address or private calendar), invite them to use the '✉️ Leave a Message' button to contact him directly.
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
            logger.info("Successfully initialized google-genai client.")
            return
        except ImportError:
            pass

        try:
            import google.generativeai as classic_genai
            classic_genai.configure(api_key=GEMINI_API_KEY)
            self.client = classic_genai
            self.provider = "google-generativeai"
            logger.info("Successfully initialized google-generativeai client.")
            return
        except ImportError:
            logger.warning("Neither 'google-genai' nor 'google-generativeai' could be imported.")

    async def generate_response(self, user_id: int, user_message: str) -> str:
        """Generates an intelligent AI response."""
        owner_name = get_owner_name()

        if not GEMINI_API_KEY or not self.client:
            return (
                f"👋 Hello! I am {owner_name}'s AI assistant.\n\n"
                "*(AI chat mode is waiting for GEMINI_API_KEY)*\n\n"
                "Please use the buttons below to explore Brian's background or leave a direct message!"
            )

        system_instruction = _build_system_instruction()

        # Update in-memory history
        history = _chat_histories.setdefault(user_id, [])
        history.append({"role": "user", "text": user_message})
        if len(history) > MAX_HISTORY_PER_USER:
            history = history[-MAX_HISTORY_PER_USER:]
            _chat_histories[user_id] = history

        try:
            if self.provider == "google-genai":
                from google.genai import types

                contents = []
                for turn in history:
                    contents.append(
                        types.Content(
                            role="user" if turn["role"] == "user" else "model",
                            parts=[types.Part.from_text(text=turn["text"])],
                        )
                    )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.8,
                        max_output_tokens=1500,
                    ),
                )
                reply_text = response.text.strip()
                history.append({"role": "model", "text": reply_text})
                return reply_text

            elif self.provider == "google-generativeai":
                model = self.client.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction,
                )
                chat = model.start_chat(
                    history=[
                        {"role": turn["role"], "parts": [turn["text"]]}
                        for turn in history[:-1]
                    ]
                )
                response = chat.send_message(user_message)
                reply_text = response.text.strip()
                history.append({"role": "model", "text": reply_text})
                return reply_text

        except Exception as e:
            logger.error(f"Error calling Gemini: {e}", exc_info=True)
            return (
                f"I ran into a temporary issue, but I am ready to help! What would you like to explore or discuss?"
            )


# Singleton AI instance
ai_assistant = AIService()