from rest_framework.views import APIView
from rest_framework.response import Response
from .firebase_config import root_ref
from .permissions import IsAdmin


class MonitoringRecordsAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = root_ref().child("monitoring_records").get() or {}

        records = []
        for key, value in data.items():
            value["id"] = key
            records.append(value)

        return Response(records)