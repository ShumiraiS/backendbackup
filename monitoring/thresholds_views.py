from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .firebase_config import root_ref
from .permissions import IsAdmin
from .auth_views import log_admin_action

# ================= THRESHOLDS =================

class ThresholdsAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        thresholds = root_ref().child("thresholds").get()
        if not thresholds:
            return Response([], status=200)

        result = []
        for key, value in thresholds.items():
            result.append({
                "parameter": key,
                "limit": value.get("limit"),
                "unit": value.get("unit"),
            })

        return Response(result)

    def put(self, request):
        data = request.data  # Expect list

        for item in data:
            param = item.get("parameter")
            limit = item.get("limit")
            unit = item.get("unit")

            root_ref().child("thresholds").child(param).set({
                "parameter": param,
                "limit": limit,
                "unit": unit,
            })

        log_admin_action(
            action="Threshold Updated",
            performed_by=request.headers.get("X-User-Role"),
            role=request.headers.get("X-User-Role"),
            entity=param,
            before=old_limit,
            after=limit,
            severity="High",
            request=request,
        )

        return Response({"message": "Thresholds updated successfully"})