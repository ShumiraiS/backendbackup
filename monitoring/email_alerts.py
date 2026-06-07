import requests
import threading
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings


def get_recommendation_list(reading):
    """
    Basic recommendation engine returning a list of actions based on parameter violations.
    """
    recs = []
    if not reading:
        return ["Investigate the effluent treatment process for abnormal conditions."]

    # Casing matches lowercase keys in ingested reading
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

    return recs


def get_recommendation(reading):
    """
    Legacy compatibility function returning newline-separated recommendations.
    """
    return "\n".join(get_recommendation_list(reading))


def format_timestamp(ts):
    """
    Formats ISO timestamp string into a user-friendly datetime format.
    """
    try:
        # e.g., "2026-06-07T20:10:00Z" -> "Jun 07, 2026, 08:10:00 PM UTC"
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y, %I:%M:%S %p UTC")
    except Exception:
        return ts


def generate_compliance_alert_html(site_id, alert_payload, reading=None):
    """
    Generates a rich HTML string for compliance alert emails matching AlertEmailHTML.js.
    """
    industry_id = site_id
    alert_type = alert_payload.get("type", "COMPLIANCE_BREACH")
    severity = alert_payload.get("severity", "HIGH")
    message = alert_payload.get("message", "")
    timestamp = alert_payload.get("timestamp", "")
    compliance_status = alert_payload.get("compliance", "RED")
    parameters = alert_payload.get("anomalous_parameters", [])

    severity_color = "#DC2626" if severity == "HIGH" else "#7F1D1D" if severity == "CRITICAL" else "#F59E0B"

    critical_thresholds = {
        "ph": {"min": 6, "max": 9, "unit": ""},
        "temperature": {"max": 40, "unit": "°C"},
        "suspended_solids": {"max": 200, "unit": "mg/L"},
        "chlorides": {"max": 300, "unit": "mg/L"},
        "cod": {"max": 250, "unit": "mg/L"},
    }

    def get_parameter_status(param, val):
        p = param.lower()
        thresh = critical_thresholds.get(p)
        if not thresh or val is None:
            return "normal"
        if p == "ph":
            return "critical" if (val < thresh["min"] or val > thresh["max"]) else "normal"
        return "critical" if val > thresh["max"] else "normal"

    formatted_parameters = ", ".join(parameters) if parameters else None
    default_alert_message = f"The following parameter(s) exceeded EMA limits: {formatted_parameters}. Immediate attention is recommended." if formatted_parameters else "A compliance breach has been detected. Immediate attention is recommended."

    if not message or "unknown parameter" in message.lower():
        display_message = default_alert_message
    elif formatted_parameters and message.strip().endswith(":"):
        display_message = f"{message} {formatted_parameters}."
    elif formatted_parameters and formatted_parameters not in message:
        display_message = f"{message} {formatted_parameters}."
    else:
        display_message = message

    # Build readings table
    sensor_params = ["ph", "temperature", "suspended_solids", "chlorides", "cod"]
    all_readings = {}
    if reading:
        all_readings = {k: reading[k] for k in sensor_params if k in reading and reading[k] is not None}

    readings_table_rows = ""
    for param, value in all_readings.items():
        is_critical = get_parameter_status(param, value) == "critical"
        thresh = critical_thresholds.get(param.lower(), {})
        unit = thresh.get("unit", "")
        bg_color = "#fef2f2" if is_critical else "#ffffff"
        val_color = "#dc2626" if is_critical else "#1e293b"
        status_indicator = '<td style="padding: 12px; font-size: 12px; color: #dc2626; font-weight: 600;">⚠️ Exceeds</td>' if is_critical else '<td style="padding: 12px;"></td>'
        
        param_label = param.replace("_", " ")
        val_str = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
        
        readings_table_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; background-color: {bg_color};">
          <td style="padding: 12px; font-size: 13px; font-weight: 600; color: #4b5563; text-transform: uppercase; letter-spacing: 0.5px;">
            {param_label}
          </td>
          <td style="padding: 12px; text-align: right;">
            <span style="font-size: 18px; font-weight: bold; color: {val_color};">
              {val_str}
            </span>
            <span style="font-size: 12px; color: #64748b; margin-left: 4px;">{unit}</span>
          </td>
          {status_indicator}
        </tr>
        """

    # Build recommendations list
    recs = get_recommendation_list(reading)
    actions_list_html = ""
    for idx, action in enumerate(recs):
        actions_list_html += f"""
      <tr>
        <td style="padding: 12px 12px 12px 12px; vertical-align: top; font-size: 14px; color: #1e40af;">
          <strong>{idx + 1}.</strong>
        </td>
        <td style="padding: 12px; font-size: 14px; color: #1e3a8a;">{action}</td>
      </tr>
        """

    formatted_time = format_timestamp(timestamp)

    affected_params_html = ""
    if parameters:
        param_list_str = ", ".join(parameters)
        affected_params_html = f'<p style="font-size: 12px; color: #a16207; margin-top: 12px;"><strong>Affected Parameters:</strong> {param_list_str}</p>'

    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EffluAI Compliance Alert</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif; }
    * { margin: 0; padding: 0; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  </style>
</head>
<body style="background: linear-gradient(to bottom right, #f8fafc, #f3f4f6); padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto;">
    <tr>
      <td>
        <!-- Main Card -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.1); border: 1px solid #e2e8f0;">
          
          <!-- Header -->
          <tr style="background: linear-gradient(to right, __SEVERITY_COLOR__, __SEVERITY_COLOR__dd); color: white;">
            <td style="padding: 32px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="font-size: 28px; margin-right: 12px; display: inline-block;">⚠️</div>
                    <h1 style="font-size: 28px; font-weight: bold; display: inline-block;">Compliance Alert</h1>
                  </td>
                </tr>
              </table>
              <p style="margin-top: 12px; font-size: 13px; opacity: 0.95; line-height: 1.5;">
                A regulatory violation has been detected in your monitoring system. Immediate attention is recommended.
              </p>
            </td>
          </tr>

          <!-- Content -->
          <tr>
            <td style="padding: 32px;">
              <!-- Info Grid -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
                <tr>
                  <td width="33%" style="padding-right: 12px;">
                    <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                      <p style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Industry ID</p>
                      <p style="font-size: 16px; font-weight: bold; color: #1e293b;">__INDUSTRY_ID__</p>
                    </div>
                  </td>
                  <td width="33%" style="padding: 0 6px;">
                    <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                      <p style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Alert Type</p>
                      <p style="font-size: 16px; font-weight: bold; color: #1e293b;">__ALERT_TYPE__</p>
                    </div>
                  </td>
                  <td width="33%" style="padding-left: 12px;">
                    <div style="background: __SEVERITY_COLOR__; border-radius: 8px; padding: 16px; color: white;">
                      <p style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; opacity: 0.9;">Severity</p>
                      <p style="font-size: 16px; font-weight: bold;">__SEVERITY__</p>
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Alert Summary -->
              <div style="background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 4px; padding: 16px; margin-bottom: 24px;">
                <p style="font-size: 12px; font-weight: 600; color: #92400e; margin-bottom: 8px;">Alert Summary</p>
                <p style="font-size: 13px; color: #b45309; line-height: 1.6; margin-bottom: 8px;">__DISPLAY_MESSAGE__</p>
                __AFFECTED_PARAMS_HTML__
              </div>

              <!-- Timestamp & Status -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
                <tr>
                  <td width="50%" style="padding-right: 12px;">
                    <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                      <p style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Detected At</p>
                      <p style="font-size: 12px; font-family: 'Courier New', monospace; color: #1e293b;">__DETECTED_AT__</p>
                    </div>
                  </td>
                  <td width="50%" style="padding-left: 12px;">
                    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px;">
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <div style="width: 8px; height: 8px; background: #ef4444; border-radius: 50%; animation: pulse 2s infinite;"></div>
                        <span style="font-size: 11px; font-weight: 600; color: #b91c1c; text-transform: uppercase; letter-spacing: 0.5px;">Status</span>
                      </div>
                      <p style="font-size: 16px; font-weight: bold; color: #b91c1c;">__STATUS__</p>
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Sensor Readings -->
              __SENSOR_READINGS_SECTION__

              <!-- Recommended Actions -->
              __RECOMMENDED_ACTIONS_SECTION__

              <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">

              <!-- Footer -->
              <div style="text-align: center; color: #64748b;">
                <p style="font-size: 12px; margin-bottom: 12px;">
                  This alert was generated automatically by the EffluAI monitoring system.
                </p>
                <div style="font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 8px;">
                  EffluAI Monitoring System
                </div>
                <p style="font-size: 12px; color: #94a3b8;">
                  Visit your dashboard for complete details and immediate actions.
                </p>
              </div>
            </td>
          </tr>

          <!-- Bottom Branding -->
          <tr style="background: linear-gradient(to right, #f1f5f9, #f3f4f6); border-top: 1px solid #e2e8f0;">
            <td style="padding: 16px; text-align: center;">
              <p style="font-size: 12px; color: #64748b;">
                © 2026 EffluAI. Industrial Wastewater Compliance Monitoring.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""

    html = html.replace("__SEVERITY_COLOR__", severity_color)
    html = html.replace("__INDUSTRY_ID__", industry_id)
    html = html.replace("__ALERT_TYPE__", alert_type.replace("_", " "))
    html = html.replace("__SEVERITY__", severity)
    html = html.replace("__DISPLAY_MESSAGE__", display_message)
    html = html.replace("__AFFECTED_PARAMS_HTML__", affected_params_html)
    html = html.replace("__DETECTED_AT__", formatted_time)
    html = html.replace("__STATUS__", compliance_status)

    sensor_readings_section = ""
    if all_readings:
        sensor_readings_section = f"""
              <div style="margin-bottom: 24px;">
                <h3 style="font-size: 12px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Sensor Readings</h3>
                <table width="100%" cellpadding="0" cellspacing="0" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                  <thead>
                    <tr style="background: #f1f5f9; border-bottom: 1px solid #e2e8f0;">
                      <th style="padding: 12px; font-size: 12px; font-weight: 600; color: #475569; text-align: left; text-transform: uppercase; letter-spacing: 0.5px;">Parameter</th>
                      <th style="padding: 12px; font-size: 12px; font-weight: 600; color: #475569; text-align: right; text-transform: uppercase; letter-spacing: 0.5px;">Value</th>
                      <th style="padding: 12px; font-size: 12px; font-weight: 600; color: #475569; text-align: right; text-transform: uppercase; letter-spacing: 0.5px;"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {readings_table_rows}
                  </tbody>
                </table>
              </div>
        """
    html = html.replace("__SENSOR_READINGS_SECTION__", sensor_readings_section)

    recommended_actions_section = ""
    if recs:
        recommended_actions_section = f"""
              <div style="margin-bottom: 24px;">
                <h3 style="font-size: 12px; font-weight: 600; color: #1e3a8a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Recommended Actions</h3>
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 0;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    {actions_list_html}
                  </table>
                </div>
              </div>
        """
    html = html.replace("__RECOMMENDED_ACTIONS_SECTION__", recommended_actions_section)

    return html


def send_alert_email(site_id, alert_payload, reading=None):
    """
    Sends compliance alert emails in a background thread to prevent blocking requests.
    If RESEND_API_KEY is configured in settings, sends via Resend's HTTP API.
    Otherwise, falls back to Django's standard SMTP backend.
    """
    def _send():
        try:
            subject = f"EffluAI Alert - {alert_payload['title']}"

            # Generate rich HTML representation of the email
            html_content = generate_compliance_alert_html(site_id, alert_payload, reading)

            # Generate fallback plain text content
            values_section = ""
            if reading:
                values_section = f"""
Sensor Readings

pH: {reading.get('ph')}
Temperature: {reading.get('temperature')}
Suspended Solids: {reading.get('suspended_solids')}
Chlorides: {reading.get('chlorides')}
COD: {reading.get('cod')}
"""

            legacy_recs = get_recommendation(reading)
            recommendation_section = f"\nRecommended Action\n{legacy_recs}\n" if legacy_recs else ""

            text_content = f"""
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

            recipients = [
                "shumiraishiri@gmail.com",
                "shiriyapindashumirai@gmail.com",
            ]

            api_key = getattr(settings, "RESEND_API_KEY", None)
            if api_key:
                from_email = settings.DEFAULT_FROM_EMAIL
                # Fallback to Resend onboarding email if custom verified domain not set yet
                if "gmail.com" in from_email.lower():
                    from_email = "EffluAI Alerts <onboarding@resend.dev>"

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "from": from_email,
                    "to": recipients,
                    "subject": subject,
                    "html": html_content,
                }
                try:
                    response = requests.post(
                        "https://api.resend.com/emails",
                        json=payload,
                        headers=headers,
                        timeout=10,
                    )
                    response.raise_for_status()
                    # Successfully sent via Resend API
                    return
                except Exception as e:
                    # Fall back to standard SMTP on error
                    print(f"Failed to send email via Resend API: {e}. Falling back to SMTP.")

            # Standard SMTP Fallback (supports html_message out-of-the-box in Django)
            send_mail(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                html_message=html_content,
                fail_silently=False,
            )
        except Exception as thread_err:
            print(f"Background email send thread failed: {thread_err}")

    # Run in a background thread so it doesn't block the request
    thread = threading.Thread(target=_send)
    thread.start()