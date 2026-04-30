from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from datetime import datetime, timedelta
import uuid

from .firebase import root_ref


class SensorsAPIView(APIView):
    """
    GET  /api/sensors/
    POST /api/sensors/
    """

    def get(self, request):
        industry_id = request.query_params.get("industry_id")
        stp_id = request.query_params.get("stp_id")

        sensors = root_ref().child("sensors").get() or {}
        result = []

        for sensor_id, details in sensors.items():
            if industry_id and details.get("industry_id") != industry_id:
                continue

            if stp_id and details.get("stp_id") != stp_id:
                continue

            payload = dict(details)
            payload["sensor_id"] = sensor_id
            result.append(payload)

        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request):
            sensor_id = request.query_params.get("sensor_id")

            if not sensor_id:
                return Response(
                    {"error": "sensor_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sensor_ref = root_ref().child("sensors").child(sensor_id)
            existing = sensor_ref.get()

            if not existing:
                return Response(
                    {"error": "Sensor not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            sensor_ref.delete()

            return Response(
                {"message": "Sensor deleted successfully"},
                status=status.HTTP_200_OK,
            )
    def post(self, request):
        industry_id = request.data.get("industry_id")
        stp_id = request.data.get("stp_id")
        parameter = request.data.get("parameter")
        location = request.data.get("location")
        address = request.data.get("address")
        calibration_frequency = request.data.get("calibration_frequency")
        lifespan = request.data.get("lifespan")

        if not parameter:
            return Response(
                {"error": "parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not industry_id and not stp_id:
            return Response(
                {"error": "Either industry_id or stp_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sensor_id = f"SEN_{uuid.uuid4().hex[:6].upper()}"

        installation_date = datetime.utcnow()

        next_maintenance = None
        if calibration_frequency:
            try:
                freq = int(calibration_frequency)
                next_maintenance = (
                    installation_date + timedelta(days=90)
                )
            except:
                pass

        payload = {
            "industry_id": industry_id,
            "stp_id": stp_id,
            "parameter": parameter,
            "location": location or "Inspection Chamber",
            "address": address,
            "status": "Active",
            "health": "Healthy",
            "installation_date": installation_date.isoformat(),
            "calibration_frequency": calibration_frequency,
            "lifespan": lifespan,
            "next_maintenance": next_maintenance.isoformat(),
        }

        root_ref().child("sensors").child(sensor_id).set(payload)

        return Response(
            {
                "message": "Sensor created successfully",
                "sensor_id": sensor_id,
            },
            status=status.HTTP_201_CREATED,
        )