from django.core.management.base import BaseCommand
from monitoring.firebase_config import root_ref


class Command(BaseCommand):
    help = "Seed default regulatory thresholds into Firebase"

    def handle(self, *args, **kwargs):
        thresholds = {
            "COD": {"limit": 250, "unit": "mg/L"},
            "BOD": {"limit": 200, "unit": "mg/L"},
            "TSS": {"limit": 200, "unit": "mg/L"},
            "pH": {"limit": "6 - 9", "unit": ""},
            "Temperature": {"limit": 40, "unit": "°C"},
            "Oil & Grease": {"limit": 50, "unit": "mg/L"},
            "Ammonia (NH3)": {"limit": 30, "unit": "mg/L"},
            "Nitrates": {"limit": 50, "unit": "mg/L"},
            "Phosphates": {"limit": 10, "unit": "mg/L"},
            "Chlorides": {"limit": 1000, "unit": "mg/L"},
            "Sulphates": {"limit": 500, "unit": "mg/L"},
            "Heavy Metals": {"limit": "Varies by metal", "unit": ""},
        }

        root_ref().child("thresholds").set(thresholds)

        self.stdout.write(self.style.SUCCESS("Thresholds seeded successfully."))