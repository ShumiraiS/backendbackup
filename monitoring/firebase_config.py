# monitoring/firebase_config.py
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, db


# This expects:
# 1) serviceAccountKey.json in the backend root folder (C:\effluai-backend\serviceAccountKey.json)
# 2) FIREBASE_DATABASE_URL set in env (recommended)
#
# Example FIREBASE_DATABASE_URL:
# https://<your-project-id>-default-rtdb.firebaseio.com/

BASE_DIR = Path(__file__).resolve().parent.parent
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT", str(BASE_DIR / "serviceAccountKey.json"))
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")


def init_firebase():
    """Initialise firebase_admin only once."""
    if firebase_admin._apps:
        return

    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(
            f"Firebase service account JSON not found at: {SERVICE_ACCOUNT_PATH}\n"
            f"Move your serviceAccountKey.json to: {BASE_DIR}\\serviceAccountKey.json "
            f"OR set env FIREBASE_SERVICE_ACCOUNT to its path."
        )

    if not FIREBASE_DATABASE_URL:
        raise ValueError(
            "FIREBASE_DATABASE_URL is missing.\n"
            "Set it in your environment, e.g.\n"
            'setx FIREBASE_DATABASE_URL "https://<your-project-id>-default-rtdb.firebaseio.com/"'
        )

    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})


def root_ref():
    """Return a reference to the root of the Realtime Database."""
    init_firebase()
    return db.reference("/")
