def param_status(value, *, min_val=None, max_val=None):
    """
    Returns GREEN/YELLOW/RED for one parameter based on thresholds.
    YELLOW is a warning band near the limit (10%).
    """
    if value is None:
        return "UNKNOWN"

    # Within range
    if min_val is not None and value < min_val:
        # Below min: RED, but allow YELLOW if within 10% of min
        band = 0.10 * abs(min_val)
        return "YELLOW" if value >= (min_val - band) else "RED"

    if max_val is not None and value > max_val:
        band = 0.10 * abs(max_val)
        return "YELLOW" if value <= (max_val + band) else "RED"

    return "GREEN"


def overall_status(statuses: dict):
    """
    Worst-case logic: if any RED -> RED, else if any YELLOW -> YELLOW, else GREEN.
    """
    if any(s == "RED" for s in statuses.values()):
        return "RED"
    if any(s == "YELLOW" for s in statuses.values()):
        return "YELLOW"
    if any(s == "GREEN" for s in statuses.values()):
        return "GREEN"
    return "UNKNOWN"


def assess_reading(reading: dict, limits: dict):
    """
    reading: {ph, temperature, cod, chlorides, suspended_solids}
    limits:  {ph_min, ph_max, temperature_max, cod_max, chlorides_max, suspended_solids_max}
    """
    statuses = {
        "ph": param_status(reading.get("ph"), min_val=limits.get("ph_min"), max_val=limits.get("ph_max")),
        "temperature": param_status(reading.get("temperature"), max_val=limits.get("temperature_max")),
        "cod": param_status(reading.get("cod"), max_val=limits.get("cod_max")),
        "chlorides": param_status(reading.get("chlorides"), max_val=limits.get("chlorides_max")),
        "suspended_solids": param_status(reading.get("suspended_solids"), max_val=limits.get("suspended_solids_max")),
    }

    overall = overall_status(statuses)
    return overall, statuses