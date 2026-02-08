from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase import root_ref
from .compliance import assess_reading
from .anomaly import anomaly_score_from_history
from .alerts import maybe_create_alert


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

    if overall == "RED":
        priority = "HIGH"
        summary = f"{context_label}: Non-compliant discharge detected. Immediate action is recommended."
        actions = [
            "Verify readings with a confirmatory sample and calibrate sensors if necessary.",
            "Inspect treatment stages and check for process upsets contributing to high pollution load.",
            "Implement corrective steps (e.g., pre-treatment optimisation, sedimentation/filtration checks).",
            "Increase monitoring frequency until readings stabilise within limits."
        ]
        who = ["Industry operator", "Urban council", "EMA officer"]
    elif overall == "YELLOW":
        priority = "MEDIUM"
        summary = f"{context_label}: Potential compliance risk. Preventative action is recommended."
        actions = [
            "Repeat sampling to confirm the trend and monitor more frequently.",
            "Review operations/maintenance to prevent a breach.",
            "Apply minor process adjustments to bring values comfortably within limits."
        ]
        who = ["Industry operator", "Urban council"]
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
            limits = root_ref().child("thresholds").child("industry").get() or {}
            ref = root_ref().child("readings").child(industry_id)
            site_type = "industry"
            site_id = industry_id
        else:
            context_label = f"STP {stp_id}"
            limits = root_ref().child("thresholds").child("stp").get() or {}
            ref = root_ref().child("readings_stp").child(stp_id)
            site_type = "stp"
            site_id = stp_id

        data = ref.order_by_key().limit_to_last(20).get()
        if not data:
            return Response({"message": "No readings found for the selected site."}, status=status.HTTP_404_NOT_FOUND)

        keys = sorted(list(data.keys()))
        latest_key = keys[-1]
        reading = data[latest_key] or {}
        reading["id"] = latest_key

        history = [data[k] for k in keys[:-1]]

        overall, per_param = assess_reading(reading, limits)
        advice = build_advice(overall, per_param, reading, context_label)

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
