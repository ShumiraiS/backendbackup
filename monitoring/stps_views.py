from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading

import uuid
from datetime import datetime


class STPsListAPIView(APIView):
    """
    GET  /api/stps/      → List all STPs
    POST /api/stps/      → Create new STP
    """

    # -------------------- GET --------------------
    def get(self, request):
        stps = root_ref().child("stps").get()

        if not stps:
            return Response([], status=status.HTTP_200_OK)

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

    # -------------------- POST --------------------
    def post(self, request):
        name = request.data.get("name")
        location = request.data.get("location")
        parameters = request.data.get("parameters", [])

        if not name:
            return Response(
                {"error": "STP name is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        stp_id = f"STP_{uuid.uuid4().hex[:6].upper()}"

        payload = {
            "name": name,
            "location": location or "",
            "parameters": parameters,
            "created_at": datetime.utcnow().isoformat(),
        }

        root_ref().child("stps").child(stp_id).set(payload)

        return Response(
            {
                "message": "STP created successfully.",
                "stp_id": stp_id,
            },
            status=status.HTTP_201_CREATED,
        )