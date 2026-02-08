from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading


class STPsListAPIView(APIView):
    """
    GET /api/stps/
    Returns STPs list + status badge (GREEN/YELLOW/RED/OFFLINE).
    """

    def get(self, request):
        stps = root_ref().child("stps").get()
        if not stps:
            return Response({"message": "No STPs found."}, status=status.HTTP_404_NOT_FOUND)

        limits = root_ref().child("thresholds").child("stp").get() or {}
        result = []

        for stp_id, details in stps.items():
            status_badge = "OFFLINE"
            last_updated = None

            readings_ref = root_ref().child("readings_stp").child(stp_id)
            latest_data = readings_ref.order_by_key().limit_to_last(1).get()

            if latest_data:
                latest_key = list(latest_data.keys())[0]
                latest = latest_data[latest_key] or {}

                overall, _ = assess_reading(latest, limits)
                status_badge = overall
                last_updated = latest.get("timestamp")

            payload = dict(details)
            payload["stp_id"] = stp_id
            payload["status"] = status_badge
            payload["last_updated"] = last_updated
            result.append(payload)

        return Response(result, status=status.HTTP_200_OK)
