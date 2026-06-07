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
    Body: {site_id, timestamp?, ph, temperature, cod, chlorides, suspended_solids, water_level}
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
            "water_level": payload.get("water_level"),
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

            # Parse pH range (e.g., "6 - 9")
            ph_limit_str = raw_limits.get("pH", {}).get("limit", "6 - 9")
            try:
                parts = str(ph_limit_str).split("-")
                ph_min = float(parts[0].strip())
                ph_max = float(parts[1].strip())
            except Exception:
                ph_min = 6.0
                ph_max = 9.0

            # Helper to safely parse float limits
            def _parse_limit(param_name, default_val):
                val = raw_limits.get(param_name, {}).get("limit")
                try:
                    return float(val) if val is not None else default_val
                except (ValueError, TypeError):
                    return default_val

            limits = {
                "ph_min": ph_min,
                "ph_max": ph_max,
                "temperature_max": _parse_limit("Temperature", 40.0),
                "suspended_solids_max": _parse_limit("TSS", 200.0),
                "cod_max": _parse_limit("COD", 250.0),
                "chlorides_max": _parse_limit("Chlorides", 1000.0),
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

            # Thresholds mapping for monitoring record storage
            thresholds_map = {
                "ph": raw_limits.get("pH", {}).get("limit", "6 - 9"),
                "temperature": raw_limits.get("Temperature", {}).get("limit", 40),
                "suspended_solids": raw_limits.get("TSS", {}).get("limit", 200),
                "cod": raw_limits.get("COD", {}).get("limit", 250),
                "chlorides": raw_limits.get("Chlorides", {}).get("limit", 1000),
            }

            # 4) Store monitoring records snapshot
            for param, status in per_param.items():
                record_id = f"REC_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

                db.child("monitoring_records").child(record_id).set({
                    "industry": site_id,
                    "parameter": param,
                    "value": reading.get(param),
                    "threshold": thresholds_map.get(param, "N/A"),
                    "status": "Compliant" if status in ("GREEN", "YELLOW") else "Non-Compliant",
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
