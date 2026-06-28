# agents/deployment/deployment_agent.py
import os
import json

from agents.deployment.decoy_registry import DecoyRegistry
from agents.deployment.context_builder import build_global_context
from agents.deployment.rule_engine import build_interception_rules
from core.path_resolver import normalize_path, resolve_path


class DeploymentManager:

    def __init__(self, generation_agent=None):
        self.registry_file = "registry.json"
        self.registry = DecoyRegistry()
        self._load_registry()
        self.global_context = {}
        self.interception_rules = {}
        self.generation_agent = generation_agent

    def _load_registry(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r") as f:
                    data = json.load(f)
                    for p, meta in data.items():
                        self.registry.add(p, meta)
            except Exception as e:
                print(f"[DEPLOYMENT] Failed to load registry: {e}")

    def _save_registry(self):
        try:
            with open(self.registry_file, "w") as f:
                json.dump(self.registry.get_all(), f, indent=2)
        except Exception as e:
            print(f"[DEPLOYMENT] Failed to save registry: {e}")

    def deploy(self, strategy_output, analysis=None, materialize_files: bool = True):
        """
        Main entry point
        """
        self.global_context = {}
        self.interception_rules = {}

        self._build_registry(strategy_output)
        self._save_registry()
        self.global_context = build_global_context()
        self.interception_rules = build_interception_rules(
            self.registry.get_all()
        )

        if materialize_files:
            for path, metadata in self.registry.get_all().items():
                self._materialize_file(path, metadata, analysis or {})

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

            original_path = path
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
                "sensitivity": self._infer_sensitivity(path, content_type),
                "real_os_path": original_path
                
            }

            self.registry.add(path, metadata)

    def _materialize_file(self, path, metadata, analysis):
        try:
            real_path = metadata.get("real_os_path")
            if not real_path:
                real_path = resolve_path(path)

            os.makedirs(os.path.dirname(real_path), exist_ok=True)

            # Dynamic File Swapping (Quarantine & Replace)
            # If the file already exists, it's a real file that the attacker is targeting.
            # We move it to a safe ".aads_vault" extension, then write the fake file in its place!
            if os.path.exists(real_path):
                vault_path = real_path + ".aads_vault"
                if not os.path.exists(vault_path):
                    import shutil
                    import ctypes
                    try:
                        shutil.move(real_path, vault_path)
                        print(f"[DEPLOYMENT] Vaulted real file for interception: {real_path}")
                        
                        # 1. NTFS Cloaking: Hide the vault file from the attacker
                        # FILE_ATTRIBUTE_HIDDEN = 0x02, FILE_ATTRIBUTE_SYSTEM = 0x04
                        ctypes.windll.kernel32.SetFileAttributesW(vault_path, 0x02 | 0x04)
                        
                        # 3. Log transaction for automated recovery
                        self._log_transaction(real_path, vault_path)
                        
                    except PermissionError:
                        # 2. Graceful Lock Handling: Pivot to an adjacent decoy if file is in use
                        print(f"[DEPLOYMENT WARNING] File {real_path} is locked by another process!")
                        base, ext = os.path.splitext(real_path)
                        real_path = base + "_Q3_draft" + ext
                        print(f"[DEPLOYMENT PIVOT] Dynamically targeting adjacent decoy instead: {real_path}")
                    except Exception as e:
                        print(f"[DEPLOYMENT ERROR] Could not vault {real_path}: {e}")
                        return
                else:
                    # It's already been vaulted and replaced with a decoy previously
                    pass

            content = self._generate_placeholder(path, metadata, analysis)

            with open(real_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[DEPLOYMENT ERROR] {path}: {e}")

    def _generate_placeholder(self, path, metadata, analysis):
        if self.generation_agent:
            enriched_metadata = {**metadata, "analysis": analysis}
            try:
                result = self.generation_agent.generate(path, enriched_metadata)
                if result and "content" in result:
                    return result["content"]
            except Exception as e:
                print(f"[DEPLOYMENT GENERATION ERROR] {path}: {e}")

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

    def _log_transaction(self, real_path, vault_path):
        import json
        tx_log = "vault_transactions.json"
        transactions = {}
        if os.path.exists(tx_log):
            try:
                with open(tx_log, "r") as f:
                    transactions = json.load(f)
            except: pass
        transactions[real_path] = vault_path
        with open(tx_log, "w") as f:
            json.dump(transactions, f)

    def restore_vaults(self):
        import json, shutil, ctypes
        tx_log = "vault_transactions.json"
        if not os.path.exists(tx_log):
            print("No active vaults to restore.")
            return
            
        with open(tx_log, "r") as f:
            transactions = json.load(f)
            
        restored = 0
        for real_path, vault_path in transactions.items():
            if os.path.exists(vault_path):
                if os.path.exists(real_path):
                    try:
                        os.remove(real_path) # Remove the fake decoy
                    except: pass
                # Remove NTFS cloaking so we can move it back
                try:
                    # FILE_ATTRIBUTE_NORMAL = 128
                    ctypes.windll.kernel32.SetFileAttributesW(vault_path, 128)
                    shutil.move(vault_path, real_path)
                    restored += 1
                except Exception as e:
                    print(f"[RECOVERY ERROR] Failed to restore {real_path}: {e}")
                
        # Clear log after successful restoration
        try:
            os.remove(tx_log)
        except: pass
        print(f"[DEPLOYMENT] Successfully restored {restored} vaulted files from safety.")

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
