from datetime import datetime, timezone
from .firebase import root_ref
from .email_alerts import send_alert_email

def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def create_alert(site_type: str, site_id: str, payload: dict):
    """
    Writes alert to:
    alerts/<site_type>/<site_id>/<alert_id>
    Uses a time-based alert_id for sorting.
    """
    alert_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    payload = dict(payload)
    payload.setdefault("created_at", _now_iso())
    payload.setdefault("read", False)

    root_ref().child("alerts").child(site_type).child(site_id).child(alert_id).set(payload)
    return alert_id


def maybe_create_alert(site_type: str, site_id: str, reading: dict, compliance: str, anomaly: dict | None):
    """
    Creates alerts when:
    - compliance is RED, OR
    - anomaly_score >= 50
    Prevents spam by not repeating the same type for the same timestamp.
    """
    ts = reading.get("timestamp") or "unknown_time"
    anomaly_score = (anomaly or {}).get("anomaly_score", 0)
    is_anomaly = (anomaly or {}).get("is_anomaly", False)
    anomalous_params = (anomaly or {}).get("anomalous_parameters", [])

    # Build a lightweight dedupe key
    dedupe_key = f"{ts}|{compliance}|{anomaly_score}"

    # Store last dedupe key to avoid duplicates on refresh
    last_key_ref = root_ref().child("alerts_lastkey").child(site_type).child(site_id)
    last_key = last_key_ref.get()

    if last_key == dedupe_key:
        return None  # no new alert

    # Decide alert type + message
    alert_type = None
    severity = "LOW"
    title = ""
    message = ""

    if compliance == "RED":
        alert_type = "COMPLIANCE_BREACH"
        severity = "HIGH"
        title = "Compliance breach detected"

        breached = ", ".join(anomalous_params) if anomalous_params else "Unknown parameter"

        message = f"The following parameter(s) exceeded EMA limits: {breached}. Immediate attention is recommended."

    elif is_anomaly:
        alert_type = "ANOMALY_DETECTED"
        severity = "MEDIUM"
        title = "Unusual pattern detected"
        message = "The latest reading deviates from recent behaviour. Investigate potential process changes."

    if not alert_type:
        return None

    alert_payload = {
        "type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "timestamp": ts,
        "site_type": site_type,
        "site_id": site_id,
        "compliance": compliance,
        "anomaly_score": anomaly_score,
        "anomalous_parameters": anomalous_params,
    }

    alert_id = create_alert(site_type, site_id, alert_payload)
    send_alert_email(site_id, alert_payload, reading)
    last_key_ref.set(dedupe_key)

    return alert_id