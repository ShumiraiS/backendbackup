import os
import json
import firebase_admin
from firebase_admin import credentials, db

# Since this script runs from the backend directory, serviceAccountKey.json is in the same directory.
SERVICE_ACCOUNT_PATH = os.path.join(os.getcwd(), "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://efflu-aibackend-default-rtdb.firebaseio.com/"
    })

ref = db.reference("/")
rules = ref.child("ai_rules").get()
print(json.dumps(rules, indent=2))
