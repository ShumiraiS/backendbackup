from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .alerts import maybe_create_alert
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

        # Fetch latest readings for the industry
        latest = root_ref().child("readings").child(industry_id).child("latest").get()

        if not latest:
            return Response({
                "latest": None,
                "history": []
            })

        history = [latest]
        latest["industry_id"] = industry_id


        # Fetch thresholds
        raw_limits = root_ref().child("thresholds").get() or {}

        ph_limit = raw_limits.get("pH", {}).get("limit")
        ph_min = None
        ph_max = None

        if ph_limit and "-" in str(ph_limit):
            parts = ph_limit.split("-")
            ph_min = float(parts[0].strip())
            ph_max = float(parts[1].strip())

        limits = {
            "ph_min": ph_min,
            "ph_max": ph_max,
            "temperature_max": raw_limits.get("Temperature", {}).get("limit"),
            "suspended_solids_max": raw_limits.get("TSS", {}).get("limit"),
        }

        # Compute compliance for EACH reading
        for item in history:
            overall, per_param = assess_reading(item, limits)

            item["compliance"] = overall
            item["parameter_status"] = per_param

            # 🚨 Trigger alert generation
            maybe_create_alert(
                site_type="industry",
                site_id=industry_id,
                reading=item,
                compliance=overall,
                anomaly=None
            )

        latest = history[-1]
        latest_param_status = latest.get("parameter_status", {})
        latest = history[-1]
        latest_param_status = latest.get("parameter_status", {})

        # --- Mapping + Display helpers ---
        # Map human labels -> reading keys in Firebase
        PARAM_KEY_MAP = {
            "pH": "ph",
            "PH": "ph",
            "Ph": "ph",
            "Temperature": "temperature",
            "COD": "cod",
            "Chlorides": "chlorides",
            "Suspended Solids": "suspended_solids",
            "TSS": "suspended_solids",
            "Total Suspended Solids (TSS)": "suspended_solids",
        }

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

        # --- 1) Try industry configured parameters ---
        industry_details = root_ref().child("industries").child(industry_id).get() or {}
        industry_parameters = industry_details.get("parameters") or []

        # --- 2) If missing/empty, fallback to sensors assigned to this industry ---
        sensors_used = []
        if not industry_parameters:
            sensors = root_ref().child("sensors").get() or {}
            for _sid, s in sensors.items():
                if s.get("industry_id") == industry_id and s.get("parameter"):
                    sensors_used.append(s.get("parameter"))
            # de-duplicate while keeping order
            seen = set()
            industry_parameters = []
            for p in sensors_used:
                if p not in seen:
                    industry_parameters.append(p)
                    seen.add(p)

        # If STILL empty, do NOT default to 5. Show nothing.
        cards = []
        for label in industry_parameters:
            # Normalise label -> key
            key = PARAM_KEY_MAP.get(label)
            if not key:
                # last-resort normalisation
                key = str(label).strip().lower().replace(" ", "_")

            cards.append({
                "key": key,
                "label": label,
                "value": latest.get(key),
                "unit": units.get(key, ""),
                "status": latest_param_status.get(key),
                "limit": limits_display.get(key),
            })

        latest["cards"] = cards

        return Response(
            {
                "latest": latest,
                "history": history,
                "debug": {
                    "industry_id": industry_id,
                    "industry_parameters_saved": industry_details.get("parameters", None),
                    "sensors_parameters_used_if_fallback": sensors_used,
                    "final_parameters_used": industry_parameters,
                    "final_cards_count": len(cards),
                }
            },
            status=status.HTTP_200_OK
        )