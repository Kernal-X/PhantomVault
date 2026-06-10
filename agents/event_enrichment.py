"""
Populate ML feature fields on monitor events using psutil and lightweight history.

Called from SystemAgent for every event after collection; does not change detection logic.
"""

from __future__ import annotations

import ipaddress
import math
import os
import statistics
import time
from collections import Counter, defaultdict, deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

import psutil

# --- Trusted ranges for is_known_ip (same idea as ScoringDetector) ---
_TRUSTED_IP_NETWORKS: Tuple[Any, ...] = (
    ipaddress.ip_network("8.8.8.0/24"),
    ipaddress.ip_network("8.34.208.0/20"),
    ipaddress.ip_network("8.35.192.0/20"),
    ipaddress.ip_network("1.1.1.0/24"),
    ipaddress.ip_network("1.0.0.0/24"),
    ipaddress.ip_network("13.107.0.0/16"),
    ipaddress.ip_network("40.64.0.0/10"),
    ipaddress.ip_network("52.95.0.0/16"),
)

_KNOWN_EXE_ROOTS: Tuple[str, ...] = tuple(
    sorted({x for x in (
        os.environ.get("SystemRoot", r"C:\Windows").lower(),
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "system32").lower(),
        os.environ.get("ProgramFiles", r"C:\Program Files").lower(),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)").lower(),
    ) if x})
)


def _norm_path(p: str) -> str:
    try:
        return os.path.normcase(os.path.abspath(p))
    except Exception:
        return os.path.normcase(p)


def _port_risk(port: int) -> int:
    if port in (80, 443, 53, 123, 587, 993):
        return 0
    if port in (22, 135, 139, 445, 3389, 5985, 5986):
        return 2
    if 0 < port < 1024:
        return 2
    if port == 0:
        return 0
    return 1


def _is_known_ip_value(ip_str: str) -> int:
    if not ip_str:
        return 0
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return int(any(ip in net for net in _TRUSTED_IP_NETWORKS))
    except ValueError:
        return 0


def _is_private_ip_value(ip_str: str) -> int:
    if not ip_str or not str(ip_str).strip():
        return 0
    try:
        ip = ipaddress.ip_address(str(ip_str).strip())
        return int(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        s = str(ip_str).strip().lower()
        return int(s.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "127.")))


class EventEnricher:
    """Stateful enricher: rolling windows for frequencies and z-scores."""

    def __init__(self) -> None:
        self._window_s = 300.0
        self._file_window_s = 60.0
        self._net_window_s = 60.0
        self._uniq_ip_window_s = 300.0

        # (ts, process_name, cpu, memory_mb)
        self._proc_samples: Deque[Tuple[float, str, float, float]] = deque()
        # (ts, process_name) for frequency
        self._proc_names: Deque[Tuple[float, str]] = deque()
        # (ts, parent, child) lowercased
        self._parent_child: Deque[Tuple[float, str, str]] = deque()
        self._pair_counts: Counter[Tuple[str, str]] = Counter()
        # (ts, remote_ip, remote_port, pid)
        self._net_events: Deque[Tuple[float, str, int, int]] = deque()
        # (ts, pid, remote_ip)
        self._net_by_pid: Deque[Tuple[float, int, str]] = deque()
        # (ts, normalized file path)
        self._file_events: Deque[Tuple[float, str]] = deque()
        self._file_path_counts: Counter[str] = Counter()

    def _trim(self, now: float) -> None:
        cut = now - self._window_s
        while self._proc_samples and self._proc_samples[0][0] < cut:
            self._proc_samples.popleft()
        while self._proc_names and self._proc_names[0][0] < cut:
            self._proc_names.popleft()
        while self._parent_child and self._parent_child[0][0] < cut:
            ts, p, c = self._parent_child.popleft()
            key = (p, c)
            self._pair_counts[key] -= 1
            if self._pair_counts[key] <= 0:
                del self._pair_counts[key]
        cut_f = now - self._file_window_s
        while self._file_events and self._file_events[0][0] < cut_f:
            self._file_events.popleft()
        cut_n = now - self._net_window_s
        while self._net_events and self._net_events[0][0] < cut_n:
            self._net_events.popleft()
        cut_u = now - self._uniq_ip_window_s
        while self._net_by_pid and self._net_by_pid[0][0] < cut_u:
            self._net_by_pid.popleft()

    def _zscore(self, history: List[float], x: float) -> float:
        if len(history) < 3:
            return 0.0
        try:
            m = statistics.mean(history)
            s = statistics.pstdev(history)
        except statistics.StatisticsError:
            return 0.0
        if s < 1e-9:
            return 0.0
        return (x - m) / s

    def _cmd_entropy(self, cmdline: str) -> float:
        if not cmdline:
            return 0.0
        counts = Counter(cmdline)
        total = float(len(cmdline))
        entropy = 0.0
        for count in counts.values():
            probability = count / total
            entropy -= probability * math.log2(probability)
        return entropy

    def _is_known_binary_path(self, exe: Optional[str]) -> int:
        if not exe:
            return 0
        low = exe.lower()
        return int(any(low.startswith(root) for root in _KNOWN_EXE_ROOTS if root))

    def _snapshot_process_metrics(self, pid: int) -> Tuple[Optional[str], Optional[str], float, float, Optional[str]]:
        """Returns process_name, parent_process, cpu_percent, memory_mb, exe_path."""
        try:
            proc = psutil.Process(pid)
            cpu = float(proc.cpu_percent(interval=None))
            mem_mb = float(proc.memory_info().rss) / (1024 * 1024)
            name = proc.name() or "unknown"
            parent_name: Optional[str] = None
            try:
                p = proc.parent()
                if p:
                    pn = p.name()
                    if pn and pn.lower() != name.lower():
                        parent_name = pn
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            exe: Optional[str] = None
            try:
                exe = proc.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                exe = None
            return name, parent_name, cpu, mem_mb, exe
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None, None, 0.0, 0.0, None

    def _guess_file_owner(self, file_path: str, max_procs: int = 150) -> Tuple[Optional[int], Optional[str], float, float]:
        target = _norm_path(file_path)
        n = 0
        for proc in psutil.process_iter(["pid", "name"]):
            if n >= max_procs:
                break
            n += 1
            try:
                for f in proc.open_files() or []:
                    if _norm_path(f.path) == target:
                        pid = proc.pid
                        metrics = self._snapshot_process_metrics(pid)
                        pname, _, cpu, mem, _ = metrics
                        return pid, pname or proc.name(), cpu, mem
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None, None, 0.0, 0.0

    def enrich(self, event: Dict[str, Any]) -> None:
        et = event.get("type")
        if et in ("process_start", "process_sample"):
            self._enrich_process(event)
        elif et == "network_connection":
            self._enrich_network(event)
        elif et == "file_access":
            self._enrich_file(event)

    def _enrich_process(self, event: Dict[str, Any]) -> None:
        data = event.setdefault("data", {})
        now = float(event.get("timestamp") or time.time())
        self._trim(now)

        pid = int(data.get("pid") or 0)
        pname = str(data.get("process_name") or "unknown").strip() or "unknown"
        cpu = float(data.get("cpu_percent") or 0.0)
        mem = float(data.get("memory_mb") or 0.0)
        cmdline = str(data.get("cmdline") or "")

        if pid and not data.get("exe_path"):
            try:
                data["exe_path"] = psutil.Process(pid).exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                data["exe_path"] = None

        parent = data.get("parent_process")
        pl = str(parent).lower().strip() if parent else ""
        cl = pname.lower()
        if pl and cl:
            self._parent_child.append((now, pl, cl))
            self._pair_counts[(pl, cl)] += 1

        self._proc_samples.append((now, pname, cpu, mem))
        self._proc_names.append((now, pname))

        # history for z-score: same process name
        cpus = [c for t, n, c, _ in self._proc_samples if n == pname]
        mems = [m for t, n, _, m in self._proc_samples if n == pname]

        data["cpu_zscore"] = round(self._zscore(cpus, cpu), 6)
        data["memory_zscore"] = round(self._zscore(mems, mem), 6)

        if pl:
            cnt = self._pair_counts.get((pl, cl), 0)
            data["parent_child_rarity"] = round(1.0 / (1.0 + float(cnt)), 6)
        else:
            data["parent_child_rarity"] = 0.0

        data["process_freq_5min"] = sum(1 for t, n in self._proc_names if n.lower() == pname.lower())

        exe = data.get("exe_path")
        data["is_known_binary"] = self._is_known_binary_path(exe if isinstance(exe, str) else None)
        data["cmd_entropy"] = round(self._cmd_entropy(cmdline), 6)

        # Network-related fields N/A
        data.setdefault("connection_freq_1min", 0)
        data.setdefault("unique_ip_5min", 0)
        data.setdefault("port_risk", 0)
        data.setdefault("is_known_ip", 0)
        if "remote_ip" not in data:
            data["remote_ip"] = None
        if "remote_port" not in data:
            data["remote_port"] = 0

        data.setdefault("file_freq_1min", 0)
        data.setdefault("file_rarity", 0.0)

    def _enrich_network(self, event: Dict[str, Any]) -> None:
        data = event.setdefault("data", {})
        now = float(event.get("timestamp") or time.time())
        self._trim(now)

        pid = int(data.get("pid") or 0)
        rip = str(data.get("remote_ip") or "").strip()
        rport = int(data.get("remote_port") or 0)

        if pid:
            metrics = self._snapshot_process_metrics(pid)
            pname, parent, cpu, mem, exe = metrics
            if pname:
                data["process_name"] = pname
            if parent:
                data["parent_process"] = parent
            data["cpu_percent"] = round(cpu, 4)
            data["memory_mb"] = round(mem, 4)
            if exe:
                data["exe_path"] = exe
            data["is_known_binary"] = self._is_known_binary_path(exe)

            # process history for z-scores (network snapshot as extra sample)
            pn = str(data.get("process_name") or "unknown")
            self._proc_samples.append((now, pn, cpu, mem))
            self._proc_names.append((now, pn))
            cpus = [c for t, n, c, _ in self._proc_samples if n == pn]
            mems = [m for t, n, _, m in self._proc_samples if n == pn]
            data["cpu_zscore"] = round(self._zscore(cpus, cpu), 6)
            data["memory_zscore"] = round(self._zscore(mems, mem), 6)

            pl = str(data.get("parent_process") or "").lower().strip() if data.get("parent_process") else ""
            cl = pn.lower()
            if pl and cl:
                self._parent_child.append((now, pl, cl))
                self._pair_counts[(pl, cl)] += 1
                cnt = self._pair_counts.get((pl, cl), 0)
                data["parent_child_rarity"] = round(1.0 / (1.0 + float(cnt)), 6)
            else:
                data["parent_child_rarity"] = 0.0

            data["process_freq_5min"] = sum(1 for t, n in self._proc_names if n.lower() == pn.lower())
        else:
            data.setdefault("cpu_zscore", 0.0)
            data.setdefault("memory_zscore", 0.0)
            data.setdefault("parent_child_rarity", 0.0)
            data.setdefault("process_freq_5min", 0)
            data.setdefault("is_known_binary", 0)
        data.setdefault("cmd_entropy", 0.0)

        if rip:
            self._net_events.append((now, rip, rport, pid))
            if pid:
                self._net_by_pid.append((now, pid, rip))

        data["connection_freq_1min"] = sum(
            1 for t, ip, p, pd in self._net_events if ip == rip and p == rport and pd == pid
        )
        if pid:
            ips: Set[str] = {ip for t, pd, ip in self._net_by_pid if pd == pid}
            data["unique_ip_5min"] = len(ips)
        else:
            data["unique_ip_5min"] = 0

        data["port_risk"] = _port_risk(rport)
        data["is_private_ip"] = _is_private_ip_value(rip)
        data["is_known_ip"] = _is_known_ip_value(rip)

        data.setdefault("file_freq_1min", 0)
        data.setdefault("file_rarity", 0.0)

    def _enrich_file(self, event: Dict[str, Any]) -> None:
        data = event.setdefault("data", {})
        now = float(event.get("timestamp") or time.time())
        self._trim(now)

        fp = data.get("file_path")
        path_str = str(fp) if fp is not None else ""
        norm = _norm_path(path_str) if path_str else ""

        if norm:
            self._file_events.append((now, norm))
            self._file_path_counts[norm] += 1

        data["file_freq_1min"] = sum(1 for t, p in self._file_events if p == norm) if norm else 0
        total = sum(self._file_path_counts.values()) or 1
        cnt = self._file_path_counts.get(norm, 0) if norm else 0
        data["file_rarity"] = round(1.0 - (cnt / float(total)), 6) if norm else 0.0

        if norm and not data.get("pid"):
            gid, gname, gcpu, gmem = self._guess_file_owner(path_str)
            if gid is not None:
                data["pid"] = gid
            if gname:
                data["process_name"] = gname
            data["cpu_percent"] = round(gcpu, 4)
            data["memory_mb"] = round(gmem, 4)

        # Defaults for process-centric metrics
        data.setdefault("cpu_zscore", 0.0)
        data.setdefault("memory_zscore", 0.0)
        data.setdefault("parent_child_rarity", 0.0)
        data.setdefault("process_freq_5min", 0)
        exe = data.get("exe_path")
        if exe is None and data.get("pid"):
            try:
                exe = psutil.Process(int(data["pid"])).exe()
                data["exe_path"] = exe
            except Exception:
                pass
        data["is_known_binary"] = self._is_known_binary_path(data.get("exe_path") if isinstance(data.get("exe_path"), str) else None)
        data.setdefault("cmd_entropy", 0.0)

        data.setdefault("connection_freq_1min", 0)
        data.setdefault("unique_ip_5min", 0)
        data.setdefault("port_risk", 0)
        data.setdefault("is_known_ip", 0)
        data.setdefault("remote_ip", None)
        data.setdefault("remote_port", 0)
        data.setdefault("is_private_ip", 0)
