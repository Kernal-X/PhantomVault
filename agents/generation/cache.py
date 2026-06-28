import os
import json
import hashlib
from datetime import datetime,timezone
from typing import Optional

CACHE_DIR = "cache/generated_files"
CACHE_VERSION = "v2"


# -----------------------------------
# HELPERS
# -----------------------------------

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _normalize_metadata(metadata:dict | None) -> dict:
    """
    Normalize metadata so cache keys are stable and comparable.
    """
    metadata = metadata or {}

    return {
        "file_type": str(metadata.get("file_type", "")).strip().lower(),
        "content_type": str(metadata.get("content_type", "")).strip().lower(),
        "size": str(metadata.get("size", "")).strip(),
        "sensitivity": str(metadata.get("sensitivity", "medium")).strip().lower(),
        "realism_level": str(metadata.get("realism_level", "medium")).strip().lower(),
        "use_llm_realism": bool(metadata.get("use_llm_realism", False)),
        "columns": metadata.get("columns", []) if isinstance(metadata.get("columns", []), list) else []
    }


def _build_cache_identity(path: str, metadata: Optional[dict] = None) -> dict:
    """
    Build stable cache identity payload.
    """
    return {
        "version": CACHE_VERSION,
        "path": path,
        "metadata": _normalize_metadata(metadata)
    }


def _path_to_cache_key(path: str, metadata: Optional[dict] = None) -> str:
    """
    Generate cache key using path + normalized metadata.
    Prevents stale mismatches when same file path is requested
    with different metadata.
    """
    identity = _build_cache_identity(path, metadata)
    raw = json.dumps(identity, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _cache_file_path(path: str, metadata: Optional[dict] = None) -> str:
    key = _path_to_cache_key(path, metadata)
    return os.path.join(CACHE_DIR, f"{key}.json")


# -----------------------------------
# MAIN CACHE API
# -----------------------------------

def set_file(path: str, data: dict, metadata: Optional[dict] = None):
    """
    Store generated fake artifact in cache.

    Expected data format:
    {
        "content": "...",
        "schema": [...],
        "metadata": {...}
    }
    """
    _ensure_cache_dir()
    cache_path = _cache_file_path(path, metadata)

    payload = {
        "content": data.get("content", ""),
        "schema": data.get("schema", []),
        "metadata": _normalize_metadata(data.get("metadata", metadata or {})),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "cache_version": CACHE_VERSION
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def get_file(path: str, metadata: Optional[dict] = None):
    """
    Retrieve cached fake artifact for a given path + metadata identity.

    Returns:
        dict or None
    """
    cache_path = _cache_file_path(path, metadata)

    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_cache():
    """
    Optional helper to wipe all cached generated files.
    """
    if not os.path.exists(CACHE_DIR):
        return

    for file_name in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def clear_cache_for_path(path: str | None):
    """
    Optional helper to remove all cache entries for a given path
    regardless of metadata variation.
    """
    if not os.path.exists(CACHE_DIR):
        return

    for file_name in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, file_name)

        if not os.path.isfile(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            if payload.get("metadata") is not None:
                # path itself isn't stored in file currently, so this only
                # works for future extension unless you store path in payload
                pass

        except Exception:
            continue