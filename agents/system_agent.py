import time

from agents.event_enrichment import EventEnricher
from core.monitor import Monitor
from detectors.scoring import ScoringDetector
from utils.filters import EventFilter
from logs.logger import SOCLogger


class SystemAgent:
    def __init__(self):
        self.monitor = Monitor(interval=1)
        self.detector = ScoringDetector(alert_threshold=0, suspicious_threshold=0)
        self.event_filter = EventFilter()
        self.logger = SOCLogger(rate_limit_seconds=30)
        self.enricher = EventEnricher()

    def start(self):
        try:
            while True:
                events = self.monitor.collect()

                for event in events:
                    self.enricher.enrich(event)

                    # Remove noise
                    if self.event_filter.should_ignore_noise(event):
                        continue

                    # Analyze behavior
                    detection = self.detector.analyze(event)

                    # Apply trust logic
                    if not self.event_filter.apply_known_process_logic(event, detection):
                        continue

                    # Emit alert (handles cooldown + formatting)
                    result=self.logger.emit(event, detection)
                    if result is not None:
                        # this already contains ML + aggregation output
                        pass  # (next step: send to analysis agent)

        except KeyboardInterrupt:
            return