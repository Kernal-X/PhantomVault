# core/decision_engine.py

def decide_action(path, metadata, rules, analysis, supported_types):

    intent = analysis.get("intent", "unknown")
    stage = analysis.get("attack_stage", "unknown")
    confidence = analysis.get("confidence", 0.0)

    file_type = metadata.get("file_type", "txt")

    # unsupported → real
    if file_type not in supported_types:
        return "real"

    rule = rules.get(path, {})
    mode = rule.get("deception_mode", "partial")

    # ------------------------
    # LOW CONFIDENCE → SAFE
    # ------------------------
    if confidence < 0.4:
        return "real"

    # ------------------------
    # MEDIUM CONFIDENCE
    # ------------------------
    if 0.4 <= confidence < 0.7:
        # This project uses binary responses: REAL or FAKE.
        # "partial" mode is treated as "fake" for safer deception (no real-data leakage).
        if mode in {"partial", "full"}:
            return "fake"
        return "real"

    # ------------------------
    # HIGH CONFIDENCE
    # ------------------------
    if confidence >= 0.7:

        if intent in ["data_exfiltration", "reconnaissance"]:
            return "fake"

        if stage in ["discovery", "lateral_movement", "exfiltration"]:
            return "fake"

        # This project uses binary responses: REAL or FAKE.
        return "fake" if mode in {"partial", "full"} else "real"

    return "real"