# Technical BDR Inbound Research & MEDDIC Outreach Automation

**Author:** Maroa Brian Robare  
**Role:** Technical Business Development Representative (BDR) & Solutions Designer  
**Focus:** Sales Workflow Automation, CRM Architecture, Generative AI Integration  

---

## 1. Executive Summary

Traditional business development requires representatives to spend 20 to 30 minutes per inbound lead manually conducting account research, deducing pain points, formulating outreach copy, and updating CRM records.

This automation pipeline replaces that manual process with an automated Python workflow:
1. Extracts technical and commercial context from a prospect's domain.
2. Applies the MEDDIC sales qualification framework using Google Gemini AI to analyze bottlenecks.
3. Automatically synthesizes an executive, hyper-personalized outreach draft.
4. Creates a synchronized Contact and Deal inside HubSpot CRM.
5. Transmits an official notification to a private Telegram communication channel.

Business Outcome: Reduces inbound account qualification turnaround time from 25 minutes to under 5 seconds while eliminating data hygiene errors in CRM pipelines.

---

## 2. System Architecture

Workflow:
Inbound Lead -> Web Scraper (BeautifulSoup) -> Gemini 3.8 AI (MEDDIC Engine) -> HubSpot CRM Sync -> Telegram Executive Alert

---

## 3. Technology Stack

- Language: Python 3.10+
- AI Intelligence: Google Gemini API (gemini-3.8-flash)
- Web Extraction: BeautifulSoup4, Requests
- CRM Platform: HubSpot REST API (v3 Objects: Contacts & Deals)
- Delivery Protocol: Telegram Bot API
- Environment Management: Python-Dotenv

---

## 4. Configuration & Environment Variables

The system relies on the following environment variables in .env:

- GEMINI_API_KEY: Google Gemini AI API Key
- HUBSPOT_ACCESS_TOKEN: HubSpot Private App Token (Scopes: contacts read/write, deals read/write)
- TELEGRAM_BOT_TOKEN: Telegram Bot Token
- OWNER_CHAT_ID: Numeric Telegram User ID

---

## 5. Pipeline Component Breakdown

### 5.1 Web Extraction (scrape_company_context)
- Extracts title, meta description, structural headings, and clean text snippets from the prospect's homepage.
- Cleans style and script elements to isolate core value propositions.

### 5.2 MEDDIC AI Qualification (generate_meddic_pitch)
- Evaluates technical bottlenecks and buyer persona alignment.
- Generates structured JSON: pain points, lead score, rationale, subject line, and outreach email draft.
- Enforces an executive, corporate tone with zero informal emojis.

### 5.3 HubSpot CRM Synchronization (sync_to_hubspot)
- Creates or updates the Contact record in HubSpot.
- Creates a Deal in the qualified pipeline stage with the full MEDDIC qualification notes attached.

### 5.4 Delivery Dispatch (send_telegram_alert)
- Transmits an executive briefing directly to the BDR's smartphone in seconds for immediate review.

---

## 6. Live Execution Case Study (Kinsta)

- Company: Kinsta (https://kinsta.com)
- Prospect: Sarah Jenkins, VP of Revenue Operations
- Evaluation: WARM -- Kinsta is expanding from managed WordPress into application and database hosting, creating sales triage complexity.
- Recommended Subject: kinsta's multi-product expansion and revops workflow
- Outcome: Complete cold pitch generated and deal populated in HubSpot automatically.

---

## 7. Strategic Value & Interview Talking Points

- Resume Bullet: Architected an automated inbound lead research pipeline integrating Python, Gemini 3.8, and HubSpot APIs, reducing account qualification time from 25 minutes to under 5 seconds.
- Interview Response: "In modern sales, speed-to-lead and relevance determine conversion rates. Rather than relying on generic bulk email tools or spending hours manually browsing company sites, I designed a full-stack Python automation. It scrapes an inbound prospect's web infrastructure, analyzes their business model through the MEDDIC framework using Gemini AI, populates a fully documented deal inside HubSpot, and alerts my mobile phone via Telegram with a ready-to-send draft."