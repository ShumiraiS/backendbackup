# monitoring/ingest_views.py
import json
from datetime import datetime, timezone

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse
from django.views import View

from .firebase import root_ref
from .compliance import assess_reading
from .alerts import maybe_create_alert

def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@method_decorator(csrf_exempt, name='dispatch')
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
        raw_limits = db.child("thresholds").get() or {}

        limits = {
            "ph_min": raw_limits.get("ph", {}).get("min"),
            "ph_max": raw_limits.get("ph", {}).get("max"),
            "temperature_max": raw_limits.get("temperature", {}).get("max"),
            "suspended_solids_max": raw_limits.get("TSS", {}).get("limit"),
        }

        overall, per_param = assess_reading(reading, limits)

        maybe_create_alert(
            site_type="industry",
            site_id=site_id,
            reading=reading,
            compliance=overall,
            anomaly={
                "anomaly_score": 100 if overall == "RED" else 0,
                "is_anomaly": overall == "RED",
                "anomalous_parameters": [
                    p for p, s in per_param.items() if s == "RED"
                ],
            }
        )

        db.child("status").child("industry").child(site_id).set({
            "compliance": overall,
            "parameter_status": per_param,
            "last_updated": reading["timestamp"]
        })

        # 3) Store monitoring records snapshot
        for param, status in per_param.items():
            record_id = f"REC_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

            db.child("monitoring_records").child(record_id).set({
                "industry": site_id,
                "parameter": param,
                "value": reading.get(param),
                "threshold": limits.get(param, {}).get("limit"),
                "status": "Compliant" if status == "GREEN" else "Non-Compliant",
                "timestamp": reading["timestamp"]
            })

        return JsonResponse({
            "status": "ok",
            "site_id": site_id,
            "stored_timestamp": reading["timestamp"],
            "compliance": overall,
            "parameter_status": per_param
        })
