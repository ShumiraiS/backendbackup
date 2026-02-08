from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading


class LatestReadingBySTPAPIView(APIView):
    """
    GET /api/stp/readings/latest/?stp_id=STP_1
    """

    def get(self, request):
        stp_id = request.query_params.get("stp_id")
        if not stp_id:
            return Response({"error": "stp_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        ref = root_ref().child("readings_stp").child(stp_id)
        data = ref.order_by_key().limit_to_last(1).get()

        if not data:
            return Response({"message": f"No readings found for {stp_id}."}, status=status.HTTP_404_NOT_FOUND)

        latest_key = list(data.keys())[0]
        latest = data[latest_key] or {}
        latest["id"] = latest_key
        latest["stp_id"] = stp_id

        limits = root_ref().child("thresholds").child("stp").get() or {}
        overall, per_param = assess_reading(latest, limits)

        latest["compliance"] = overall
        latest["parameter_status"] = per_param

        return Response(latest, status=status.HTTP_200_OK)
