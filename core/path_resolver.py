import os

DECOY_ROOT = os.path.abspath("./decoy_env")


def normalize_path(path: str) -> str:
    r"""
    Convert ANY incoming path (Windows/Linux) → virtual path
    Example:
        D:\shared\logs\a.log → /shared/logs/a.log
    """
    if not path:
        return None

    path = str(path).replace("\\", "/")

    # remove drive letter (C:, D:)
    if ":" in path:
        path = path.split(":", 1)[1]

    # Canonicalize to known virtual roots if present anywhere in the path.
    # This keeps registry keys stable even when absolute OS paths are observed.
    parts = [p for p in path.split("/") if p]
    lowered = [p.lower() for p in parts]
    for anchor in ("shared", "demo_shared"):
        if anchor in lowered:
            idx = lowered.index(anchor)
            parts = parts[idx:]
            break

    return "/" + "/".join(parts) if parts else "/"


def resolve_path(path: str) -> str:
    """
    Convert virtual path → decoy filesystem path
    """
    if not path:
        return None

    path = normalize_path(path)

    # remove leading /
    path = path[1:]

    real_path = os.path.join(DECOY_ROOT, path)

    # safety check
    if not real_path.startswith(DECOY_ROOT):
        raise Exception("Unsafe path detected")

    return real_path