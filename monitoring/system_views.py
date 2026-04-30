# monitoring/system_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from .firebase_config import root_ref
from datetime import datetime

class SystemHealthAPIView(APIView):

    def get(self, request):
        api_status = "UP"
        firebase_status = "UP"

        # Check Firebase connectivity
        try:
            root_ref().child("health_check").set({
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception:
            firebase_status = "DOWN"

        return Response({
            "api": api_status,
            "firebase": firebase_status,
            "timestamp": datetime.utcnow().isoformat()
        })