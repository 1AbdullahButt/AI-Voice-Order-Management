from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI
from dotenv import load_dotenv
import os, io, requests, threading
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ------- tweakable: menu terms to preserve/normalize -------
MENU_TERMS = [
    "Fajita pizza", "Pepperoni pizza", "Zinger burger", "Cheeseburger",
    "Fries", "Large fries", "Medium fries", "Coke", "Diet Coke",
    "Large Coke", "Medium Coke"
]

# ---------- Google Sheets ----------
def _open_orders_sheet():
    sa_path    = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id   = os.environ.get("ORDERS_SHEET_ID")
    sheet_name = os.environ.get("ORDERS_SHEET_NAME", "Sheet1")
    print("→ Using SA file:", sa_path, "| Exists?", os.path.exists(sa_path))
    print("→ Sheet ID:", sheet_id, "| Worksheet:", sheet_name)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds  = Credentials.from_service_account_file(sa_path, scopes=scopes)
    gc     = gspread.authorize(creds)
    sh     = gc.open_by_key(sheet_id)
    return sh.worksheet(sheet_name)

def _find_row_by_order_id(order_id: str) -> int:
    ws = _open_orders_sheet()
    cell = ws.find(str(order_id), in_column=1)  # Col A
    if not cell:
        raise RuntimeError(f"Order ID {order_id} not found")
    return cell.row

def _update_cells(row: int, *, status=None, call_text=None, updated_order=None):
    ws = _open_orders_sheet()
    if status is not None:
        ws.update_cell(row, 5, status)         # E: Status
    if call_text is not None:
        ws.update_cell(row, 6, call_text)      # F: Call (we store transcript)
    if updated_order is not None:
        ws.update_cell(row, 7, updated_order)  # G: Updated Order

# ---------- Twilio recording download ----------
def _download_recording(recording_url_base: str) -> bytes:
    sid   = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    url   = recording_url_base.strip() + ".mp3"
    r = requests.get(url, auth=(sid, token), timeout=30)
    r.raise_for_status()
    return r.content

# ---------- Whisper ----------
def _transcribe_with_whisper(mp3_bytes: bytes) -> str:
    f = io.BytesIO(mp3_bytes); f.name = "user_input.mp3"
    tx = client.audio.transcriptions.create(model="whisper-1", file=f)
    return (tx.text or "").strip()

# ---------- Single GPT pass: classify + rewrite ----------
def _analyze_and_rewrite(transcript: str, original_order: str) -> dict:
    """
    Returns dict: {"decision": "accurate"|"changes", "updated_line": "<one-line order>"}
    - If accurate, updated_line should equal original_order.
    - If changes, updated_line should be a clean, POS-friendly one-liner.
    """
    menu_hint = "; ".join(MENU_TERMS)
    sys = (
        "You are helping a restaurant confirm orders from a phone transcript. "
        "You must:\n"
        "1) Decide if the caller confirmed ('accurate') or requested 'changes'. "
        "   Treat phrases like 'yes', 'correct', 'no changes', 'keep same', 'as is', 'it's fine' as 'accurate'.\n"
        "2) Produce ONE concise POS-friendly line for the final order as 'updated_line'.\n"
        "   - If decision is 'accurate': set updated_line = original_order exactly.\n"
        "   - If 'changes': rewrite clearly with quantities/sizes if stated.\n"
        "   - Preserve menu terms exactly if clear. Menu terms: " + menu_hint + ".\n"
        "   - Do NOT invent items.\n"
        "Return ONLY strict JSON: {\"decision\":\"accurate|changes\",\"updated_line\":\"...\"}"
    )
    user = f"original_order: {original_order}\ntranscript: {transcript}"
    chat = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content": sys},
            {"role":"user","content": user}
        ],
        temperature=0
    )
    content = (chat.choices[0].message.content or "").strip()
    # super small guard: if model ever fails JSON, force 'changes' and reuse transcript
    try:
        import json as _json
        data = _json.loads(content)
        dec = (data.get("decision","") or "").lower()
        if dec not in ("accurate","changes"):
            dec = "changes"
        upd = data.get("updated_line","") or (original_order if dec=="accurate" else transcript)
        return {"decision": dec, "updated_line": upd}
    except Exception:
        return {"decision": "changes", "updated_line": transcript}

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def root():
    return "OK — POST /voice?order_id=..."

@app.route("/voice", methods=["POST"])
def voice():
    order_id = request.args.get("order_id")
    resp = VoiceResponse()
    if not order_id:
        resp.say("Missing order information. Please try again later.", voice="alice")
        return Response(str(resp), mimetype="text/xml")

    resp.say("This is your order confirmation call.", voice="alice")
    resp.say("After the beep, say 'accurate' to confirm, or say your changes.", voice="alice")
    resp.record(
        timeout=2,
        transcribe=False,
        max_length=30,
        action=f"/process-recording?order_id={order_id}",
        method="POST"
    )
    return Response(str(resp), mimetype="text/xml")

@app.route("/process-recording", methods=["POST"])
def process_recording():
    print("\n--- Incoming Form Data ---")
    print(dict(request.form))
    print("--------------------------\n")

    order_id      = request.args.get("order_id")
    recording_url = request.form.get("RecordingUrl")

    # Fast-ACK so Twilio doesn't timeout
    resp = VoiceResponse()
    if not order_id or not recording_url:
        resp.say("Sorry, missing information. Please try again later.", voice="alice")
        return Response(str(resp), mimetype="text/xml")

    threading.Thread(
        target=_background_process_recording,
        args=(order_id, recording_url),
        daemon=True
    ).start()

    resp.say("Thanks! I’m updating your order now.", voice="alice")
    return Response(str(resp), mimetype="text/xml")

# ---------- Background worker ----------
def _background_process_recording(order_id: str, recording_url: str):
    print(f"▶️ BG start for order {order_id}")
    try:
        # Optional: mark Processing
        try:
            row = _find_row_by_order_id(order_id)
            _update_cells(row, status="Processing")
        except Exception as e:
            print("   (warn) couldn't mark Processing:", repr(e))

        audio_bytes = _download_recording(recording_url)
        transcript  = _transcribe_with_whisper(audio_bytes)
        print(f"   📝 Transcript: {transcript}")

        row = _find_row_by_order_id(order_id)
        ws  = _open_orders_sheet()
        original_order = ws.acell(f"D{row}").value or ""
        print(f"   📄 Original@D{row}: {original_order}")

        result = _analyze_and_rewrite(transcript, original_order)
        decision = result["decision"]
        updated  = result["updated_line"]
        print(f"   🔎 Decision: {decision}")
        print(f"   ✍️ Updated: {updated}")

        # Write once
        final_status = "Confirmed" if decision == "accurate" else "Changed"
        _update_cells(row, status=final_status, call_text=transcript, updated_order=updated)
        print(f"   ✅ Wrote E/F/G for row {row}")

    except Exception as e:
        print("❌ BG Error:", repr(e))
        try:
            row = _find_row_by_order_id(order_id)
            _update_cells(row, status="Failed")
        except Exception:
            pass
    finally:
        print(f"⏹️ BG end for order {order_id}")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    print("OPENAI_API_KEY loaded:", bool(os.environ.get("OPENAI_API_KEY")))
    print("TWILIO creds loaded:", bool(os.environ.get("TWILIO_ACCOUNT_SID")) and bool(os.environ.get("TWILIO_AUTH_TOKEN")))
    print("SHEETS path present:", bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")))
    print("SHEET ID present:", bool(os.environ.get("ORDERS_SHEET_ID")))
    print("SHEET NAME:", os.environ.get("ORDERS_SHEET_NAME", "Sheet1"))
    app.run(host="0.0.0.0", port=5000, debug=True)
