import math
import random
import time
from datetime import datetime



# ---------------------------------------------------
# CORE DRIFT MODEL
# ---------------------------------------------------

def drift(base, amplitude, noise_level, speed, phase_shift=0):
    t = (time.time() + phase_shift) / speed
    wave = amplitude * math.sin(t)
    noise = random.uniform(-noise_level, noise_level)
    return base + wave + noise



# ---------------------------------------------------
# PARAMETER SIMULATORS
# ---------------------------------------------------

def simulate_temperature(site_type="industry", phase=0):
    base = 24 if site_type == "industry" else 22
    value = drift(base, amplitude=1.5, noise_level=0.3, speed=60, phase_shift=phase)
    return round(value, 2)


def simulate_ph(site_type="industry", phase=0):
    base = 7.1 if site_type == "industry" else 7.0
    value = drift(base, amplitude=0.35, noise_level=0.08, speed=12, phase_shift=phase)
    return round(value, 2)



def simulate_suspended_solids(site_type="industry", phase=0):
    base = 70 if site_type == "industry" else 55
    value = drift(base, amplitude=15, noise_level=5, speed=8, phase_shift=phase)
    return round(value, 2)


def simulate_cod(site_id=None):
    base = random.uniform(160, 210)

    # Industry C has higher risk
    anomaly_probability = 0.15 if site_id == "IND_C" else 0.05

    if random.random() < anomaly_probability:
        # Gradual anomaly ramp
        ramp = random.uniform(30, 80)
        base += ramp

    return round(base, 2)


def simulate_chlorides(site_id=None):
    base = random.uniform(220, 300)

    anomaly_probability = 0.12 if site_id == "IND_C" else 0.04

    if random.random() < anomaly_probability:
        base += random.uniform(50, 120)

    return round(base, 2)



# ---------------------------------------------------
# SITE-SPECIFIC GENERATION
# ---------------------------------------------------

def generate_industry_reading(industry_id):
    """
    Generates readings per industry.

    Industry A:
        - Temperature REAL (handled elsewhere)
        - pH REAL
        - Suspended Solids REAL
        - COD simulated
        - Chlorides simulated

    Industry B & C:
        - Fully simulated
    """

    if industry_id == "IND_A":
        return {
            # These three should be replaced by your sensor input pipeline
            "temperature": None,
            "ph": None,
            "suspended_solids": None,
            "cod": simulate_cod(industry_id),
            "chlorides": simulate_chlorides(industry_id),

        }

    # Industry B & C fully simulated
    phase_map = {
        "IND_B": 20,
        "IND_C": 40,
    }

    phase = phase_map.get(industry_id, 0)

    return {
        "temperature": simulate_temperature("industry", phase),
        "ph": simulate_ph("industry", phase),
        "suspended_solids": simulate_suspended_solids("industry", phase),
        "cod": simulate_cod(industry_id),
        "chlorides": simulate_chlorides(industry_id),

    }



def generate_stp_reading(stp_id):

    return {
        "temperature": simulate_temperature("stp"),
        "ph": simulate_ph("stp"),
        "suspended_solids": simulate_suspended_solids("stp"),
        "cod": round(random.uniform(80, 140), 2),
        "chlorides": round(random.uniform(120, 200), 2),
    }

