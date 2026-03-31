import time

# -------- FIX IMPORT PATH --------
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.ml_models.aggregator_model.aggregator import StreamingAggregator
from ml.ml_models.aggregator_model.router import ModelRouter


class Pipeline:

    def __init__(self):
        self.router = ModelRouter()
        self.aggregator = StreamingAggregator(threshold=1.5, decay=0.9)

        print("Pipeline Initialized")

    def process_event(self, event):

        # -------- Step 1: Router → Model --------
        model_output = self.router.route(event)

        risk_score = model_output["risk_score"]
        event_struct = model_output["event"]   # 🔥 KEY FIX

        print("\n📌 Event Type:", event["type"])
        print("➡ Risk Score:", round(risk_score, 4))

        # -------- Step 2: Aggregator --------
        agg_result = self.aggregator.add_event(event_struct)

        print("📊 Aggregator Output:", agg_result)

        # -------- Step 3: Threshold Check --------
        if agg_result["alert"]:
            print("\n ALERT TRIGGERED")
            print(agg_result["data"])

        return agg_result


# =====================================================
# TEST PIPELINE
# =====================================================
if __name__ == "__main__":

    pipeline = Pipeline()

    events = [

        {
            "type": "network",
            "remote_port": 80,
            "connection_freq_1min": 5,
            "unique_ip_5min": 2,
            "is_known_ip": 1
        },

        {
            "type": "network",
            "remote_port": 4444,
            "connection_freq_1min": 30,
            "unique_ip_5min": 20,
            "is_known_ip": 0,
            "severity": 2,
            "system_score": 3
        },

        {
            "type": "process",
            "cpu_percent": 85,
            "memory_mb": 600,
            "cpu_zscore": 3.0,
            "memory_zscore": 2.5,
            "unknown_process_flag": 1,
            "behavioral_anomaly_flag": 1
        },

        {
            "type": "file",
            "system_score": 3,
            "sensitive_access_flag": 1,
            "behavioral_anomaly_flag": 1
        }
    ]

    for event in events:
        pipeline.process_event(event)
        time.sleep(1)