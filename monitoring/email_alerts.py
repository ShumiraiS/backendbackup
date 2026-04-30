from django.core.mail import send_mail
from django.conf import settings


def get_recommendation(reading):
    """
    Basic recommendation engine based on parameter violations.
    """

    recs = []

    if reading.get("ph") and (reading["ph"] < 6 or reading["ph"] > 9):
        recs.append("Check chemical dosing system to stabilise pH levels.")

    if reading.get("temperature") and reading["temperature"] > 35:
        recs.append("Inspect cooling processes to reduce discharge temperature.")

    if reading.get("suspended_solids") and reading["suspended_solids"] > 200:
        recs.append("Check sedimentation tanks or filtration units for poor solids removal.")

    if reading.get("chlorides") and reading["chlorides"] > 250:
        recs.append("Investigate industrial salt discharge or process contamination.")

    if reading.get("cod") and reading["cod"] > 250:
        recs.append("Review biological treatment efficiency or organic waste discharge.")

    if not recs:
        recs.append("Investigate the effluent treatment process for abnormal conditions.")

    return "\n".join(recs)


def send_alert_email(site_id, alert_payload, reading=None):

    subject = f"EffluAI Alert - {alert_payload['title']}"

    values_section = ""
    recommendation_section = ""

    if reading:

        values_section = f"""
Sensor Readings

pH: {reading.get('ph')}
Temperature: {reading.get('temperature')}
Suspended Solids: {reading.get('suspended_solids')}
Chlorides: {reading.get('chlorides')}
COD: {reading.get('cod')}
"""

        recommendation_section = f"""

Recommended Action
{get_recommendation(reading)}
"""

    message = f"""
EffluAI Compliance Alert

Industry: {site_id}

Type: {alert_payload['type']}
Severity: {alert_payload['severity']}

Message:
{alert_payload['message']}

Timestamp:
{alert_payload['timestamp']}

Compliance Status:
{alert_payload['compliance']}

{values_section}

{recommendation_section}

This alert was generated automatically by the EffluAI monitoring system.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [
            "shumiraishiri@gmail.com",
            "shiriyapindashumirai@gmail.com",
        ],
        fail_silently=False,
    )