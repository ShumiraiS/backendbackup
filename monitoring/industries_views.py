from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from datetime import datetime
import uuid

from .firebase import root_ref
from .compliance import assess_reading


class IndustriesListAPIView(APIView):
    """
    GET  /api/industries/
    POST /api/industries/
    """

    def get(self, request):
        industries = root_ref().child("industries").get()
        if not industries:
            return Response(
                {"message": "No industries found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Pull thresholds once (EMA limits)
        limits = root_ref().child("thresholds").child("industry").get() or {}

        result = []

        for industry_id, details in industries.items():
            # Default if no readings
            status_badge = "OFFLINE"
            last_updated = None

            # Try fetch latest reading for this industry
            readings_ref = root_ref().child("readings").child(industry_id)
            latest_data = readings_ref.order_by_key().limit_to_last(1).get()

            if latest_data:
                latest_key = list(latest_data.keys())[0]
                latest = latest_data[latest_key] or {}

                # If compliance already stored, use it; else compute it
                if "compliance" in latest and latest.get("compliance"):
                    status_badge = latest.get("compliance")
                else:
                    overall, _per_param = assess_reading(latest, limits)
                    status_badge = overall

                last_updated = latest.get("timestamp")

            payload = dict(details)  # copy details safely
            payload["industry_id"] = industry_id
            payload["status"] = status_badge
            payload["last_updated"] = last_updated

            result.append(payload)

        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new industry
        """

        name = request.data.get("name")
        address = request.data.get("address")
        contact_email = request.data.get("contact_email")

        if not name:
            return Response(
                {"error": "Industry name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate unique Industry ID
        industry_id = f"IND_{uuid.uuid4().hex[:6].upper()}"

        # Get parameters from request
        parameters = request.data.get("parameters", [])

        if not isinstance(parameters, list):
            return Response(
                {"error": "parameters must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            "name": name,
            "address": address or "",
            "contact_email": contact_email or "",
            "parameters": parameters,  # ✅ THIS IS THE FIX
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save to Firebase
        root_ref().child("industries").child(industry_id).set(payload)

        return Response(
            {
                "message": "Industry created successfully.",
                "industry_id": industry_id,
            },
            status=status.HTTP_201_CREATED,
        )