from rest_framework.views import APIView
from rest_framework.response import Response
from .firebase_config import root_ref

class ComplianceHistoryAPIView(APIView):

    def get(self, request):
        db = root_ref()

        industries = db.child("industries").get() or {}
        compliance_data = db.child("compliance_history").get() or {}

        total = len(industries)

        records = list(compliance_data.values())

        compliant = sum(1 for r in records if r.get("overall_status") == "GREEN")
        non_compliant = sum(1 for r in records if r.get("overall_status") == "RED")

        # Entities with no readings = assume GREEN (or UNKNOWN depending on policy)
        entities_with_readings = {r.get("entity_name") for r in records}
        entities_without_readings = total - len(entities_with_readings)

        compliant += entities_without_readings

        average = round((compliant / total) * 100, 2) if total > 0 else 0

        distribution = []

        for name in industries.keys():
            status = next(
                (r.get("overall_status") for r in records if r.get("entity_name") == name),
                "GREEN"  # default if no reading
            )

            score = 100 if status == "GREEN" else 50 if status == "YELLOW" else 30

            distribution.append({
                "name": name,
                "compliance": score
            })

        high_risk = [
            {
                "name": r.get("entity_name"),
                "location": r.get("location"),
                "parameter": "Multiple",
                "reading": "-",
                "risk": "High"
            }
            for r in records
            if r.get("overall_status") == "RED"
        ]

        return Response({
            "total": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "average": average,
            "distribution": distribution,
            "high_risk": high_risk
        })