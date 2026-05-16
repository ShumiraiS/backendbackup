import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

SERVICE_ACCOUNT_PATH = r"c:\effluai-backend\serviceAccountKey.json"

rules = {
  "rule_ph_acidic": {
    "parameter": "ph",
    "condition": "<",
    "threshold": 6.0,
    "description": "Highly acidic pH detected. This can cause severe corrosion to discharge infrastructure and harm aquatic life."
  },
  "rule_ph_alkaline": {
    "parameter": "ph",
    "condition": ">",
    "threshold": 9.0,
    "description": "Highly alkaline pH detected. Immediate neutralization is required before discharge."
  },
  "rule_temp_high": {
    "parameter": "temperature",
    "condition": ">",
    "threshold": 35.0,
    "description": "Elevated temperature can decrease dissolved oxygen in receiving waters, threatening aquatic ecosystems."
  },
  "rule_cod_high": {
    "parameter": "cod",
    "condition": ">",
    "threshold": 250.0,
    "description": "High Chemical Oxygen Demand (COD) indicates excessive organic pollution load. Check biological treatment stages."
  },
  "rule_chlorides_high": {
    "parameter": "chlorides",
    "condition": ">",
    "threshold": 500.0,
    "description": "High chlorides detected. This indicates high salinity which is difficult to treat and toxic to freshwater organisms."
  },
  "rule_solids_high": {
    "parameter": "suspended_solids",
    "condition": ">",
    "threshold": 100.0,
    "description": "Excessive suspended solids detected. Check sedimentation tanks and filtration systems for potential bypass or failure."
  }
}

print("Authenticating...")
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH, 
    scopes=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/firebase.database"]
)

request = google.auth.transport.requests.Request()
credentials.refresh(request)
token = credentials.token

url = "https://efflu-aibackend-default-rtdb.firebaseio.com/ai_rules.json"

print("Uploading rules to Firebase...")
headers = {"Authorization": f"Bearer {token}"}
response = requests.put(url, headers=headers, json=rules)

if response.status_code == 200:
    print("Success! Rules seeded to ai_rules.")
else:
    print(f"Error {response.status_code}: {response.text}")
