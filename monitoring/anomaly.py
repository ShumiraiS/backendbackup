import math

PARAMS = ["ph", "temperature", "cod", "chlorides", "suspended_solids"]


def _safe_mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def _safe_std(values, mean):
    if not values or mean is None:
        return None
    var = sum((v - mean) ** 2 for v in values) / max(1, (len(values) - 1))
    return math.sqrt(var)


def anomaly_score_from_history(history, latest, z_threshold=2.0):
    """
    Unsupervised anomaly detection:
    - Uses recent history to estimate mean/std per parameter
    - Computes z-score for latest reading
    - Returns anomaly_score (0-100) + which parameters look abnormal

    history: list of dicts (past readings)
    latest: dict (latest reading)
    """
    if not history or len(history) < 3:
        return {
            "anomaly_score": 0,
            "is_anomaly": False,
            "anomalous_parameters": [],
            "z_scores": {}
        }

    z_scores = {}
    anomalous = []

    for p in PARAMS:
        hist_vals = [r.get(p) for r in history if isinstance(r.get(p), (int, float))]
        current = latest.get(p)

        if current is None or not isinstance(current, (int, float)) or len(hist_vals) < 3:
            continue

        mean = _safe_mean(hist_vals)
        std = _safe_std(hist_vals, mean)

        if std is None or std == 0:
            # No variation -> cannot compute meaningful anomaly
            continue

        z = (current - mean) / std
        z_scores[p] = round(z, 3)

        if abs(z) >= z_threshold:
            anomalous.append(p)

    # Score: scale by how many parameters are anomalous + how large z is
    if not z_scores:
        return {
            "anomaly_score": 0,
            "is_anomaly": False,
            "anomalous_parameters": [],
            "z_scores": {}
        }

    severity = sum(min(4.0, abs(z_scores[p])) for p in anomalous)  # cap each contribution
    breadth = len(anomalous) / len(PARAMS)

    raw = (severity * 15) + (breadth * 40)  # tuned to feel intuitive
    score = int(min(100, max(0, raw)))

    return {
        "anomaly_score": score,
        "is_anomaly": score >= 50,  # you can adjust this
        "anomalous_parameters": anomalous,
        "z_scores": z_scores
    }
