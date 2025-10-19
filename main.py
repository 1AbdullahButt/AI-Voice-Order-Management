import os
from transcribe import transcribe_audio
from intent import extract_intent
from action_handler import apply_actions
from response import generate_response
from call_handler import make_call  # ← NEW import

# Set your audio file path
audio_path = "audio/sample_voice.mp3"

# Step 1: Transcribe audio to text
text = transcribe_audio(audio_path)
print("\n--- Transcribed Text ---")
print(text)

# Step 2: Send text to GPT for intent extraction
intent_json = extract_intent(text)
print("\n--- Extracted Intent ---")
print(intent_json)

# Step 3: Apply actions to the mock database
updated_order = apply_actions(intent_json)
print("\n--- Updated Order ---")
print(updated_order)

# Step 4: Generate a human-readable response
final_response = generate_response(intent_json)
print("\n--- Response to User ---")
print(final_response)

# ✅ Step 5: Make a call and speak the response
user_phone = "+923053977706"  # ← Your test phone number here
make_call(user_phone, final_response)
