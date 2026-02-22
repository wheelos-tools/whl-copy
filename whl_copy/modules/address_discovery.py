"""Address discovery pipeline for source/destination selection."""
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Protocol


@dataclass(frozen=True)
class AddressCandidate:
    """A discoverable source/destination address."""

    address: str
    kind: str
    label: str
    meta: Dict[str, str] = field(default_factory=dict)


class AddressDetector(Protocol):
    """Detector protocol, implemented by all storage probes."""

    def detect(self) -> List[AddressCandidate]:
        ...


class LocalPathDetector:
    """Detect likely local addresses based on config and workspace context."""

    def __init__(self, cfg: dict, state_hint: Optional[str] = None):
        self.cfg = cfg
        self.state_hint = state_hint

    def detect(self) -> List[AddressCandidate]:
        candidates: List[AddressCandidate] = []
        # source.base_path (local source root)
        source_base = self.cfg.get("source", {}).get("base_path")
        # destination.targets may be under destination.targets or legacy top-level targets
        dest_targets = self.cfg.get("destination", {}).get("targets", [])
        legacy_targets = self.cfg.get("targets", [])
        targets = list(dict.fromkeys(dest_targets or legacy_targets))

        seen = set()

        def add_local(path_value: str, label_extra: str = ""):
            if not path_value:
                return
            path_str = str(path_value)
            if path_str in seen:
                return
            seen.add(path_str)
            label = f"Local: {path_str}" if not label_extra else f"Local ({label_extra}): {path_str}"
            candidates.append(
                AddressCandidate(address=path_str, kind="local", label=label)
            )

        # Always add declared bases/targets first
        add_local(source_base, "source")
        for t in targets:
            add_local(t, "target")

        # Add cwd/home only if they are not already present and only if helpful
        cwd = os.getcwd()
        home = str(Path.home())
        if (cwd not in seen) and (cwd == source_base or cwd in targets or self.state_hint == cwd):
            add_local(cwd, "cwd")
        if (home not in seen) and (home == source_base or home in targets or self.state_hint == home):
            add_local(home, "home")

        if self.state_hint:
            candidates.append(
                AddressCandidate(
                    address=self.state_hint,
                    kind="local",
                    label=f"Last used: {self.state_hint}",
                    meta={"priority": "high"},
                )
            )

        return candidates


class UsbMountDetector:
    """Detect mounted removable volumes on common mount roots."""

    def detect(self) -> List[AddressCandidate]:
        roots = ["/Volumes", "/media", "/mnt"]
        candidates: List[AddressCandidate] = []
        for root in roots:
            root_path = Path(root)
            if not root_path.exists() or not root_path.is_dir():
                continue
            for entry in sorted(root_path.iterdir()):
                if not entry.is_dir():
                    continue
                if platform.system() == "Darwin" and entry.name.lower() == "macintosh hd":
                    continue
                candidates.append(
                    AddressCandidate(
                        address=str(entry),
                        kind="usb",
                        label=f"USB/Mount: {entry}",
                    )
                )
        return candidates


class RemoteConfigDetector:
    """Build remote addresses from configuration blocks."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self) -> List[AddressCandidate]:
        candidates: List[AddressCandidate] = []
        # remote_candidates: list of { host, username, protocol, base_path }
        for rc in self.cfg.get("remote_candidates", []):
            host = rc.get("host")
            user = rc.get("username")
            base = rc.get("base_path", "")
            proto = rc.get("protocol")
            if host and user:
                remote = f"{user}@{host}:{base}"
                meta = {"protocol": proto} if proto else {}
                # label should be concise; keep remote address in meta for later use
                candidates.append(
                    AddressCandidate(
                        address=remote,
                        kind="remote",
                        label=f"{host}:{base or '/'}",
                        meta={**meta, "address": remote},
                    )
                )

        # Also accept explicit destination.host / destination.username entries
        dest = self.cfg.get("destination", {})
        if dest.get("host") and dest.get("username"):
            for target in dest.get("targets", [dest.get("base_path", "") or dest.get("path", "")]):
                if not target:
                    continue
                remote = f"{dest['username']}@{dest['host']}:{target}"
                candidates.append(
                    AddressCandidate(
                        address=remote,
                        kind="remote",
                        label=f"{dest['host']}:{target or '/'}",
                        meta={"address": remote},
                    )
                )

        return candidates


class BosDetector:
    """Build BOS endpoint candidates from configuration."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self) -> List[AddressCandidate]:
        candidates: List[AddressCandidate] = []
        bos_cfg = self.cfg.get("bos") or {}
        for bucket in bos_cfg.get("buckets", []):
            name = bucket.get("name")
            if not name:
                continue
            prefix = bucket.get("prefix", "")
            endpoint = f"bos://{name}/{prefix}".rstrip("/")
            candidates.append(
                AddressCandidate(
                    address=endpoint,
                    kind="bos",
                    label=f"BOS: {endpoint}",
                )
            )
        return candidates


class CustomAddressDetector:
    """Expose manually configured custom endpoints."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self) -> List[AddressCandidate]:
        candidates: List[AddressCandidate] = []
        for item in self.cfg.get("custom_endpoints", []):
            if not item:
                continue
            candidates.append(
                AddressCandidate(
                    address=str(item),
                    kind="custom",
                    label=f"Custom: {item}",
                )
            )
        return candidates


class AddressScanner:
    """Composable scanner with pluggable detector chain."""

    def __init__(self, detectors: List[AddressDetector]):
        self.detectors = detectors

    def discover(self) -> List[AddressCandidate]:
        merged: Dict[str, AddressCandidate] = {}
        for detector in self.detectors:
            for candidate in detector.detect():
                merged[candidate.address] = candidate

        candidates = list(merged.values())

        # Priority ordering: last-used (meta.priority=='high'), usb, custom, local (targets), remote, bos
        kind_order = {"last": 0, "usb": 1, "custom": 2, "local": 3, "remote": 4, "bos": 5}

        def sort_key(cand: AddressCandidate):
            # highest priority if explicitly set
            if cand.meta.get("priority") == "high":
                return (0, 0, cand.label.lower())
            kind_rank = kind_order.get(cand.kind, 99)
            return (1, kind_rank, cand.label.lower())

        return sorted(candidates, key=sort_key)
