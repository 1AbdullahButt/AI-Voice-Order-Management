import os, time
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# ---- Env
SA_FILE    = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
SHEET_ID   = os.environ.get("ORDERS_SHEET_ID")
SHEET_NAME = os.environ.get("ORDERS_SHEET_NAME", "Sheet1")

TW_SID  = os.environ["TWILIO_ACCOUNT_SID"]
TW_TOK  = os.environ["TWILIO_AUTH_TOKEN"]
TW_FROM = os.environ.get("TWILIO_FROM_NUMBER") or os.environ.get("TWILIO_PHONE_NUMBER")
if not TW_FROM:
    raise RuntimeError("Set TWILIO_FROM_NUMBER or TWILIO_PHONE_NUMBER in .env")

PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"]  # https base, no /voice

# ---- Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds  = Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
gc     = gspread.authorize(creds)
sheet  = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ---- Twilio
tclient = Client(TW_SID, TW_TOK)
TERMINAL_STATES = {"completed", "busy", "no-answer", "failed", "canceled"}

def normalize_pk_phone(raw: str) -> str:
    if not raw: return ""
    p = raw.strip().replace(" ", "").replace("-", "")
    if p.startswith("+"): return p
    return "+92" + p.lstrip("0")

def wait_until_call_finishes(call_sid: str, poll_sec: float = 3.0, max_wait_sec: int = 300) -> str:
    waited = 0
    while waited < max_wait_sec:
        call = tclient.calls(call_sid).fetch()
        status = (call.status or "").lower()
        print(f"   ↳ Call {call_sid} status: {status}")
        if status in TERMINAL_STATES:
            return status
        time.sleep(poll_sec)
        waited += poll_sec
    return "timeout"

def main():
    print("PUBLIC_BASE_URL =", PUBLIC_BASE_URL)
    print("TWILIO_FROM_NUMBER =", TW_FROM)

    rows = sheet.get_all_values()
    if not rows:
        print("Sheet is empty."); return

    header = [h.strip() for h in rows[0]]
    expected = ["Order ID", "Name", "Phone", "Original Order", "Status", "Call", "Updated Order"]
    for col in expected:
        if col not in header: print(f"⚠️ Missing column: {col}")
    idx = {col: (header.index(col) + 1) for col in header}

    for r, row in enumerate(rows[1:], start=2):
        row = (row + [""] * 7)[:7]
        order_id, name, phone, original_order, status, call_flag, updated_order = row

        if not order_id or not phone:
            continue
        if (call_flag or "").strip().lower() != "yes":
            continue
        if (status or "").strip().lower() not in ("new", "retry"):
            continue

        to_number = normalize_pk_phone(phone)
        if not to_number:
            print(f"⚠️ Skipping row {r}: bad phone '{phone}'")
            sheet.update_cell(r, idx.get("Status", 5), "Failed")
            continue

        try:
            base = PUBLIC_BASE_URL.rstrip("/")
            webhook_url = f"{base}/voice?order_id={order_id}"
            print(f"📞 Dialing row {r} -> {name} ({to_number}) | OrderID={order_id}")

            call = tclient.calls.create(
                to=to_number,
                from_=TW_FROM,
                url=webhook_url,
                method="POST"
            )

            if "Status" in idx:
                sheet.update_cell(r, idx["Status"], "Called")
            if "Call" in idx:
                sheet.update_cell(r, idx["Call"], call.sid)

            # wait for this call to finish before next row
            final_status = wait_until_call_finishes(call.sid, poll_sec=3.0, max_wait_sec=300)
            print(f"   ✅ Call finished with status: {final_status}")

            time.sleep(3)  # small gap before the next call

        except Exception as e:
            err = str(e)
            print(f"❌ Row {r} call failed: {err}")
            if "21219" in err or "unverified" in err.lower():
                sheet.update_cell(r, idx["Status"], "Unverified Number")
                sheet.update_cell(r, idx["Call"], "TWILIO_21219")
            else:
                sheet.update_cell(r, idx["Status"], "Failed")

if __name__ == "__main__":
    main()
