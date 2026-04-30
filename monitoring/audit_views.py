from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .firebase import root_ref


class AuditLogsAPIView(APIView):
    """
    GET /api/admin/logs/?limit=50
    """

    def get(self, request):
        limit = int(request.query_params.get("limit", "100"))

        data = root_ref().child("admin_logs").get() or {}

        logs = []
        for log_id, entry in data.items():
            if isinstance(entry, dict):
                entry["id"] = log_id
                logs.append(entry)

        # Sort newest first
        logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)

        return Response(logs[:limit], status=status.HTTP_200_OK)