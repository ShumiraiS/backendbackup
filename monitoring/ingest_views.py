# monitoring/ingest_views.py
import json
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views import View

from .firebase import root_ref
from .compliance import assess_reading


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class IngestIndustryReadingAPIView(View):
    """
    POST /api/ingest/industry/
    Body: {site_id, timestamp?, ph, temperature, cod, chlorides, suspended_solids}
    """

    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        site_id = payload.get("site_id")
        if not site_id:
            return JsonResponse({"error": "site_id is required"}, status=400)

        reading = {
            "timestamp": payload.get("timestamp") or _now_iso(),
            "ph": payload.get("ph"),
            "temperature": payload.get("temperature"),
            "cod": payload.get("cod"),
            "chlorides": payload.get("chlorides"),
            "suspended_solids": payload.get("suspended_solids"),
            "source": "esp32"
        }

        # 1) Store to Firebase (latest + history)
        db = root_ref()

        # latest snapshot
        db.child("readings").child(site_id).child("latest").set(reading)

        # history (auto key)
        hist_key = datetime.now(timezone.utc).strftime("r%Y%m%d%H%M%S%f")
        db.child("readings").child(site_id).child("history").child(hist_key).set(reading)

        # 2) Compute compliance and write status node (nice for UI)
        limits = db.child("thresholds").child("industry").get() or {}
        overall, per_param = assess_reading(reading, limits)

        db.child("status").child("industry").child(site_id).set({
            "compliance": overall,
            "parameter_status": per_param,
            "last_updated": reading["timestamp"]
        })

        # 3) (Optional) Auto-create alert if RED
        if overall == "RED":
            alert_id = f"ALERT_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
            red_params = [k for k, v in per_param.items() if v == "RED"]
            db.child("alerts").child("industry").child(site_id).child(alert_id).set({
                "severity": "HIGH",
                "message": "Compliance breach detected from sensor upload",
                "parameters": red_params,
                "timestamp": reading["timestamp"],
                "read": False,
                "resolved": False
            })

        return JsonResponse({
            "status": "ok",
            "site_id": site_id,
            "stored_timestamp": reading["timestamp"],
            "compliance": overall,
            "parameter_status": per_param
        })
