# 🧠 AI Voice Order Management (Twilio + OpenAI + Google Sheets)

An end-to-end **AI voice assistant** that automatically calls customers, listens to their responses, understands intent, and updates Google Sheets — all without human input.

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

