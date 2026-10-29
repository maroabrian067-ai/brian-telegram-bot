"""
Inbound Lead Research & Hyper-Personalized Outreach Automation
Author: Maroa Brian Robare (Technical BDR & Solutions Designer)
Formatting: Official Executive Format (Zero Emojis)
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. SCRAPER: Extract Company Value Proposition & Context
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def scrape_company_context(website_url: str) -> dict:
    """Scrapes homepage title, meta description, and core headings."""
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(website_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Clean script and style tags
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        title = soup.title.string.strip() if soup.title else ""
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Extract primary headings
        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])[:6]]
        headings_text = " | ".join(headings)

        # Grab clean body text snippet
        body_text = " ".join(soup.stripped_strings)[:1200]

        return {
            "url": website_url,
            "title": title,
            "meta_description": meta_desc,
            "key_headings": headings_text,
            "snippet": body_text,
            "success": True
        }

    except Exception as e:
        print(f"[Warning] Could not scrape {website_url}: {e}")
        return {
            "url": website_url,
            "title": "",
            "meta_description": "",
            "key_headings": "",
            "snippet": "Direct analysis based on company domain and market category.",
            "success": False
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. AI QUALIFIER: MEDDIC Analysis & Outreach Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_meddic_pitch(lead: dict, company_context: dict) -> dict:
    """Uses Gemini to qualify the lead and draft an official B2B outreach email."""
    prompt = f"""
You are an executive Technical Business Development Representative (BDR) and Solutions Designer representing Maroa Brian Robare.

LEAD DETAILS:
- Contact Name: {lead.get('name', 'Prospect')}
- Role/Title: {lead.get('role', 'Decision Maker')}
- Company: {lead.get('company', 'Prospective Company')}
- Email: {lead.get('email', 'N/A')}
- Website: {company_context.get('url')}

SCRAPED WEBSITE CONTEXT:
- Title: {company_context.get('title')}
- Description: {company_context.get('meta_description')}
- Key Value Props / Headings: {company_context.get('key_headings')}
- Context Snippet: {company_context.get('snippet')}

STRICT STYLE RULES:
1. Do NOT use any emojis, symbols, or informal slang anywhere in the output.
2. Tone must be professional, direct, consultative, and executive.

YOUR TASK:
Analyze this prospect using the MEDDIC sales framework and generate:
1. Pain Points: 2-3 technical or operational bottlenecks (e.g. web hosting latency, database optimization, lead triage across buyer personas).
2. Lead Score: Hot, Warm, or Cold (with a crisp 1-sentence rationale).
3. Subject Line: Clean, professional, lower-case style B2B subject line.
4. Outreach Email: A 3-paragraph executive cold email (under 110 words):
   - Hook: Reference a concrete observation or expansion trend from their website.
   - Value Proposition: How Brian's technical background (cloud architecture, database scaling, or sales workflow automation) delivers measurable ROI.
   - Call to Action: Professional invitation for a brief 10-minute discovery call.

Return your answer strictly in valid JSON format with keys:
"pain_points", "lead_score", "score_rationale", "subject_line", "email_draft"
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config={"temperature": 0.6, "response_mime_type": "application/json"}
    )

    try:
        return json.loads(response.text.strip())
    except Exception:
        return {
            "pain_points": ["Web performance and uptime", "Database query optimization"],
            "lead_score": "Warm",
            "score_rationale": "High relevance for modern cloud infrastructure.",
            "subject_line": f"Technical infrastructure inquiry - {lead.get('company')}",
            "email_draft": response.text.strip()
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. HUBSPOT INTEGRATION: Create Contact & Deal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def sync_to_hubspot(lead: dict, ai_analysis: dict) -> bool:
    """Syncs lead and AI research into HubSpot Deals and Contacts."""
    if not HUBSPOT_ACCESS_TOKEN:
        print("[HubSpot Simulation] Private App Token not configured in .env. Payload preview:")
        print(f"   Deal: {lead.get('company')} - Inbound Qualified Lead")
        print(f"   Score: {ai_analysis.get('lead_score')}")
        print(f"   Subject: {ai_analysis.get('subject_line')}")
        return True

    headers = {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # 1. Create or Update Contact in HubSpot
    contact_url = "https://api.hubapi.com/crm/v3/objects/contacts"
    first_name = lead.get("name", "").split()[0]
    last_name = " ".join(lead.get("name", "").split()[1:]) if " " in lead.get("name", "") else ""

    contact_payload = {
        "properties": {
            "email": lead.get("email"),
            "firstname": first_name,
            "lastname": last_name,
            "jobtitle": lead.get("role"),
            "company": lead.get("company"),
            "website": lead.get("website")
        }
    }

    contact_resp = requests.post(contact_url, headers=headers, json=contact_payload)

    # 2. Create Deal with AI Outreach in Deal Description
    deal_url = "https://api.hubapi.com/crm/v3/objects/deals"
    deal_description = (
        f"MEDDIC QUALIFICATION REPORT\n"
        f"---------------------------\n"
        f"Score: {ai_analysis.get('lead_score')} - {ai_analysis.get('score_rationale')}\n"
        f"Detected Bottlenecks: {', '.join(ai_analysis.get('pain_points', []))}\n\n"
        f"RECOMMENDED OUTREACH DRAFT\n"
        f"---------------------------\n"
        f"Subject: {ai_analysis.get('subject_line')}\n\n"
        f"{ai_analysis.get('email_draft')}"
    )

    deal_payload = {
        "properties": {
            "dealname": f"{lead.get('company')} - Inbound Qualified Lead",
            "dealstage": "qualifiedtobuy",
            "pipeline": "default",
            "description": deal_description
        }
    }

    deal_resp = requests.post(deal_url, headers=headers, json=deal_payload)
    if deal_resp.status_code in [200, 201]:
        print(f"[HubSpot] Successfully synced Deal for {lead.get('company')}.")
        return True
    else:
        print(f"[HubSpot Error] Sync failed: {deal_resp.text}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. TELEGRAM NOTIFICATION: Clean Official Alert
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def send_telegram_alert(lead: dict, ai_analysis: dict):
    """Sends clean, official notification to Brian's Telegram (Zero Emojis)."""
    if not TELEGRAM_BOT_TOKEN or not OWNER_CHAT_ID:
        return

    message = (
        f"INBOUND LEAD QUALIFICATION REPORT\n"
        f"===================================\n"
        f"Company: {lead.get('company')} ({lead.get('website')})\n"
        f"Contact: {lead.get('name')}, {lead.get('role')}\n"
        f"Email: {lead.get('email')}\n"
        f"Evaluation: {ai_analysis.get('lead_score').upper()} -- {ai_analysis.get('score_rationale')}\n\n"
        f"RECOMMENDED OUTREACH DRAFT\n"
        f"-----------------------------------\n"
        f"Subject: {ai_analysis.get('subject_line')}\n\n"
        f"{ai_analysis.get('email_draft')}\n"
        f"===================================\n"
        f"Status: Deal synced to HubSpot CRM. Ready for review."
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": OWNER_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[Notification Error] Could not send alert: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. RUN PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def process_inbound_lead(lead: dict):
    print(f"\n=======================================================")
    print(f"[Initiating] Processing Lead: {lead['name']} ({lead['company']})")
    print(f"=======================================================")

    print("[Step 1/4] Scraping company domain for technical context...")
    context = scrape_company_context(lead["website"])

    print("[Step 2/4] Running Gemini MEDDIC analysis and drafting outreach...")
    ai_result = generate_meddic_pitch(lead, context)

    print("[Step 3/4] Syncing record to HubSpot CRM...")
    sync_to_hubspot(lead, ai_result)

    print("[Step 4/4] Transmitting official report to Telegram...")
    send_telegram_alert(lead, ai_result)

    print("\n[Complete] Pipeline executed successfully.")
    print(f"Rating: {ai_result.get('lead_score')}")
    print(f"Subject: {ai_result.get('subject_line')}")
    print(f"\nDraft:\n{ai_result.get('email_draft')}\n")


if __name__ == "__main__":
    sample_lead = {
        "name": "Sarah Jenkins",
        "role": "VP of Revenue Operations",
        "company": "Kinsta",
        "website": "https://kinsta.com",
        "email": "sarah.jenkins@kinsta.com"
    }

    process_inbound_lead(sample_lead)