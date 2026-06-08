from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading
from .anomaly import anomaly_score_from_history
from .alerts import maybe_create_alert
from .inference_engine import run_inference
from .email_alerts import get_recommendation_list


def build_advice(overall, per_param, reading, context_label):
    names = {
        "ph": "pH",
        "temperature": "Temperature",
        "cod": "COD",
        "chlorides": "Chlorides",
        "suspended_solids": "Suspended Solids",
    }

    red_params = [k for k, v in per_param.items() if v == "RED"]
    yellow_params = [k for k, v in per_param.items() if v == "YELLOW"]

    reasons = [f"{names[p]} is outside the EMA limit" for p in red_params]
    reasons += [f"{names[p]} is close to the EMA limit" for p in yellow_params]

    if overall in ["RED", "YELLOW"]:
        priority = "HIGH" if overall == "RED" else "MEDIUM"
        summary = (
            f"{context_label}: Non-compliant discharge detected. Immediate action is recommended."
            if overall == "RED"
            else f"{context_label}: Potential compliance risk. Preventative action is recommended."
        )
        # Fetch dynamic parameter-specific recommendations matching email alerts
        actions = get_recommendation_list(reading)
        who = ["Industry operator", "Urban council", "EMA officer"] if overall == "RED" else ["Industry operator", "Urban council"]
    else:
        priority = "LOW"
        summary = f"{context_label}: Readings appear compliant with EMA limits."
        actions = [
            "Continue routine monitoring and record-keeping.",
            "Maintain treatment processes to sustain compliance."
        ]
        who = ["Industry operator"]

    notes = []
    if per_param.get("cod") in ["RED", "YELLOW"]:
        notes.append("Elevated COD may indicate high organic load or insufficient treatment performance.")
    if per_param.get("suspended_solids") in ["RED", "YELLOW"]:
        notes.append("High suspended solids may cause blockages and reduce treatment efficiency.")

    return {
        "overall_status": overall,
        "priority": priority,
        "summary": summary,
        "reasons": reasons,
        "recommended_actions": actions,
        "who_should_act": who,
        "notes": notes,
        "timestamp": reading.get("timestamp")
    }


class AIAdviceAPIView(APIView):
    """
    GET /api/ai/advice/?industry_id=IND_A
    GET /api/ai/advice/?stp_id=STP_1
    """

    def get(self, request):
        industry_id = request.query_params.get("industry_id")
        stp_id = request.query_params.get("stp_id")

        if not industry_id and not stp_id:
            return Response({"error": "Provide either industry_id or stp_id"}, status=status.HTTP_400_BAD_REQUEST)

        if industry_id:
            context_label = f"Industry {industry_id}"
            raw_limits = root_ref().child("thresholds").get() or {}
            ref = root_ref().child("readings").child(industry_id)
            site_type = "industry"
            site_id = industry_id
        else:
            context_label = f"STP {stp_id}"
            raw_limits = root_ref().child("thresholds").get() or {}
            ref = root_ref().child("readings_stp").child(stp_id)
            site_type = "stp"
            site_id = stp_id

        data = ref.order_by_key().limit_to_last(20).get()
        if not data:
            return Response({
                "overall_status": "GREEN",
                "priority": "LOW",
                "summary": f"{context_label}: No telemetry readings recorded yet.",
                "reasons": [],
                "recommended_actions": [
                    "Ensure sensor node is online and transmitting telemetry.",
                    "Verify Firebase real-time database connection status."
                ],
                "who_should_act": ["Industry operator"],
                "notes": ["Awaiting first telemetry transmission from the facility."],
                "timestamp": None
            }, status=status.HTTP_200_OK)

        keys = sorted(list(data.keys()))
        latest_key = keys[-1]
        reading = data[latest_key] or {}
        reading["id"] = latest_key

        print("SMART ADVISOR READING:", reading)

        history = [data[k] for k in keys[:-1]]

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

        # Run inference engine
        triggered_rules = run_inference(reading)

        advice = build_advice(overall, per_param, reading, context_label)

        # Add rule explanations
        if triggered_rules:
            advice["rule_triggers"] = triggered_rules

        advice["anomaly"] = anomaly_score_from_history(history, reading, z_threshold=2.0)

        # ✅ Auto-create alert (deduped)
        maybe_create_alert(
            site_type=site_type,
            site_id=site_id,
            reading=reading,
            compliance=overall,
            anomaly=advice.get("anomaly")
        )

        return Response(advice, status=status.HTTP_200_OK)