"""Main Telegram bot application for Maroa Brian Robare: Digital Representative & Inquiry Forwarder."""

import html
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    constants,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    GEMINI_API_KEY,
    OWNER_CHAT_ID,
    PROFILE,
    TELEGRAM_BOT_TOKEN,
    format_about_text,
    format_contact_text,
    format_skills_text,
    get_owner_name,
)
from ai_service import ai_assistant

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# State tracking for visitors: user_id -> state (e.g. "LEAVING_MESSAGE")
user_states = {}

# Map owner forwarded message ID -> visitor user_id (for two-way replies)
reply_map = {}


# --- DUMMY HTTP SERVER FOR CLOUD HEALTH CHECKS (RENDER / KOYEB) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Maroa Brian Robare's Telegram Bot is running 24/7!")

    def log_message(self, format, *args):
        pass  # Silence cloud ping logs


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server listening on port {port}")
    server.serve_forever()


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Builds the main interactive menu buttons."""
    keyboard = [
        [
            InlineKeyboardButton("👤 About Brian", callback_data="btn_about"),
            InlineKeyboardButton("🛠 Skills & Projects", callback_data="btn_skills"),
        ],
        [
            InlineKeyboardButton("📬 Contact Details", callback_data="btn_contact"),
            InlineKeyboardButton("✉️ Leave a Message", callback_data="btn_leave_msg"),
        ],
        [
            InlineKeyboardButton("🤖 How to Chat with Brian's AI", callback_data="btn_chat_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    user_name = user.first_name if user else "Visitor"
    owner_name = get_owner_name()

    greeting_template = PROFILE.get("bot_behavior", {}).get("greeting_message", "")
    if greeting_template:
        welcome_text = greeting_template.format(name=user_name, owner_name=owner_name)
    else:
        welcome_text = f"👋 Hello {user_name}! Welcome to the digital office of {owner_name}."

    welcome_text += "\n\nFeel free to explore an option below or send any question about my background directly in this chat!"

    await update.message.reply_text(
        text=welcome_text,
        reply_markup=get_main_keyboard(),
    )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Returns the user's Telegram ID."""
    user = update.effective_user
    chat = update.effective_chat
    response = (
        f"🆔 *Your Telegram Information*\n\n"
        f"• *Your User ID:* `{user.id}`\n"
        f"• *Chat ID:* `{chat.id}`\n"
        f"• *Name:* {user.full_name}\n"
        f"• *Username:* @{user.username if user.username else 'Not set'}\n\n"
        f"*(Copy your User ID and paste it into `.env` as `OWNER_CHAT_ID`)*"
    )
    await update.message.reply_text(response, parse_mode=constants.ParseMode.MARKDOWN)


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline menu button clicks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id
    owner_name = get_owner_name()

    if data == "btn_about":
        text = format_about_text()
        await query.message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)

    elif data == "btn_skills":
        text = format_skills_text()
        await query.message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)

    elif data == "btn_contact":
        text = format_contact_text()
        await query.message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)

    elif data == "btn_leave_msg":
        user_states[user_id] = "LEAVING_MESSAGE"
        await query.message.reply_text(
            f"✍️ *Leave a Message for {owner_name}*\n\n"
            f"Please type your message, inquiry, or contact info below and send it. "
            f"I will forward it straight to Brian's personal Telegram inbox!\n\n"
            f"_(Type `/cancel` if you change your mind)_",
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    elif data == "btn_chat_help":
        help_text = (
            f"💡 *Chatting with Brian's AI Assistant*\n\n"
            f"I am equipped with Brian's complete background in:\n"
            f"• Technical BDR & Inbound Lead Qualification (BANT/MEDDIC)\n"
            f"• Web Architecture, PHP, MySQL, & Hosting Concepts\n"
            f"• Generative AI & CRM Workflows (HubSpot, Salesforce)\n\n"
            f"Ask questions like:\n"
            f"• _\"What is Brian's experience with sales discovery?\"_\n"
            f"• _\"Tell me about his technical hosting projects.\"_\n"
            f"• _\"How can we schedule an interview?\"_\n\n"
            f"Just send your question as a regular message anytime!"
        )
        await query.message.reply_text(help_text, parse_mode=constants.ParseMode.MARKDOWN)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels any message composition."""
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
        await update.message.reply_text("✅ Cancelled. How else can I assist you?", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("Nothing to cancel! Choose an option:", reply_markup=get_main_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes incoming visitor messages and owner replies."""
    user = update.effective_user
    chat = update.effective_chat
    user_id = user.id
    user_text = update.message.text
    owner_name = get_owner_name()

    # 1. OWNER REPLYING TO FORWARDED INQUIRY
    if OWNER_CHAT_ID and user_id == OWNER_CHAT_ID and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        if replied_msg_id in reply_map:
            visitor_id = reply_map[replied_msg_id]
            try:
                await context.bot.send_message(
                    chat_id=visitor_id,
                    text=f"💬 *Direct Reply from {owner_name}:*\n\n{user_text}",
                    parse_mode=constants.ParseMode.MARKDOWN,
                )
                await update.message.reply_text(f"✅ Delivered to visitor (ID: `{visitor_id}`).", parse_mode=constants.ParseMode.MARKDOWN)
                return
            except Exception as e:
                logger.error(f"Error relaying owner reply: {e}")
                await update.message.reply_text(f"❌ Failed to deliver reply: {e}")
                return

    # 2. VISITOR LEAVING DIRECT MESSAGE
    if user_states.get(user_id) == "LEAVING_MESSAGE":
        del user_states[user_id]

        if not OWNER_CHAT_ID:
            await update.message.reply_text(
                f"✅ Thank you! Your message has been received.\n\n"
                f"*(Tip: Brian has not yet added OWNER_CHAT_ID in .env)*",
                reply_markup=get_main_keyboard(),
            )
            return

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        visitor_tag = f"@{user.username}" if user.username else "No username"

        forward_notice = (
            f"📬 *NEW VISITOR INQUIRY FOR BRIAN*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *From:* {html.escape(user.full_name)} ({visitor_tag})\n"
            f"🆔 *User ID:* `{user.id}`\n"
            f"🕒 *Time:* {timestamp_str}\n\n"
            f"💬 *Message:*\n{user_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 *Swipe/reply to this message directly in Telegram to send an answer back!*"
        )

        try:
            sent_msg = await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=forward_notice,
                parse_mode=constants.ParseMode.MARKDOWN,
            )
            reply_map[sent_msg.message_id] = user.id

            await update.message.reply_text(
                f"✅ Thank you, {user.first_name}! Your message has been forwarded directly to {owner_name}'s Telegram inbox. "
                f"He will get back to you shortly.",
                reply_markup=get_main_keyboard(),
            )
        except Exception as e:
            logger.error(f"Error forwarding message to owner: {e}")
            await update.message.reply_text(
                f"❌ An error occurred forwarding your message. You can reach Brian directly at maroabrian067@gmail.com.",
                reply_markup=get_main_keyboard(),
            )
        return

    # 3. REGULAR CONVERSATION -> GEMINI AI ANSWERS
    await context.bot.send_chat_action(chat_id=chat.id, action=constants.ChatAction.TYPING)
    ai_reply = await ai_assistant.generate_response(user_id=user_id, user_message=user_text)

    try:
        await update.message.reply_text(ai_reply, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=get_main_keyboard())
    except Exception:
        await update.message.reply_text(ai_reply, reply_markup=get_main_keyboard())


def main():
    """Starts the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN is empty in .env!")
        return

    # Start the background HTTP health server for cloud hosting
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    print("=" * 65)
    print("🤖 Starting Maroa Brian Robare's Personal Telegram Bot...")
    print(f"👤 Representing: {get_owner_name()}")
    print(f"🧠 Gemini AI: {'Connected ✅' if GEMINI_API_KEY else 'API key not set in .env ⚠️'}")
    print(f"📬 Forwarding Chat ID: {OWNER_CHAT_ID if OWNER_CHAT_ID else 'Not configured yet (Send /id to bot) ⚠️'}")
    print("=" * 65)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("about", lambda u, c: u.message.reply_text(format_about_text(), parse_mode=constants.ParseMode.MARKDOWN)))
    app.add_handler(CommandHandler("skills", lambda u, c: u.message.reply_text(format_skills_text(), parse_mode=constants.ParseMode.MARKDOWN)))
    app.add_handler(CommandHandler("contact", lambda u, c: u.message.reply_text(format_contact_text(), parse_mode=constants.ParseMode.MARKDOWN)))
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot is LIVE! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()