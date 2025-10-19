# call_handler.py

from twilio.rest import Client
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_SID, TWILIO_TOKEN)

def make_call(to_number: str, user_message: str):
    # URL-encode the dynamic message
    encoded_message = urllib.parse.quote(f"<Response><Say>{user_message}</Say></Response>")

    # Twimlets will read the message
    twiml_url = f"http://twimlets.com/echo?Twiml={encoded_message}"

    # Create the call
    call = client.calls.create(
        to=to_number,
        from_=TWILIO_NUMBER,
        url=twiml_url
    )

    print(f"🔔 Call initiated! SID: {call.sid}")