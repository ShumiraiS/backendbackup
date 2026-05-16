import os
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

SERVICE_ACCOUNT_PATH = r"c:\effluai-backend\serviceAccountKey.json"

# Create credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH, 
    scopes=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/firebase.database"]
)

# Get access token
request = google.auth.transport.requests.Request()
credentials.refresh(request)
token = credentials.token

# URL for RTDB
url = "https://efflu-aibackend-default-rtdb.firebaseio.com/ai_rules.json"

# Fetch data
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("AI_RULES:")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error {response.status_code}: {response.text}")
