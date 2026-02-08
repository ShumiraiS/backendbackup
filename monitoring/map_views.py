from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading


class MapOverviewAPIView(APIView):
    """
    GET /api/map/overview/
    Returns map markers for industries + STPs with status and coordinates.
    """

    def get(self, request):
        limits_industry = root_ref().child("thresholds").child("industry").get() or {}
        limits_stp = root_ref().child("thresholds").child("stp").get() or {}

        markers = []

        # -------- Industries --------
        industries = root_ref().child("industries").get() or {}
        for industry_id, details in industries.items():
            status_badge = "OFFLINE"
            last_updated = None

            latest_data = (
                root_ref()
                .child("readings")
                .child(industry_id)
                .order_by_key()
                .limit_to_last(1)
                .get()
            )

            if latest_data:
                k = list(latest_data.keys())[0]
                latest = latest_data[k] or {}
                overall, _ = assess_reading(latest, limits_industry)
                status_badge = overall
                last_updated = latest.get("timestamp")

            markers.append({
                "id": industry_id,
                "type": "industry",
                "name": (details or {}).get("name"),
                "location": (details or {}).get("location"),
                "lat": (details or {}).get("lat"),
                "lng": (details or {}).get("lng"),
                "status": status_badge,
                "last_updated": last_updated,
            })

        # -------- STPs --------
        stps = root_ref().child("stps").get() or {}
        for stp_id, details in stps.items():
            status_badge = "OFFLINE"
            last_updated = None

            latest_data = (
                root_ref()
                .child("readings_stp")
                .child(stp_id)
                .order_by_key()
                .limit_to_last(1)
                .get()
            )

            if latest_data:
                k = list(latest_data.keys())[0]
                latest = latest_data[k] or {}
                overall, _ = assess_reading(latest, limits_stp)
                status_badge = overall
                last_updated = latest.get("timestamp")

            markers.append({
                "id": stp_id,
                "type": "stp",
                "name": (details or {}).get("name"),
                "location": (details or {}).get("location"),
                "lat": (details or {}).get("lat"),
                "lng": (details or {}).get("lng"),
                "status": status_badge,
                "last_updated": last_updated,
            })

        return Response(
            {"markers": markers, "count": len(markers)},
            status=status.HTTP_200_OK
        )
