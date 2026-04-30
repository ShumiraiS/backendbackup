from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading


class LatestReadingBySTPAPIView(APIView):
    """
    GET /api/stp/readings/latest/?stp_id=STP_XXXX
    Always returns 200 (even if no readings)
    """

    def get(self, request):
        stp_id = request.query_params.get("stp_id")

        if not stp_id:
            return Response(
                {"error": "stp_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get parameter thresholds (this defines STP parameters)
        limits = root_ref().child("thresholds").child("stp").get() or {}

        ref = root_ref().child("readings_stp").child(stp_id)
        data = ref.order_by_key().limit_to_last(20).get()

        history = []

        if data:
            for key, value in data.items():
                value["id"] = key
                value["stp_id"] = stp_id
                history.append(value)

            history = sorted(history, key=lambda x: x.get("timestamp", ""))

            # Add compliance info
            for item in history:
                overall, per_param = assess_reading(item, limits)
                item["compliance"] = overall
                item["parameter_status"] = per_param

        latest = history[-1] if history else None

        # Build cards even if no readings
        cards = []

        for param, limit in limits.items():
            value = None
            status_param = "NO_DATA"

            if latest:
                value = latest.get(param)
                status_param = latest.get("parameter_status", {}).get(param, "NO_DATA")

            cards.append({
                "key": param,
                "label": param.upper(),
                "value": value,
                "unit": "",
                "limit": limit,
                "status": status_param,
            })

        return Response({
            "latest": latest,
            "history": history,
            "cards": cards
        }, status=status.HTTP_200_OK)