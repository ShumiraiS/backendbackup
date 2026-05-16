import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

SERVICE_ACCOUNT_PATH = r"c:\effluai-backend\serviceAccountKey.json"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH, 
    scopes=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/firebase.database"]
)

request = google.auth.transport.requests.Request()
credentials.refresh(request)
token = credentials.token

url = "https://efflu-aibackend-default-rtdb.firebaseio.com/thresholds.json"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(url, headers=headers)

print("THRESHOLDS:")
print(json.dumps(response.json(), indent=2))
