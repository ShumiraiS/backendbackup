import os
import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings

# Build the full path to serviceAccountKey.json (same folder as manage.py)
SERVICE_ACCOUNT_PATH = os.path.join(settings.BASE_DIR, "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://efflu-aibackend-default-rtdb.firebaseio.com/"
    })

def root_ref():
    return db.reference("/")
