import pickle
import pandas as pd


class NetworkModel:

    def __init__(self, model_path):
        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.rf = data["rf_model"]
        self.iso = data["iso_model"]
        self.rf_features = data["rf_features"]
        self.iso_features = data["iso_features"]

    # -------- EXACT RULE ENGINE FROM TRAIN.PY --------
    def compute_rule_score(self, row):
        score = 0.0
        reasons = []

        if row.get("severity", 0) >= 2:
            score += 0.20
            reasons.append("high_severity")

        if row.get("system_score", 0) >= 3:
            score += 0.20
            reasons.append("high_system_score")

        if row.get("behavioral_anomaly_flag", 0) == 1:
            score += 0.20
            reasons.append("behavioral_flag")

        if row.get("external_connection_flag", 0) == 1:
            score += 0.10
            reasons.append("external_connection")

        if row.get("is_known_ip", 1) == 0:
            score += 0.15
            reasons.append("unknown_ip")

        if row.get("port_risk", 0) >= 0.7:
            score += 0.15
            reasons.append("high_risk_port")

        if row.get("connection_freq_1min", 0) > 20:
            score += 0.10
            reasons.append("high_connection_rate")

        if row.get("unique_ip_5min", 0) > 15:
            score += 0.10
            reasons.append("ip_scanning")

        return min(score, 1.0), reasons

    # -------- PREDICT (MATCH TRAIN FLOW) --------
    def predict(self, event):

        df = pd.DataFrame([event])

        # ensure all required features exist
        for col in self.rf_features + self.iso_features:
            if col not in df.columns:
                df[col] = 0

        df = df.fillna(0)

        # RF
        X_rf = df[self.rf_features]
        rf_prob = self.rf.predict_proba(X_rf)[0][1]

        # ISO (RAW — NO NORMALIZATION)
        X_iso = df[self.iso_features]
        iso_score = -self.iso.decision_function(X_iso)[0]

        # RULE
        rule_score, reasons = self.compute_rule_score(event)


        # -------- EXACT HYBRID --------
        hybrid_score = (
            0.45 * rule_score +
            0.30 * rf_prob +
            0.25 * iso_score
        )

        # -------- SAME THRESHOLD LOGIC --------
        if (rule_score >= 0.6) or (rf_prob >= 0.8) or (iso_score >= 0.7):
            final_score = max(hybrid_score, 0.8)
        else:
            final_score = hybrid_score

        return {
            "risk_score": round(final_score, 4),
            "event": {
                "type": "network",
                "risk_score": round(final_score, 4),
                "data": {
                    "rf_prob": round(rf_prob, 4),
                    "iso_score": round(iso_score, 4),
                    "rule_score": round(rule_score, 4),
                    "reason": ", ".join(reasons) if reasons else "normal traffic",
                    **event
                }
            }
        }