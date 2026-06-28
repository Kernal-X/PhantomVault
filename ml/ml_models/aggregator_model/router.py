from __future__ import annotations

from pathlib import Path

from ml.ml_models.file_model.file_model import FileModel
from ml.ml_models.network_model.network_model import NetworkModel
from ml.ml_models.process_model.process_model import ProcessModel


class ModelRouter:

    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent
        self.file_model = self._safe_load(FileModel, base_dir / "file_model" / "file_hybrid_final.pkl")
        self.network_model = self._safe_load(NetworkModel, base_dir / "network_model" / "network_hybrid_model.pkl")
        self.process_model = self._safe_load(ProcessModel, base_dir / "process_model" / "process_hybrid_final.pkl")

        self.models = {
            "file": self.file_model,
            "network": self.network_model,
            "process": self.process_model
        }

    def _safe_load(self, model_cls, model_path: Path):
        if not model_path.exists():
            print(f"[MODEL ROUTER] Missing model artifact: {model_path}")
            return None
        try:
            return model_cls(str(model_path))
        except Exception as exc:
            print(f"[MODEL ROUTER] Failed to load {model_path.name}: {exc}")
            return None

    def route(self, event):

        model = self.models.get(event["type"])

        if not model:
            return {
                "risk_score": 0.0,
                "event": {
                    "type": event["type"],
                    "risk_score": 0.0,
                    "data": {"reason": "no model found"}
                }
            }

        return model.predict(event)
