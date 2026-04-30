def assess_reading(reading, limits):
    """
    Returns overall_status, per_parameter_dict
    """

    statuses = {}

    def check_range(value, min_val=None, max_val=None):
        if value is None:
            return "UNKNOWN"
        if min_val is not None and value < min_val:
            return "RED"
        if max_val is not None and value > max_val:
            return "RED"
        return "GREEN"

    statuses["temperature"] = check_range(
        reading.get("temperature"),
        None,
        limits.get("temperature_max"),
    )

    statuses["ph"] = check_range(
        reading.get("ph"),
        limits.get("ph_min"),
        limits.get("ph_max"),
    )

    statuses["cod"] = check_range(
        reading.get("cod"),
        None,
        limits.get("cod_max"),
    )

    statuses["chlorides"] = check_range(
        reading.get("chlorides"),
        None,
        limits.get("chlorides_max"),
    )

    statuses["suspended_solids"] = check_range(
        reading.get("suspended_solids"),
        None,
        limits.get("suspended_solids_max"),
    )

    overall = "GREEN"
    if "RED" in statuses.values():
        overall = "RED"

    return overall, statuses
