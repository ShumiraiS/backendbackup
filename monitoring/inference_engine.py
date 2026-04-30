from .firebase import root_ref


def run_inference(reading):
    """
    Loads rules from Firebase and checks if any rule conditions are triggered.
    Returns a list of triggered rules.
    """

    rules = root_ref().child("ai_rules").get() or {}

    triggered = []

    for rule_id, rule in rules.items():

        parameter = rule.get("parameter")
        condition = rule.get("condition")
        threshold = rule.get("threshold")

        value = reading.get(parameter)

        if value is None:
            continue

        if condition == ">" and value > threshold:
            triggered.append(rule)

        elif condition == "<" and value < threshold:
            triggered.append(rule)

    return triggered