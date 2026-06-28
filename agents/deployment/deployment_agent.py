# agents/deployment/deployment_agent.py
import os

from agents.deployment.decoy_registry import DecoyRegistry
from agents.deployment.context_builder import build_global_context
from agents.deployment.rule_engine import build_interception_rules
from core.path_resolver import normalize_path, resolve_path


class DeploymentManager:

    def __init__(self):
        self.registry = DecoyRegistry()
        self.global_context = {}
        self.interception_rules = {}

    def deploy(self, strategy_output, materialize_files: bool = True):
        """
        Main entry point
        """
        self.registry = DecoyRegistry()
        self.global_context = {}
        self.interception_rules = {}

        self._build_registry(strategy_output)
        self.global_context = build_global_context()
        self.interception_rules = build_interception_rules(
            self.registry.get_all()
        )

        if materialize_files:
            for path, metadata in self.registry.get_all().items():
                self._materialize_file(path, metadata)

        return self.get_state()

    # ------------------------
    # INTERNAL METHODS
    # ------------------------

    def _build_registry(self, strategy_output):

        SUPPORTED_TYPES = ["csv", "txt", "log", "json", "env","sql"]

        files = strategy_output.get("execution_plan", {}).get("files_to_create", [])

        for file in files:

            # ------------------------
            # FIX 1: Correct path key
            # ------------------------
            path = file.get("absolute_path") or file.get("path")

            if not path:
                print("[WARNING] Missing path, skipping file")
                continue

            path = normalize_path(path)

            # ------------------------
            # FIX 2: Extract file type properly
            # ------------------------
            file_type = file.get("file_type")

            # fallback from mime_type_hint
            if not file_type:
                mime = file.get("mime_type_hint", "")
                if "csv" in mime:
                    file_type = "csv"
                elif "json" in mime:
                    file_type = "json"
                elif "log" in mime:
                    file_type = "log"
                elif "env" in mime:
                    file_type = "env"
                else:
                    file_type = "txt"

            # ------------------------
            # FILTER unsupported
            # ------------------------
            if file_type not in SUPPORTED_TYPES:
                print(f"[WARNING] Skipping unsupported file type: {file_type}")
                continue

            # ------------------------
            # FIX 3: Clean metadata schema
            # ------------------------
            realism = file.get("realism", "medium")
            size_bytes = file.get("size_bytes_target")

            def map_size(bytes_val):
                if not bytes_val:
                    return "250KB"

                if bytes_val < 1024:
                    return "1KB"
                elif bytes_val < 10 * 1024:
                    return "50KB"
                elif bytes_val < 100 * 1024:
                    return "250KB"
                elif bytes_val < 1024 * 1024:
                    return "1MB"
                else:
                    return "2MB"
            content_type = file.get("content_profile", "generic")

            metadata = {
                "file_type": file_type,

                # unified naming
                "columns": file.get("columns", []),

                # fallback handling
                "content_type": content_type,

                # consistent naming
                "realism": realism,
                "realism_level": realism,
                "use_llm_realism": realism == "high",
                "size":map_size(size_bytes),
                "sensitivity": self._infer_sensitivity(path, content_type)
                
            }

            self.registry.add(path, metadata)

    def _materialize_file(self, path, metadata):
        try:
            real_path = resolve_path(path)

            os.makedirs(os.path.dirname(real_path), exist_ok=True)

            # DO NOT overwrite real files blindly
            if os.path.exists(real_path):
                return

            content = self._generate_placeholder(metadata)

            with open(real_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[DEPLOYMENT ERROR] {path}: {e}")

    def _generate_placeholder(self, metadata):
        ft = metadata["file_type"]
        ct = metadata["content_type"]

        if ft == "csv":
            cols = metadata.get("columns") or ["id", "name", "value"]
            return ",".join(cols) + "\n"

        if ft == "log":
            return "[INIT] System log initialized...\n"

        if ft == "txt":
            if ct == "credentials":
                return "admin: ********\nuser: ********\n"
            return "Internal document\n"

        if ft == "json":
            return "{}"

        if ft == "env":
            return "ENV=production\n"

        return "placeholder"

    def _infer_sensitivity(self, path, content_type):
        path = (path or "").lower()
        content_type = (content_type or "").lower()

        if any(k in path for k in ["password", "secret", "admin", "finance"]):
            return "high"

        if content_type in ["credentials", "salary_data", "employee_data"]:
            return "high"

        if content_type in ["logs", "internal_note"]:
            return "medium"

        return "medium"

    # ------------------------
    # PUBLIC API
    # ------------------------

    def get_state(self):
        return {
            "decoy_registry": self.registry.get_all(),
            "global_context": self.global_context,
            "interception_rules": self.interception_rules
        }
