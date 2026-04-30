from rest_framework.views import APIView
from rest_framework.response import Response
from monitoring.firebase_config import root_ref  # adjust to your actual file

class DashboardOverviewView(APIView):
    def get(self, request):

        users = root_ref().child("users").get() or {}
        sensors = root_ref().child("sensors").get() or {}
        alerts = root_ref().child("alerts").get() or {}

        users_count = len(users)
        sensors_count = len(sensors)
        alerts_count = len(alerts)

        compliance = max(0, 100 - alerts_count * 5)

        return Response({
            "users": users_count,
            "sensors": sensors_count,
            "alerts": alerts_count,
            "compliance": compliance
        })