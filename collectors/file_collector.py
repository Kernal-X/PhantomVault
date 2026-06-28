import os
import time
import threading
from typing import Dict, Iterable, List

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class _BufferedFileEventHandler(FileSystemEventHandler):
    def __init__(self, collector: "FileCollector"):
        super().__init__()
        self._collector = collector

    def on_created(self, event):
        if not event.is_directory:
            self._collector._push_event(event.src_path, "created")

    def on_modified(self, event):
        if not event.is_directory:
            self._collector._push_event(event.src_path, "modified")

    def on_deleted(self, event):
        if not event.is_directory:
            self._collector._push_event(event.src_path, "deleted")


class FileCollector:
    def __init__(self, path: str | Iterable[str] = ".", recursive: bool = True):
        self.paths = self._normalize_paths(path)
        self.recursive = recursive
        self._events: List[Dict] = []
        self._lock = threading.Lock()
        self._observer = Observer()
        self._handler = _BufferedFileEventHandler(self)
        self._started = False
        self.start()

    def _push_event(self, file_path: str, action: str) -> None:
        event = {
            "type": "file_access",
            "timestamp": time.time(),
            "data": {
                "file_path": str(file_path),
                "action": action,
            },
        }
        with self._lock:
            self._events.append(event)

    def start(self):
        if self._started:
            return
        scheduled = 0
        for watch_path in self.paths:
            if not os.path.isdir(watch_path):
                print(f"[FILE COLLECTOR] Skipping missing watch path: {watch_path}")
                continue
            self._observer.schedule(self._handler, watch_path, recursive=self.recursive)
            scheduled += 1

        if scheduled == 0:
            raise ValueError("FileCollector could not schedule any valid watch paths.")

        self._observer.start()
        self._started = True

    def stop(self):
        if not self._started:
            return
        self._observer.stop()
        self._observer.join(timeout=2)
        self._started = False

    def collect(self) -> List[Dict]:
        with self._lock:
            events = self._events[:]
            self._events.clear()
        return events

    def _normalize_paths(self, value: str | Iterable[str]) -> List[str]:
        if isinstance(value, str):
            raw_paths = [value]
        else:
            raw_paths = list(value or [])

        normalized: List[str] = []
        for item in raw_paths:
            if not item:
                continue
            expanded = os.path.expandvars(os.path.expanduser(str(item)))
            normalized.append(os.path.abspath(expanded))

        if not normalized:
            normalized.append(os.path.abspath("."))

        # Preserve order while deduplicating.
        return list(dict.fromkeys(normalized))
