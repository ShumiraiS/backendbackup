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

        try:
            # 1) Store to Firebase (latest + history)
            db = root_ref()

            # latest snapshot
            db.child("readings").child(site_id).child("latest").set(reading)

            # history (auto key)
            hist_key = datetime.now(timezone.utc).strftime("r%Y%m%d%H%M%S%f")
            db.child("readings").child(site_id).child("history").child(hist_key).set(reading)

            # 2) Compute compliance and write status node
            raw_limits = db.child("thresholds").get() or {}
            
            # Safe parsing of limits
            def safe_get(d, *keys):
                for k in keys:
                    if isinstance(d, dict):
                        d = d.get(k, {})
                    else:
                        return None
                return d if not isinstance(d, dict) else None

            limits = {
                "ph_min": safe_get(raw_limits, "ph", "min"),
                "ph_max": safe_get(raw_limits, "ph", "max"),
                "temperature_max": safe_get(raw_limits, "temperature", "max"),
                "suspended_solids_max": safe_get(raw_limits, "TSS", "limit"),
            }

            overall, per_param = assess_reading(reading, limits)

            # 3) Alert logic
            try:
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
            except Exception as alert_err:
                print(f"Alert creation failed: {alert_err}")

            db.child("status").child("industry").child(site_id).set({
                "compliance": overall,
                "parameter_status": per_param,
                "last_updated": reading["timestamp"]
            })

            # 4) Store monitoring records snapshot
            for param, status in per_param.items():
                record_id = f"REC_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
                
                # Get specific threshold for this param
                thresh = None
                if param == "ph":
                    thresh = f"{limits.get('ph_min')} - {limits.get('ph_max')}"
                elif param == "temperature":
                    thresh = limits.get("temperature_max")
                elif param == "suspended_solids":
                    thresh = limits.get("suspended_solids_max")

                db.child("monitoring_records").child(record_id).set({
                    "industry": site_id,
                    "parameter": param,
                    "value": reading.get(param),
                    "threshold": str(thresh) if thresh is not None else "N/A",
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

        except Exception as db_err:
            print(f"Database/Ingest Error: {db_err}")
            # If DEBUG is True, we return the error, otherwise generic
            from django.conf import settings
            if settings.DEBUG:
                return JsonResponse({"error": str(db_err)}, status=500)
            return JsonResponse({"error": "Internal database error"}, status=500)
