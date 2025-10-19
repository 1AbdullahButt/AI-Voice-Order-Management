import os
import openai
import json
import re
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_intent(transcribed_text):
    prompt = f"""
You are an AI assistant that extracts food order instructions from user messages and converts them into structured JSON actions.

Always return the response in this format:

{{
  "actions": [
    {{
      "type": "cancel",
      "item": "pizza"
    }},
    {{
      "type": "add",
      "item": "coke"
    }},
    {{
      "type": "change",
      "item": "burger",
      "modification": "large"
    }}
  ],
  "response": {{
    "message": "I have canceled your pizza, added a coke, and made your burger large."
  }}
}}

Rules:
- Return all actions mentioned in the user's message
- Each action must include `type` and `item`
- If the user changes an item (like size/type), include `modification`
- Respond only with the JSON. No greeting, no explanation

User message: {transcribed_text}
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a smart order assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_content = response.choices[0].message.content.strip()

    # 🛡 Try extracting JSON using regex
    match = re.search(r'\{.*\}', raw_content, re.DOTALL)
    if match:
        try:
            intent = json.loads(match.group())
            return intent
        except json.JSONDecodeError:
            print("⚠️ Error decoding JSON.")
    else:
        print("⚠️ No valid JSON found in model output.")

    # fallback if everything fails
    return {
        "actions": [],
        "response": {"message": "Sorry, I couldn't understand your request."}
    }