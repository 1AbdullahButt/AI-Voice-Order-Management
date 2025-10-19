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
6. **Google Sheets API** updates the sheet automatically. NO TYPING REQUIRED  

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

```text
AI-Voice-Order-Management/
├── flask_server.py          # Flask app: Twilio webhooks + routing
├── call_from_sheet.py       # Polls/reads Google Sheets and triggers calls
├── intent.py                # (If used) GPT-4o intent extraction
├── transcribe.py            # (If used) Whisper STT helper
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── LICENSE

```
---

## 📄 Order Sheet Schema & Call Rules (Used by `call_from_sheet.py`)

Create a Google Sheet (name can be anything) and share it with your **service account email** (Editor).

Your sheet should have **these exact columns** in this order:

| Column | Header           | Description |
|---------|------------------|--------------|
| A | **Order ID** | Unique ID for each order (e.g., ORD-101) |
| B | **Name** | Customer name |
| C | **Phone** | Customer’s phone number in E.164 format (e.g., +xxxxxx) |
| D | **Original Order** | The original order text added by the restaurant (e.g., “2x Burgers, 1x Fries”) |
| E | **Status** | Tracks call progress — must be one of `NEW`, `CALLED`, `CONFIRMED`, or `UPDATED` |
| F | **Call** | Internal marker used to record if a call was made successfully |
| G | **Updated Order** | The final updated order text or JSON response returned by GPT |

### 🧩 Sheet Logic

- A **call is made** only when `Status` = `NEW`.  
- Once the call starts, the bot immediately updates the row:
  - Sets **Status → CALLED** to prevent duplicate calls.
- After user response and GPT processing:
  - If order confirmed → `Status → CONFIRMED`
  - If changes requested → `Status → UPDATED`
  - The updated order is written to **Updated Order** column.
- Rows marked `CALLED`, `CONFIRMED`, or `UPDATED` **will not be called again** unless manually changed back to `NEW`.

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
  - PUBLIC_BASE_URL=https://<your-ngrok-subdomain>.ngrok.io

- Twilio
  - TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

- OpenAI
  - OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

- Google Sheets
  - GOOGLE_SERVICE_ACCOUNT_JSON='.json' file location (downloaded via Google Console)
  - ORDERS_SHEET_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - ORDERS_SHEET_NAME=Sheet1

### ▶️ Exact Run Order (no guesswork)

1. Start Flask server
   
    python flask_server.py

2. Expose with ngrok

    ngrok http 5000

    Copy the https://<id>.ngrok.io URL and set it as APP_BASE_URL in .env

3. Set Twilio webhooks (Console → Phone Numbers → Active Number → Voice):

  - Voice Webhook (POST): https://<ngrok>.ngrok.io/voice/incoming

  - Status Callback (POST): https://<ngrok>.ngrok.io/voice/status

4. Trigger calls

    Open another terminal window while Flask + ngrok are running, then execute:

    python call_from_sheet.py

  - This will scan for rows where status=NEW and dial them.
---

🧭 API Endpoints

| Endpoint          | Method | Description                            |
| ----------------- | ------ | -------------------------------------- |
| `/orders/call`    | POST   | Trigger outbound call                  |
| `/voice/incoming` | POST   | Receives Twilio call events            |
| `/voice/gather`   | POST   | Handles speech & Whisper transcription |
| `/voice/status`   | POST   | Optional Twilio call status callback   |
| `/health`         | GET    | Test endpoint                          |


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
```text
Bot: “Hi John, I’m calling to confirm your order of 2 beef burgers and 1 fries. Would you like to confirm or make changes?”
User: “Make it 3 burgers instead.”
Bot: “Got it. Updated your order to 3 beef burgers and 1 fries. Thank you!”
→ Sheet updates automatically.
```
