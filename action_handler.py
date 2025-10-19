# import json
# import os

# def apply_actions(intent):
#     order = {
#         "order_id": 1234,
#         "items": [
#             {"name": "drink", "status": "active", "size": "medium"},
#             {"name": "fries", "status": "active", "size": "regular"},
#             {"name": "burger", "status": "active", "size": "regular"}
#         ]
#     }

#     existing_items = {item["name"]: item for item in order["items"]}

#     for action in intent.get("actions", []):
#         item_name = action.get("item", "").lower()
#         action_type = action.get("type")

#         if action_type == "cancel":
#             if item_name in existing_items:
#                 existing_items[item_name]["status"] = "cancelled"

#         elif action_type == "change":
#             if item_name in existing_items:
#                 existing_items[item_name]["size"] = action.get("modification", "regular")
#             else:
#                 existing_items[item_name] = {
#                     "name": item_name,
#                     "status": "active",
#                     "size": action.get("modification", "regular")
#                 }

#         elif action_type == "add":
#             if item_name not in existing_items:
#                 existing_items[item_name] = {
#                     "name": item_name,
#                     "status": "active",
#                     "size": "standard"
#                 }

#     order["items"] = list(existing_items.values())
#     return order


# # Test example
# intent_json = {
#     "actions": [
#         {"type": "cancel", "item": "drink"},
#         {"type": "change", "item": "fries", "modification": "large"},
#         {"type": "add", "item": "ketchup"},
#         {"type": "add", "item": "double cheeseburger"}
#     ],
#     "response": {
#         "message": "I have canceled your drink, made your fries large, and added ketchup and a double cheeseburger."
#     }
# }

# cleaned_order = apply_actions(intent_json)


# action_handler.py

# action_handler.py

import gspread
from google.oauth2.service_account import Credentials
import json
import os

# Load credentials from your JSON key file
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Google Sheet setup
SHEET_ID = '1JCFAXYYokF4N_FnUgzOgeKI-ZbpcrA8NTCH71tHdc5Y'  # ← only the ID, not the whole URL
SHEET_NAME = 'Sheet1'  # or whatever your tab is named
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def apply_actions(intent: dict):
    # Fetch existing data into a list of dicts
    records = sheet.get_all_records()

    for action in intent.get("actions", []):
        action_type = action.get("type")
        item_name = action.get("item", "").lower()

        if action_type == "cancel":
            for row_idx, row in enumerate(records):
                if row["name"].lower() == item_name:
                    sheet.update_cell(row_idx + 2, 2, "cancelled")  # status column
                    break

        elif action_type == "change":
            for row_idx, row in enumerate(records):
                if row["name"].lower() == item_name:
                    sheet.update_cell(row_idx + 2, 3, action.get("modification", "standard"))  # size column
                    break

        elif action_type == "add":
            sheet.append_row([item_name, "active", "standard"])

    return sheet.get_all_records()  # Return updated records