# reports_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime
from .firebase import root_ref


class ReportsSummaryAPIView(APIView):

    def get(self, request):
        db = root_ref()

        industries = db.child("industries").get() or {}
        stps = db.child("stps").get() or {}
        alerts = db.child("alerts").get() or {}

        results = []

        def process_entities(entity_dict, entity_type):
            for entity_id, entity_data in entity_dict.items():

                name = entity_data.get("name", entity_id)
                location = entity_data.get("location", "Unknown")

                # Get alerts for this entity
                entity_alerts = alerts.get(entity_type.lower(), {}).get(entity_id, {}) or {}

                violations = []
                unresolved = 0

                for alert_id, alert in entity_alerts.items():
                    resolved = alert.get("read", False)

                    if not resolved:
                        unresolved += 1

                    violations.append({
                        "severity": alert.get("severity", "Medium"),
                        "parameter": ", ".join(alert.get("parameters", [])),
                        "reading": "-",
                        "threshold": "-",
                        "date": alert.get("timestamp"),
                        "resolved": resolved,
                    })

                compliance_rate = 100
                if violations:
                    compliance_rate = max(0, 100 - unresolved * 15)

                status = "Compliant"
                if unresolved > 0:
                    status = "Non-Compliant"
                elif violations:
                    status = "At Risk"

                results.append({
                    "id": entity_id,
                    "name": name,
                    "type": entity_type,
                    "location": location,
                    "lastReadingAt": entity_data.get("last_reading", "-"),
                    "status": status,
                    "complianceRate": compliance_rate,
                    "activeAlerts": unresolved,
                    "sensorsDeployed": len(entity_data.get("parameters", [])),
                    "violations": violations,
                })

        process_entities(industries, "Industry")
        process_entities(stps, "STP")

        return Response(results)