"""
Reusable schema and validation constants for Strategy Agent output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

STRATEGY_TYPES = frozenset({"targeted", "hybrid", "exploratory"})
SPREAD_STRATEGIES = frozenset(
    {
        "single_directory", # one folder
        "clustered_directories",    # few related folders
        "distributed_shares",   # across system/network
        "hilbert_hostname_mirror",  # fake isolated network
        "network_island",   # advanced structured mapping
    }
)
DEPTH_VALUES = frozenset(
    {
        "minimal_deception",    # very light
        "moderate", # balanced
        "data_heavy",   # lots of files
        "high_deception",   # deepfake system
        "network_expansion",    # fake network
    }
)
INTERACTION_LEVELS = frozenset(
    {"passive_sniffer", "low_interaction", "medium_interaction", "active_engagement"}
)
ACCESS_CONTROL_MODES = frozenset(
    {
        "deny_non_privileged_to_production",
        "read_only_decoys_for_clients",
        "isolate_decoys_in_sandbox_accounts",
        "iacl_lockdown_source_trees",
    }
)

TOP_LEVEL_STRING_KEYS = (
    "strategy_type",
    "intent",
    "attack_stage",
)

TOP_LEVEL_FLOAT_KEYS = ("confidence",)

REQUIRED_TOP_KEYS = frozenset(
    {
        "strategy_type",
        "intent",
        "attack_stage",
        "confidence",
        "execution_plan",
        "placement_plan",
        "data_protection",
        "engagement_policy",
        "monitoring_plan",
        "generation_constraints",
        "reasoning_summary",
    }
)

EXECUTION_LIST_KEYS = (
    "files_to_create",
    "credentials_to_create",
    "system_artifacts",
    "network_artifacts",
)

PLACEMENT_KEYS = frozenset({"directories_to_use", "spread_strategy", "depth"})
DATA_PROTECTION_KEYS = frozenset(
    {"real_files_lock", "redirect_access_to_decoy", "backup_original_data", "access_control"}
)
ENGAGEMENT_KEYS = frozenset(
    {"interaction_level", "allow_attacker_progress", "delay_responses"}
)
MONITORING_KEYS = frozenset({"track_events", "alert_on"})
GENERATION_CONSTRAINT_KEYS = frozenset(
    {"max_files", "max_credentials", "ensure_believability"}
)


class ExecutionPlanDict(TypedDict, total=False):
    files_to_create: List[Dict[str, Any]]
    credentials_to_create: List[Dict[str, Any]]
    system_artifacts: List[Dict[str, Any]]
    network_artifacts: List[Dict[str, Any]]


class StrategyPayload(TypedDict, total=False):
    strategy_type: str
    intent: str
    attack_stage: str
    confidence: float
    execution_plan: ExecutionPlanDict
    placement_plan: Dict[str, Any]
    data_protection: Dict[str, Any]
    engagement_policy: Dict[str, Any]
    monitoring_plan: Dict[str, Any]
    generation_constraints: Dict[str, Any]
    reasoning_summary: List[str]


def confidence_to_strategy_type(confidence: float) -> Literal["targeted", "hybrid", "exploratory"]:
    if confidence >= 0.75:
        return "targeted"
    if confidence >= 0.4:
        return "hybrid"
    return "exploratory"


def stage_to_depth(attack_stage: str) -> str:
    m = {
        "initial_access": "minimal_deception",
        "credential_access": "moderate",
        "execution": "moderate",
        "collection": "data_heavy",
        "exfiltration": "high_deception",
        "lateral_movement": "network_expansion",
        "persistence": "moderate",
        "unknown": "moderate",
    }
    return m.get(attack_stage, "moderate")


def intent_to_artifact_focus(intent: str) -> List[str]:
    mapping: Dict[str, List[str]] = {
        "data_exfiltration": ["sensitive_files", "archives", "database_dumps"],
        "credential_bruteforce": ["password_vaults", "cached_creds_files", "rdp_credential_stores"],
        "privilege_escalation": ["sudoers_snippets", "scheduled_tasks", "service_binaries"],
        "reconnaissance": ["system_inventory", "share_listings", "user_directories"],
        "lateral_movement": ["internal_endpoints", "smb_paths", "winrm_hosts", "ssh_staging"],
        "persistence": ["run_keys", "startup_folder", "cron_systemd_unit_dropins"],
        "insider_threat": ["internal_sensitive_docs", "hr_exports", "merger_plans"],
        "benign_activity": [],
        "unknown": ["generic_honeypot_documents"],
    }
    return mapping.get(intent, mapping["unknown"])


def compute_generation_limits(strategy_type: str, depth: str) -> Tuple[int, int]:
    base_files = {"minimal_deception": 3, "moderate": 6, "data_heavy": 12, "high_deception": 16, "network_expansion": 8}
    base_creds = {"minimal_deception": 2, "moderate": 4, "data_heavy": 6, "high_deception": 5, "network_expansion": 5}
    f = base_files.get(depth, 6)
    c = base_creds.get(depth, 4)
    if strategy_type == "targeted":
        f = min(f + 2, 24)
        c = min(c + 2, 12)
    elif strategy_type == "exploratory":
        f = max(2, f - 2)
        c = max(1, c - 1)
    return f, c
