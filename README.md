# 🧠 AI Voice Order Management (Twilio + OpenAI + Google Sheets)

An end-to-end **AI voice assistant** that automatically calls customers, listens to their responses, understands intent, and updates Google Sheets, all without human input.

---

## 🚀 Overview

This project simulates a restaurant or retail business that uses **AI-powered voice automation** to confirm or modify customer orders in real time.

### How it works
1. A new order is added in Google Sheets  
2. The bot (via Twilio) calls the customer  
3. The customer confirms or requests changes through voice  
4. **Whisper** transcribes the audio  
5. **GPT-4o** interprets the intent  
6. **Google Sheets API** updates the sheet automatically — no typing required  

---

## 🧩 Architecture

Google Sheets → Flask Webhook → Twilio Voice → Whisper (STT)
↓
GPT-4o (Intent)
↓
Google Sheets Update



### Example Flow
1. New row in Google Sheet → triggers API call to `/orders/call`
2. Flask endpoint uses Twilio API to start a voice call
3. User speaks → Twilio records → Flask receives recording → Whisper transcribes
4. GPT-4o processes text → extracts intent → updates Sheet via API
5. The order row updates (e.g., “NEW” → “CONFIRMED” or “UPDATED”)

---

## ⚙️ Tech Stack

| Component | Purpose |
|------------|----------|
| **Flask** | Local API + Twilio webhooks |
| **Twilio Voice API** | Calls & recordings |
| **OpenAI Whisper** | Speech-to-text |
| **GPT-4o** | Intent extraction & response logic |
| **Google Sheets API** | Data management |
| **Ngrok** | Local tunneling for Twilio webhooks |

---

## 🗂 Project Structure

AI-Voice-Order-Management/
├── flask_server.py # Flask app: Twilio webhooks + routing
├── call_from_sheet.py # Polls/reads Google Sheets and triggers calls
├── intent.py # (If used) GPT-4o intent extraction
├── transcribe.py # (If used) Whisper STT helper
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── LICENSE
└── archive/ # (Optional) parked legacy files


---


---

## 📄 Order Sheet Schema & Call Rules

Create a Google Sheet (name can be anything) and share it with your **service account email** (Editor). Recommended columns:

| Col | Field              | Type      | Example                                 |
|-----|--------------------|-----------|------------------------------------------|
| A   | `id`               | string    | `ORD-1023`                               |
| B   | `customer_name`    | string    | `Ali Khan`                               |
| C   | `phone`            | e164 str  | `+923001234567`                          |
| D   | `order_text`       | string    | `2x beef burgers, 1x fries`              |
| E   | `status`           | enum      | `NEW` / `CALLED` / `CONFIRMED` / `UPDATED` / `FAILED` |
| F   | `final_order_json` | json str  | `{"action":"confirm","items":[...]}`     |
| G   | `notes`            | string    | `no onions`                              |
| H   | `locked_at`        | datetime  | `2025-07-28T18:20:11Z`                   |
| I   | `last_updated`     | datetime  | `2025-07-28T18:22:30Z`                   |

**Call Rules (idempotent):**
- **Call only when** `status == NEW` **and** `locked_at` is empty.  
- When a worker picks a row, immediately set `locked_at=now()` and `status=CALLED` (prevents double-call).  
- After call + NLP:
  - On success **confirm**: set `status=CONFIRMED`, write `final_order_json`, update `last_updated`.
  - On success **modify**: set `status=UPDATED`, write `final_order_json`, update `last_updated`.
  - On error/no answer: set `status=FAILED`, clear `locked_at`.
- Re-runner logic: rows with `FAILED` can be retried manually; `CALLED` rows shouldn’t be re-dialed unless you reset them to `NEW`.

---

## 🧠 Workflow Breakdown

| Step | Action | Tool |
|-----:|--------|------|
| 1 | Detect new order (`status=NEW`) | Google Sheets API |
| 2 | Outbound call to customer | Twilio |
| 3 | Customer speaks (confirm/change) | Twilio Recording |
| 4 | Convert speech → text | Whisper |
| 5 | Interpret intent & normalize JSON | GPT-4o |
| 6 | Update row (status + JSON + timestamps) | Sheets API |

---

## 🧰 Setup Guide

### 1) Clone

git clone https://github.com/<your-username>/AI-Voice-Order-Management.git
cd AI-Voice-Order-Management


### 2️⃣ Install Dependencies

python -m venv .venv
source .venv/bin/activate     # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

### 3️⃣ Create .env File

Create a .env file in the root directory and add:

- ngrok
PUBLIC_BASE_URL=https://<your-ngrok-subdomain>.ngrok.io

- Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

- OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

- Google Sheets
GOOGLE_SERVICE_ACCOUNT_JSON='.json' file location (downloaded via Google Console)
ORDERS_SHEET_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ORDERS_SHEET_NAME=Sheet1

### 4️⃣ Start Ngrok

ngrok http 5000
Copy the HTTPS forwarding URL and update it under APP_BASE_URL.

### 5️⃣ Run Flask App
python app.py

---

📞 Twilio Setup

Go to Twilio Console → Phone Numbers → Active Number → Voice Settings

Set:

- Voice Webhook (POST): https://<your-ngrok>.ngrok.io/voice/incoming
- Status Callback (POST): https://<your-ngrok>.ngrok.io/voice/status

---

🧾 Google Sheets Setup

Create a Google Sheet titled Orders with columns:

| Column | Name             | Description                        |
| ------ | ---------------- | ---------------------------------- |
| A      | ID               | Unique order ID                    |
| B      | Customer Name    | Name of customer                   |
| C      | Phone            | Twilio-callable number             |
| D      | Order Details    | e.g., “2x Burgers, 1x Fries”       |
| E      | Status           | NEW / CALLED / CONFIRMED / UPDATED |
| F      | Final Order JSON | GPT’s structured output            |
| G      | Notes            | System remarks                     |
| H      | Last Updated     | Timestamp                          |

Share the sheet with your Google Service Account email (Editor).

---

🧭 API Endpoints

| Endpoint          | Method | Description                            |
| ----------------- | ------ | -------------------------------------- |
| `/orders/call`    | POST   | Trigger outbound call                  |
| `/voice/incoming` | POST   | Receives Twilio call events            |
| `/voice/gather`   | POST   | Handles speech & Whisper transcription |
| `/voice/status`   | POST   | Optional Twilio call status callback   |
| `/health`         | GET    | Test endpoint                          |

Example Test

curl -X POST https://<your-ngrok>.ngrok.io/orders/call \
  -H "Content-Type: application/json" \
  -d '{"row_id": "2"}'

---

🧩 GPT Output Format

Example GPT response:

{
  "action": "confirm",
  "items": [
    {"name": "burger", "qty": 2},
    {"name": "fries", "qty": 1}
  ],
  "notes": "extra spicy",
  "confirmed": true
}

This JSON is written to Final Order JSON in the Sheet, and the status updates automatically.

---

💾 Deployment (Optional)

You can deploy on Render, Railway, or Fly.io:

- Push your repo

- Add all .env variables

- Add Procfile → web: python app.py

- Update Twilio webhook URLs with the deployed domain

---

🧯 Troubleshooting

| Issue                     | Fix                                                 |
| ------------------------- | --------------------------------------------------- |
| **Webhook 403/404**       | Ensure your ngrok URL matches `.env` and Twilio     |
| **Sheet not updating**    | Share with the correct service account email        |
| **Whisper error**         | Ensure audio is accessible & `OPENAI_API_KEY` valid |
| **Double calls**          | Add a “lock” column to avoid duplicate triggers     |
| **Speech not recognized** | Try record-then-transcribe flow                     |

---

🧩 Example Call Flow

Bot: “Hi John, I’m calling to confirm your order of 2 beef burgers and 1 fries. Would you like to confirm or make changes?”
User: “Make it 3 burgers instead.”
Bot: “Got it. Updated your order to 3 beef burgers and 1 fries. Thank you!”
→ Sheet updates automatically.
