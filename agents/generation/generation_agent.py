import os
import json
import hashlib

from .cache import get_file, set_file
from .schema_resolver import resolve
from .data_generator import generate as generate_base_data
from .consistency_engine import apply as apply_consistency
from .realism_enhancer import apply as apply_realism
from .validators import validate, validate_metadata
from core.path_resolver import resolve_path


class GenerationAgent:
    """
    Main Generation Agent for AADS.

    Responsibilities:
    - validate metadata contract
    - check if fake artifact already exists in cache
    - resolve schema if needed
    - generate structured fake content
    - enforce consistency across fake org context
    - enhance realism
    - validate output
    - cache and return final result
    """

    def __init__(self):
        pass

    # -----------------------------------
    # METADATA NORMALIZATION
    # -----------------------------------

    def _normalize_metadata(self, metadata):
        metadata = metadata or {}

        return {
            "file_type": str(metadata.get("file_type", "")).strip().lower(),
            "content_type": str(metadata.get("content_type", "")).strip().lower(),
            "size": str(metadata.get("size", "")).strip(),
            "sensitivity": str(metadata.get("sensitivity", "medium")).strip().lower(),
            "realism_level": str(metadata.get("realism_level", "medium")).strip().lower(),
            "use_llm_realism": bool(metadata.get("use_llm_realism", False)),
            "columns": metadata.get("columns", [])
        }

    # -----------------------------------
    # CACHE KEY VERSIONING
    # -----------------------------------

    def _build_cache_key(self, path, metadata):
        """
        Make cache metadata-aware so different requests for the same path
        (e.g. sql vs csv, low vs high sensitivity) don't collide.
        """
        stable_payload = {
            "path": path,
            "file_type": metadata.get("file_type", ""),
            "content_type": metadata.get("content_type", ""),
            "size": metadata.get("size", ""),
            "sensitivity": metadata.get("sensitivity", ""),
            "realism_level": metadata.get("realism_level", ""),
            "use_llm_realism": metadata.get("use_llm_realism", False),
            "columns": metadata.get("columns", []),
        }

        digest = hashlib.md5(
            json.dumps(stable_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]

        return f"{path}::v2::{digest}"

    # -----------------------------------
    # MAIN GENERATION ENTRY
    # -----------------------------------

    def generate(self, path, metadata):
        try:
            metadata = self._normalize_metadata(metadata)

            # 0. Validate metadata first
            meta_valid, meta_reason = validate_metadata(metadata)
            if not meta_valid:
                return {
                    "success": False,
                    "content": "",
                    "source": "error",
                    "schema": [],
                    "reason": f"Invalid metadata: {meta_reason}",
                    "llm_used": False
                }

            # 1. CHECK CACHE FIRST 
            # Note: We pass the raw 'path' and 'metadata'. 
            # Let cache.py handle the hashing logic you already wrote there.
            cached = get_file(path, metadata) 
            
            if cached:
                return {
                    "success": True,
                    "content": cached.get("content", ""),
                    "source": "cache",
                    "schema": cached.get("schema", []),
                    "reason": "Returned cached fake artifact",
                    "llm_used": cached.get("metadata", {}).get("use_llm_realism", False)
                }

            # 2. CACHE MISS -> PROCEED TO GENERATION
            schema = resolve(path, metadata)
            used_llm_realism = (
                metadata.get("realism_level", "") == "high"
                and metadata.get("use_llm_realism", False)
            )

            # 3. Generate base structured content
            content = generate_base_data(path, metadata, schema)

            # 4. Apply consistency
            content = apply_consistency(content, metadata)

            # 🔥 Prevent LLM token overflow for logs
            if metadata.get("file_type") == "log":
                content = self._truncate_logs(content)

            # 5. Apply realism enhancement
            content = apply_realism(content, metadata)

            # 🔥 Persist generated content into decoy filesystem
            try:
                real_path = resolve_path(path)

                os.makedirs(os.path.dirname(real_path), exist_ok=True)

                with open(real_path, "w", encoding="utf-8") as f:
                    f.write(content)

            except Exception as e:
                print("[WRITE ERROR]", e)

            # 6. Validate final output
            is_valid, reason = validate(content, metadata, schema)

            if not is_valid:
                fallback_content = self._fallback_content(path, metadata, schema)
                
                # Cache the fallback so we don't re-run failed generation
                set_file(path, {
                    "content": fallback_content,
                    "schema": schema,
                    "metadata": metadata
                }, metadata)

                return {
                    "success": True,
                    "content": fallback_content,
                    "source": "fallback",
                    "schema": schema,
                    "reason": f"Used fallback content: {reason}",
                    "llm_used": used_llm_realism
                }

            # 7. CACHE SUCCESSFUL GENERATION
            set_file(path, {
                "content": content,
                "schema": schema,
                "metadata": metadata
            }, metadata)

            # 8. Return final artifact
            return {
                "success": True,
                "content": content,
                "source": "generated",
                "schema": schema,
                "reason": "Generated new fake artifact successfully",
                "llm_used": used_llm_realism
            }

        except Exception as e:
            # ... error handling ...
            return {
                "success": False,
                "content": "",
                "source": "error",
                "schema": [],
                "reason": f"GenerationAgent exception: {str(e)}",
                "llm_used": False
            }

    def _truncate_logs(self, content):
        """
        Prevent oversized logs from breaking LLM calls
        """
        lines = content.split("\n")

        if len(lines) > 200:
            return "\n".join(lines[:120] + ["...truncated..."] + lines[-30:])

        return content

    # -----------------------------------
    # FALLBACK GENERATION
    # -----------------------------------

    def _fallback_content(self, path, metadata, schema):
        """
        Fallback content if main generation pipeline fails validation.

        This should be:
        - simple
        - valid
        - believable enough
        """
        file_type = metadata.get("file_type", "").lower()
        content_type = metadata.get("content_type", "").lower()
        sensitivity = metadata.get("sensitivity", "medium").lower()
        filename = os.path.basename(path)

        if file_type == "csv":
            if not schema:
                schema = ["id", "name", "status"]

            rows = [schema]

            if sensitivity == "high" and len(schema) >= 3:
                rows.append([self._fallback_value(field, idx=100, sensitivity=sensitivity) for field in schema])
                rows.append([self._fallback_value(field, idx=101, sensitivity=sensitivity) for field in schema])
            else:
                rows.append([self._fallback_value(field, idx=100, sensitivity=sensitivity) for field in schema])
                rows.append([self._fallback_value(field, idx=101, sensitivity=sensitivity) for field in schema])

            return "\n".join([",".join(row) for row in rows])

        elif file_type == "json":
            if not schema:
                schema = ["id", "name", "status"]

            records = []
            for idx in [100, 101]:
                obj = {}
                for field in schema:
                    obj[field] = self._fallback_value(field, idx=idx, sensitivity=sensitivity)
                records.append(obj)

            return json.dumps(records, indent=4)

        elif file_type == "sql":
            if not schema:
                schema = ["id", "name", "status"]

            table_name = self._infer_table_name(path, metadata)
            sql_type_map = self._infer_sql_types(schema)

            create_stmt = f"CREATE TABLE {table_name} (\n"
            create_stmt += ",\n".join(
                [f"    {col} {sql_type_map.get(col, 'VARCHAR(255)')}" for col in schema]
            )
            create_stmt += "\n);\n\n"

            rows = []
            for idx in [100, 101]:
                values = [self._sql_literal(self._fallback_value(field, idx=idx, sensitivity=sensitivity)) for field in schema]
                rows.append(f"INSERT INTO {table_name} ({', '.join(schema)}) VALUES ({', '.join(values)});")

            return create_stmt + "\n".join(rows)

        elif file_type == "env":
            if sensitivity == "high":
                return (
                    "APP_ENV=production\n"
                    "APP_NAME=internal_service\n"
                    "DB_HOST=10.10.12.8\n"
                    "DB_PORT=5432\n"
                    "DB_NAME=internal_db\n"
                    "DB_USER=svc_backup\n"
                    "DB_PASSWORD=Secure@123\n"
                    "JWT_SECRET=jwt_182739_internal\n"
                    "API_KEY=sk_live_88281928\n"
                    "AWS_ACCESS_KEY_ID=AKIA882819201928\n"
                    "SERVICE_OWNER=admin.user\n"
                    "DEBUG=false"
                )

            return (
                "APP_ENV=production\n"
                "APP_NAME=internal_service\n"
                "SERVICE_OWNER=ops.team\n"
                "DEBUG=false"
            )

        elif file_type == "txt":
            if content_type == "credentials":
                if sensitivity == "high":
                    return (
                        "admin.user : Secure@123 (admin)\n"
                        "backup.user : Backup@456 (svc_backup)\n"
                        "finance.ops : Payroll@789 (finance)"
                    )
                return "ops.user : Internal@123 (ops)\nbackup.user : Archive@456 (svc)"

            elif content_type == "logs":
                return (
                    "[2026-03-10 09:15:11] [INFO] User=admin.user Event=archive sync completed\n"
                    "[2026-03-10 09:17:43] [INFO] User=svc_backup Event=scheduled export completed"
                )

            elif content_type == "env":
                return (
                    "APP_ENV=production\n"
                    "APP_NAME=internal_service\n"
                    "DB_HOST=10.10.12.8\n"
                    "DB_PORT=5432\n"
                    "DB_NAME=internal_db\n"
                    "DB_USER=svc_backup\n"
                    "DB_PASSWORD=Secure@123\n"
                    "JWT_SECRET=jwt_182739_internal\n"
                    "API_KEY=sk_live_88281928\n"
                    "SERVICE_OWNER=admin.user\n"
                    "DEBUG=false"
                )

            else:
                return f"{filename} contains internal operational notes.\nDo not distribute outside authorized teams."

        elif file_type == "log":
            return (
                "[2026-03-10 09:15:11] [INFO] User=admin.user Event=archive sync completed\n"
                "[2026-03-10 09:17:43] [WARN] User=svc_backup Event=credential rotation pending"
            )

        return f"{filename} contains internal restricted data.\nAccess limited to authorized personnel."

    # -----------------------------------
    # FALLBACK HELPERS
    # -----------------------------------

    def _fallback_value(self, field, idx=100, sensitivity="medium"):
        field_l = field.lower()

        if "employee_id" in field_l:
            return f"EMP{idx}"
        if "user_id" in field_l:
            return f"USR{idx}"
        if field_l == "id" or field_l.endswith("_id"):
            return str(idx)

        if "full_name" in field_l or field_l == "name":
            return "Aarav Mehta" if idx % 2 == 0 else "Neha Sharma"
        if "username" in field_l:
            return "admin.user" if idx % 2 == 0 else "backup.user"
        if "email" in field_l:
            return "admin.user@internal.local" if idx % 2 == 0 else "backup.user@internal.local"
        if "department" in field_l:
            return "Finance" if sensitivity == "high" else "Operations"
        if "role" in field_l:
            return "admin" if sensitivity == "high" else "analyst"
        if "status" in field_l:
            return "active"
        if "salary" in field_l:
            return "87450"
        if "bank_account" in field_l:
            return "443298120991"
        if "tax_id" in field_l:
            return "PANQW2198K"
        if "phone" in field_l:
            return "9876543210"
        if "password_hash" in field_l:
            return "$2b$12$examplehashedvalue"
        if "password" in field_l:
            return "Secure@123"
        if "access_key" in field_l:
            return "AKIA882819201928"
        if "secret_key" in field_l or "api_secret" in field_l:
            return "sk_internal_88281928"
        if "api_key" in field_l:
            return "sk_live_88281928"
        if "db_host" in field_l:
            return "10.10.12.8"
        if "db_port" in field_l:
            return "5432"
        if "db_name" in field_l:
            return "internal_db"
        if "db_user" in field_l:
            return "svc_backup"
        if "db_password" in field_l:
            return "Secure@123"
        if "environment" in field_l:
            return "production"
        if "created_at" in field_l or "last_login" in field_l or "joining_date" in field_l or "deadline" in field_l:
            return "2026-03-10 09:15:11"
        if "is_active" in field_l or "mfa_enabled" in field_l:
            return "true"
        if "ip_address" in field_l:
            return "10.10.12.8"
        if "hostname" in field_l:
            return "srv-app-02"
        if "owner" in field_l or "owner_team" in field_l:
            return "ops.team"
        if "service_name" in field_l or "integration_name" in field_l:
            return "internal_sync_service"
        if "account_number" in field_l or "account_no" in field_l:
            return "882731920182"
        if "kyc_status" in field_l or "payment_status" in field_l:
            return "verified"
        if "message" in field_l or "subject" in field_l:
            return "Internal operational record"
        if "priority" in field_l:
            return "medium"
        if "category" in field_l:
            return "internal"
        if "price" in field_l:
            return "2499"
        if "stock" in field_l:
            return "38"
        if "location" in field_l:
            return "HQ-Storage-A"

        return "value"

    def _infer_table_name(self, path, metadata):
        filename = os.path.basename(path).lower()
        content_type = metadata.get("content_type", "").lower()

        if content_type:
            return content_type.replace(" ", "_")

        filename = filename.replace(".sql", "").replace(".dump", "").replace(".bak", "")
        filename = filename.replace("-", "_").replace(" ", "_")

        return filename if filename else "records"

    def _infer_sql_types(self, schema):
        type_map = {}

        for field in schema:
            f = field.lower()

            if f == "id" or f.endswith("_id") or "employee_id" in f or "account_id" in f:
                type_map[field] = "VARCHAR(32)"
            elif "salary" in f or "price" in f:
                type_map[field] = "DECIMAL(10,2)"
            elif "created_at" in f or "last_login" in f or "joining_date" in f or "deadline" in f or "timestamp" in f:
                type_map[field] = "TIMESTAMP"
            elif "is_active" in f or "mfa_enabled" in f:
                type_map[field] = "BOOLEAN"
            elif "db_port" in f or "stock" in f:
                type_map[field] = "INT"
            else:
                type_map[field] = "VARCHAR(255)"

        return type_map

    def _sql_literal(self, value):
        if value is None:
            return "NULL"

        value_str = str(value).strip()

        if value_str.lower() in {"true", "false"}:
            return value_str.upper()

        if value_str.replace(".", "", 1).isdigit():
            return value_str

        escaped = value_str.replace("'", "''")
        return f"'{escaped}'"


# -----------------------------------
# OPTIONAL SINGLETON-STYLE HELPER
# -----------------------------------

_generation_agent_instance = GenerationAgent()


def generate(path, metadata):
    """
    Convenience wrapper so other modules can call:
        from generation.generation_agent import generate
    """
    return _generation_agent_instance.generate(path, metadata)