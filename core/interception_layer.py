# core/interception_layer.py

from core.decision_engine import decide_action
from core.path_resolver import normalize_path, resolve_path
import os

class InterceptionLayer:

    def __init__(self, generation_agent=None):
        self.generation_agent = generation_agent
        self.SUPPORTED_TYPES = ["csv", "txt", "log", "json", "env","sql"]

    # ------------------------
    # MAIN ENTRY
    # ------------------------

    def handle(self, input_data):

        original_path = input_data.get("path")
        path = normalize_path(original_path)
        analysis = input_data.get("analysis", {})
        deployment = input_data.get("deployment", {})

        registry = deployment.get("decoy_registry", {})
        rules = deployment.get("interception_rules", {})

        # ------------------------
        # 1️⃣ If no decoy → real
        # ------------------------
        if path not in registry:
            return self._read_real(original_path, reason="no_decoy")

        metadata = registry[path]
        file_type = metadata.get("file_type", "txt")

        # ------------------------
        # 2️⃣ Unsupported → real
        # ------------------------
        if file_type not in self.SUPPORTED_TYPES:
            return self._read_real(path, reason="unsupported_type")

        # ------------------------
        # 3️⃣ Decide action
        # ------------------------
        action = decide_action(
            path,
            metadata,
            rules,
            analysis,
            self.SUPPORTED_TYPES
        )
        print("DECISION:", action)

        # ------------------------
        # 4️⃣ Execute action
        # ------------------------
        if action == "real":
            return self._read_real(original_path, reason="decision_real")

        if action == "partial":
            real = self._read_real(original_path)
            fake = self._generate_fake(path, metadata, deployment,analysis)
            return self._blend(real, fake)

        if action == "fake":
            return self._generate_fake(path, metadata, deployment,analysis)

        return self._read_real(original_path, reason="fallback")

    # ------------------------
    # HELPERS
    # ------------------------

    def _generate_fake(self, path, metadata, deployment,analysis):
        if not self.generation_agent:
            return "[ERROR] No generation agent available"

        enriched_metadata = {
            **metadata,
            "analysis": analysis   # 🔥 inject here
        }
        result=self.generation_agent.generate(path, enriched_metadata)

        return result['content']

    def _read_real(self, path, reason=None):
        real_path = path

        if not os.path.exists(real_path):
            return f"[REAL:missing] {path}"

        content = None
        for enc in ["utf-8", "utf-16"]:
            try:
                with open(real_path, "r", encoding=enc) as f:
                    content = f.read()
                    break
            except:
                continue

        if content is None:
            return f"[REAL:binary_or_unsupported] {path}"

        if reason:
            return f"[REAL:{reason}]\n{content}"

        return content

    def _blend(self, real, fake):
        return f"{real}\n---PARTIAL-DECEPTION---\n{fake}"
