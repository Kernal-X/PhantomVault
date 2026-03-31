import pickle
import pandas as pd


class FileModel:

    def __init__(self, model_path):
        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.rf = data["rf_model"]
        self.iso = data["iso_model"]
        self.rf_features = data["rf_features"]
        self.iso_features = data["iso_features"]

    # -------- SAME AS TRAIN.PY --------
    def clamp01(self, x):
        return max(0.0, min(1.0, float(x)))

    # -------- SAME RULE ENGINE --------
    def compute_rule_score(self, row):

        score = 0.0
        reasons = []

        system_score = float(row.get("system_score", 0) or 0)
        severity = float(row.get("severity", 0) or 0)
        behavioral_flag = float(row.get("behavioral_anomaly_flag", 0) or 0)
        sensitive_access = float(row.get("sensitive_access_flag", 0) or 0)

        if system_score >= 4:
            score += 0.45
            reasons.append("high_system_score")
        elif system_score >= 3:
            score += 0.30
            reasons.append("elevated_system_score")
        elif system_score >= 2:
            score += 0.15

        if severity >= 2:
            score += 0.20
            reasons.append("high_severity")
        elif severity >= 1:
            score += 0.10

        if behavioral_flag == 1:
            score += 0.20
            reasons.append("behavioral_anomaly_flag")

        if sensitive_access == 1:
            score += 0.15
            reasons.append("sensitive_access_flag")

        return self.clamp01(score), reasons

    # -------- MAIN PREDICT --------
    def predict(self, event):

        df = pd.DataFrame([event])

        # fill missing values
        df = pd.DataFrame([event])

        # ensure all required features exist
        for col in self.rf_features + self.iso_features:
            if col not in df.columns:
                df[col] = 0

        df = df.fillna(0)

        # -------- RF --------
        X_rf = df[self.rf_features]
        rf_prob = self.rf.predict_proba(X_rf)[0][1]

        # -------- ISO --------
        X_iso = df[self.iso_features]
        iso_score = -self.iso.decision_function(X_iso)[0]

        # normalize same way
        iso_prob = self.clamp01(iso_score)

        # -------- RULE --------
        rule_score, reasons = self.compute_rule_score(event)

        # -------- SAME HYBRID FUSION --------
        hybrid_score = (
            0.40 * rule_score +
            0.35 * rf_prob +
            0.25 * iso_prob
        )

        # -------- SAME THRESHOLD LOGIC --------
        if rule_score >= 0.75:
            reason = "Explicit suspicious file-event rule triggered"
        elif rf_prob >= 0.72:
            reason = "Known suspicious file pattern detected"
        elif iso_prob >= 0.88:
            reason = "Novel abnormal file behavior detected"
        elif hybrid_score >= 0.42:
            reason = "Moderately suspicious file activity"
        else:
            reason = "Normal file activity"

        # -------- FINAL OUTPUT --------
        return {
            "risk_score": round(hybrid_score, 4),
            "event": {
                "type": "file",
                "risk_score": round(hybrid_score, 4),
                "data": {
                    "file_path": str(event.get("file_path", "unknown")),
                    "file_action": str(event.get("file_action", "unknown")),
                    "process_name": str(event.get("process_name", "unknown")),
                    "parent_process": str(event.get("parent_process", "unknown")),
                    "rule_score": round(rule_score, 4),
                    "rf_prob": round(rf_prob, 4),
                    "iso_prob": round(iso_prob, 4),
                    "reason": reason,
                    "rule_reasons": reasons
                    
                }
            }
        }