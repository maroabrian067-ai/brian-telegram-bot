"""AI Service powered by Google Gemini for answering visitor questions on behalf of Maroa Brian Robare."""

import json
import logging
from typing import Dict, List
from config import GEMINI_API_KEY, PROFILE, get_owner_name

logger = logging.getLogger(__name__)

# In-memory conversation history per visitor: {user_id: [{"role": "user"|"model", "text": "..."}]}
_chat_histories: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_PER_USER = 6


def _build_system_instruction() -> str:
    owner_name = get_owner_name()
    profile_json_str = json.dumps(PROFILE, indent=2)

    return f"""You are the personal AI digital representative and assistant for {owner_name}.
Your job is to talk to recruiters, hiring managers, clients, and visitors who message Brian's Telegram bot.

Here is the verified knowledge base and resume for {owner_name}:
{profile_json_str}

CRITICAL BEHAVIORAL GUIDELINES:
1. Persona: You speak professionally, enthusiastically, and warmly on Brian's behalf.
2. Expertise Highlights: Emphasize Brian's unique strengths:
   - Technical BDR / Sales acumen: Discovery calls, BANT/MEDDIC qualification, HubSpot & Salesforce pipeline hygiene.
   - Web Architecture & Hosting: PHP, MySQL, Supabase, WordPress, DNS, hosting uptime, server reliability.
   - Modern AI tools: Utilizing generative AI for account research, lead outreach, and process documentation.
3. Factual Accuracy: Only state facts that appear in Brian's verified profile above.
4. Missing Info: If asked something private or unlisted (e.g. personal home address, private calendar, unrelated trivia), politely explain that you do not have that specific detail and invite them to leave a message using the '✉️ Leave a Message' option so Brian can respond directly.
5. Formatting: Keep your answers concise, structured, and easy to read on mobile Telegram (using bolding and bullet points where helpful).
6. Next Steps: When visitors express interest in hiring, collaborating, or scheduling an interview, guide them to leave a message or reach Brian at maroabrian067@gmail.com / +254 791 338 643.
"""


class AIService:
    def __init__(self):
        self.client = None
        self.provider = None
        self._init_client()

    def _init_client(self):
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. Bot will run in fallback menu mode.")
            return

        # Try the modern google-genai SDK first
        try:
            from google import genai
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.provider = "google-genai"
            logger.info("Successfully initialized google-genai client.")
            return
        except ImportError:
            pass

        # Fallback to google-generativeai SDK if installed
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
        """Generates an AI response representing Brian."""
        owner_name = get_owner_name()

        if not GEMINI_API_KEY or not self.client:
            return (
                f"👋 Thank you for reaching out! I am {owner_name}'s digital assistant.\n\n"
                "*(AI chat mode is active once GEMINI_API_KEY is placed in .env)*\n\n"
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
                        temperature=0.7,
                        max_output_tokens=800,
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
                f"Thank you for your question! {owner_name} would be happy to discuss this in detail.\n\n"
                f"Feel free to click *'✉️ Leave a Message'* to send your inquiry straight to Brian's Telegram!"
            )


# Singleton AI instance
ai_assistant = AIService()