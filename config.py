"""Configuration loader and profile data manager for Maroa Brian Robare's Bot."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_raw_owner_id = os.getenv("OWNER_CHAT_ID", "").strip()
OWNER_CHAT_ID = int(_raw_owner_id) if _raw_owner_id.isdigit() else None

PROFILE_PATH = BASE_DIR / "profile_data.json"


def load_profile() -> dict:
    """Loads profile data from profile_data.json."""
    if not PROFILE_PATH.exists():
        return {
            "personal_info": {"name": "Maroa Brian Robare", "title": "Technical BDR"},
            "contact": {"email": "maroabrian067@gmail.com"},
            "skills": [],
            "experience_and_projects": [],
            "faqs": [],
        }
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


PROFILE = load_profile()


def get_owner_name() -> str:
    return PROFILE.get("personal_info", {}).get("name", "Maroa Brian Robare")


def format_about_text() -> str:
    info = PROFILE.get("personal_info", {})
    name = info.get("name", "Maroa Brian Robare")
    title = info.get("title", "")
    location = info.get("location", "")
    bio = info.get("bio", "")
    status = info.get("status", "")

    lines = [
        f"👤 *About {name}*",
        f"💼 *Role:* {title}" if title else "",
        f"📍 *Location:* {location}" if location else "",
        f"🟢 *Status:* {status}" if status else "",
        "",
        bio,
    ]
    return "\n".join(line for line in lines if line is not None)


def format_skills_text() -> str:
    name = get_owner_name()
    skills = PROFILE.get("skills", [])
    projects = PROFILE.get("experience_and_projects", [])

    lines = [f"🛠 *Skills & Experience of {name}*", ""]
    if skills:
        lines.append("⚡ *Core Competencies:*")
        for skill in skills:
            lines.append(f"• {skill}")
        lines.append("")

    if projects:
        lines.append("🚀 *Featured Experience & Projects:*")
        for p in projects:
            title = p.get("title", "Project")
            org = p.get("organization", "")
            desc = p.get("description", "")
            link = p.get("link", "")
            header = f"{title} ({org})" if org else title

            if link:
                lines.append(f"• [{header}]({link})\n  {desc}\n")
            else:
                lines.append(f"• *{header}*\n  {desc}\n")

    return "\n".join(lines)


def format_contact_text() -> str:
    name = get_owner_name()
    contact = PROFILE.get("contact", {})
    social = PROFILE.get("social_links", {})

    lines = [f"📬 *Get in Touch with {name}*", ""]
    if contact.get("email"):
        lines.append(f"📧 *Email:* `{contact['email']}`")
    if contact.get("phone"):
        lines.append(f"📞 *Phone:* `{contact['phone']}`")
    if contact.get("preferred_contact_method"):
        lines.append(f"⭐ *Preferred:* {contact['preferred_contact_method']}")

    if social:
        lines.append("")
        lines.append("🌐 *Online Portfolios & Profiles:*")
        for platform, url in social.items():
            readable_name = platform.replace("_", " ").title()
            lines.append(f"• [{readable_name}]({url})")

    lines.append("")
    lines.append("💡 *Tip:* Click *'✉️ Leave a Message'* below to send a note straight to Brian's Telegram inbox!")
    return "\n".join(lines)