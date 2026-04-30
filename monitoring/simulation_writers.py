from monitoring.firebase import root_ref
from monitoring.simulation_engine import (
    generate_industry_reading,
    generate_stp_reading
)
from datetime import datetime


def write_industry_reading(industry_id):
    data = generate_industry_reading(industry_id)
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"

    ref = root_ref().child("readings").child(industry_id)
    key = ref.push().key
    ref.child(key).set(data)


def write_stp_reading(stp_id):
    data = generate_stp_reading(stp_id)
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"

    ref = root_ref().child("readings_stp").child(stp_id)
    key = ref.push().key
    ref.child(key).set(data)
