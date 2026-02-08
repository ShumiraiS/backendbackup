from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading


class LatestReadingByIndustryAPIView(APIView):
    """
    GET /api/readings/latest/?industry_id=IND_A
    Returns the latest reading + compliance + dashboard-ready cards.
    """

    def get(self, request):
        industry_id = request.query_params.get("industry_id")

        if not industry_id:
            return Response(
                {"error": "industry_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch latest reading for the industry
        ref = root_ref().child("readings").child(industry_id)
        data = ref.order_by_key().limit_to_last(1).get()

        if not data:
            return Response(
                {"message": f"No readings found for {industry_id}."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Extract the single latest item
        latest_key = list(data.keys())[0]
        latest = data[latest_key] or {}
        latest["id"] = latest_key
        latest["industry_id"] = industry_id

        # Fetch EMA thresholds and compute compliance
        limits = root_ref().child("thresholds").child("industry").get() or {}
        overall, per_param = assess_reading(latest, limits)

        latest["compliance"] = overall
        latest["parameter_status"] = per_param

        # Dashboard-ready card format
        units = {
            "ph": "",
            "temperature": "°C",
            "cod": "mg/L",
            "chlorides": "mg/L",
            "suspended_solids": "mg/L",
        }

        limits_display = {
            "ph": f'{limits.get("ph_min")}–{limits.get("ph_max")}',
            "temperature": f'≤ {limits.get("temperature_max")}',
            "cod": f'≤ {limits.get("cod_max")}',
            "chlorides": f'≤ {limits.get("chlorides_max")}',
            "suspended_solids": f'≤ {limits.get("suspended_solids_max")}',
        }

        latest["cards"] = [
            {
                "key": "ph",
                "label": "pH",
                "value": latest.get("ph"),
                "unit": units["ph"],
                "status": per_param.get("ph"),
                "limit": limits_display["ph"],
            },
            {
                "key": "temperature",
                "label": "Temperature",
                "value": latest.get("temperature"),
                "unit": units["temperature"],
                "status": per_param.get("temperature"),
                "limit": limits_display["temperature"],
            },
            {
                "key": "cod",
                "label": "COD",
                "value": latest.get("cod"),
                "unit": units["cod"],
                "status": per_param.get("cod"),
                "limit": limits_display["cod"],
            },
            {
                "key": "chlorides",
                "label": "Chlorides",
                "value": latest.get("chlorides"),
                "unit": units["chlorides"],
                "status": per_param.get("chlorides"),
                "limit": limits_display["chlorides"],
            },
            {
                "key": "suspended_solids",
                "label": "Suspended Solids",
                "value": latest.get("suspended_solids"),
                "unit": units["suspended_solids"],
                "status": per_param.get("suspended_solids"),
                "limit": limits_display["suspended_solids"],
            },
        ]

        return Response(latest, status=status.HTTP_200_OK)