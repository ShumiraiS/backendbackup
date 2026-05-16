import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'effluai_backend.settings')
django.setup()

from monitoring.firebase import root_ref

rules = root_ref().child("ai_rules").get()
print(json.dumps(rules, indent=2))
