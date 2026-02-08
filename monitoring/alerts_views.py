from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .firebase import root_ref


class AlertsListAPIView(APIView):
    """
    GET /api/alerts/?site_type=industry&site_id=IND_A&limit=20
    GET /api/alerts/?site_type=stp&site_id=STP_1&limit=20
    """

    def get(self, request):
        site_type = request.query_params.get("site_type")
        site_id = request.query_params.get("site_id")
        limit = int(request.query_params.get("limit", "20"))

        if site_type not in ["industry", "stp"] or not site_id:
            return Response(
                {"error": "Provide site_type (industry|stp) and site_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = root_ref().child("alerts").child(site_type).child(site_id).get() or {}
        keys = sorted(list(data.keys()), reverse=True)[:limit]

        alerts = []
        for k in keys:
            a = data[k]
            if isinstance(a, dict):
                a["id"] = k
                alerts.append(a)

        return Response(alerts, status=status.HTTP_200_OK)


class MarkAlertReadAPIView(APIView):
    """
    POST /api/alerts/mark-read/
    Body: {"site_type":"industry","site_id":"IND_A","alert_id":"<id>"}
    """

    def post(self, request):
        site_type = request.data.get("site_type")
        site_id = request.data.get("site_id")
        alert_id = request.data.get("alert_id")

        if site_type not in ["industry", "stp"] or not site_id or not alert_id:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        ref = root_ref().child("alerts").child(site_type).child(site_id).child(alert_id)
        existing = ref.get()
        if not existing:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)

        ref.child("read").set(True)
        return Response({"message": "Alert marked as read"}, status=status.HTTP_200_OK)
