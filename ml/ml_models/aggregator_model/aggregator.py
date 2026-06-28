import time
import copy


class StreamingAggregator:

    def __init__(self, threshold=1.5, decay=0.9,max_events=100):
        self.threshold = threshold
        self.decay = decay
        self.max_events = max_events

        self.aggregator_score = 0.0
        self.event_queue = []

    # -------- Add event --------
    def add_event(self, event):
        """
        event = {
            "type": "network",
            "risk_score": 0.7,
            "data": {...}
        }
        """
        # add timestamp

        event_copy = copy.deepcopy(event)
        event_copy["timestamp"] = time.time()

        # store event
        self.event_queue.append(event_copy)

        # update score
        self.update_score(event["risk_score"])

        # -------- Trigger condition --------
        if self.aggregator_score >= self.threshold:
            output = self.build_output()

            result = {
                "alert": True,
                "data": output
            }

            self.reset()
            return result

        # -------- No trigger --------
        return {
            "alert": False,
            "state": {
                "risk_score": round(self.aggregator_score, 3),
                "events": self.event_queue
            }
        }

    # -------- Score update --------
    def update_score(self, risk_score):
        self.aggregator_score = (
            self.decay * self.aggregator_score + risk_score
        )

    # -------- Final Output --------
    def build_output(self):

        # sort events by importance (optional but useful)
        sorted_events = sorted(
            self.event_queue,
            key=lambda x: x["risk_score"],
            reverse=True
        )

        return {
            "risk_score": float(round(self.aggregator_score, 3)),
            "events": [
                {
                    "type": e["type"],
                    "risk_score": float(round(e["risk_score"], 3)),
                    "data": e["data"]
                }
                for e in sorted_events
            ]
        }

    # -------- Reset --------
    def reset(self):
        self.aggregator_score = 0.0
        self.event_queue = []