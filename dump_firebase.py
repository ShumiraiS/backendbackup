import os
import sys
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'effluai_backend.settings')
django.setup()

from monitoring.firebase import root_ref

industries = root_ref().child("industries").get()
print("INDUSTRIES:")
print(json.dumps(industries, indent=2))

stps = root_ref().child("stps").get()
print("STPS:")
print(json.dumps(stps, indent=2))
