def generate_response(intent):
    if isinstance(intent, dict):
        return intent.get("response", {}).get("message", "No response message provided.")
    else:
        return "Invalid intent format."