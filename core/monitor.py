# core/monitor.py

from collectors.process_collector import ProcessCollector
from collectors.file_collector import FileCollector
from collectors.network_collector import NetworkCollector


class Monitor:
    def __init__(self, interval=1, file_watch_paths=None, file_watch_recursive=True):
        self.process_collector = ProcessCollector(interval=interval)
        self.file_collector = FileCollector(path=file_watch_paths or ".", recursive=file_watch_recursive)
        self.network_collector = NetworkCollector()

    def collect(self):
        events = []

        # collect from process
        events.extend(self.process_collector.collect())

        # collect from file
        events.extend(self.file_collector.collect())

        # collect from network
        events.extend(self.network_collector.collect())

        return events
