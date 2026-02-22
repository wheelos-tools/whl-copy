"""Interactive wizard pipeline for universal copy workflow."""
from __future__ import annotations

import fnmatch
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from whl_copy.core.models import CopyPlan, FilterConfig, State
from whl_copy.core.profile_store import ProfileStore
from whl_copy.core.state_store import StateStore
from whl_copy.modules.address_discovery import (
    AddressScanner,
    BosDetector,
    CustomAddressDetector,
    LocalPathDetector,
    RemoteConfigDetector,
    UsbMountDetector,
)
from whl_copy.modules.rsync_transfer import rsync_push
from whl_copy.utils.interaction import PromptAdapter, build_prompt_adapter

_TIME_PRESETS = {
    "1h": timedelta(hours=1),
    "today": None,
    "unlimited": "unlimited",
}

_SIZE_CHOICES = {
    "1K": 1024,
    "1M": 1024 * 1024,
    "1G": 1024 * 1024 * 1024,
    "不限": 0,
}


class CopyWizard:
    """Wizard-style copy orchestration for source->destination workflows."""

    def __init__(
        self,
        cfg: dict,
        state_file: str,
        profiles_file: str,
        logger,
        prompt_adapter: Optional[PromptAdapter] = None,
        output_func=print,
    ):
        self.cfg = cfg
        self.logger = logger
        self.profile_store = ProfileStore(profiles_file)
        self.store = StateStore(state_file)
        self.prompt = prompt_adapter or build_prompt_adapter()
        self.output = output_func
        self.state = self.store.load()

    def run(self) -> int:
        self._write("\n=== Universal Copy Wizard ===")
        source = self._select_source()
        destination = self._select_destination(self.state.last_dest)
        filter_config, preset_name = self._configure_filters(self.state.last_filter_type)

        plan = CopyPlan(
            source=source,
            destination=destination,
            filter_config=filter_config,
            preset_name=preset_name,
        )

        preview_files, total_bytes = self._preview_files(plan)
        self._print_preview(preview_files, total_bytes)
        self._print_estimate(total_bytes)

        if not self.prompt.confirm("Proceed with copy?", default=True):
            self._write("Copy cancelled.")
            return 1

        if self.prompt.confirm("是否保存配置?", default=True):
            default_name = preset_name or "my_profile"
            profile_name = self.prompt.text("请输入配置名称", default=default_name)
            self.profile_store.save_named_profile(profile_name, plan)
            self._write(f"配置已保存: {profile_name}")

        self._run_copy(plan, total_bytes)
        self._save_last_state(plan)
        self._write("Copy workflow completed.")
        return 0

    def run_fast(self) -> int:
        """Run immediately using last state without interaction."""
        if not self.state.last_plan:
            raise ValueError("No last plan found in state file. Run wizard once first.")

        plan = CopyPlan.from_dict(self.state.last_plan)
        preview_files, total_bytes = self._preview_files(plan)
        self._print_preview(preview_files, total_bytes)
        self._print_estimate(total_bytes)
        self._run_copy(plan, total_bytes)
        self._save_last_state(plan)
        return 0

    def run_profile(self, profile_name: str) -> int:
        """Run using a named profile and skip all wizard prompts."""
        plan = self.profile_store.get_named_profile(profile_name)
        if not plan:
            raise ValueError(f"Profile not found: {profile_name}")

        preview_files, total_bytes = self._preview_files(plan)
        self._print_preview(preview_files, total_bytes)
        self._print_estimate(total_bytes)
        self._run_copy(plan, total_bytes)
        self._save_last_state(plan)
        return 0

    def _save_last_state(self, plan: CopyPlan) -> None:
        self.state = State(
            last_source=plan.source,
            last_dest=plan.destination,
            last_filter_type=plan.filter_config.filter_type,
            last_plan=plan.to_dict(),
        )
        self.store.save(self.state)

    def _select_source(self) -> str:
        """Source is always a local working directory."""
        self._write("\n[Step] Select source working directory")
        default = self.state.last_source or os.getcwd()
        source = self.prompt.text("请输入源工作目录", default=default)
        source_path = Path(source).expanduser()
        if not source_path.exists() or not source_path.is_dir():
            raise ValueError(f"Source working directory not found: {source}")
        return str(source_path)

    def _select_destination(self, default: Optional[str]) -> str:
        """Destination is selected from discovered devices + save directory."""
        self._write("\n[Step] Select destination device")
        scanner = AddressScanner(
            detectors=[
                UsbMountDetector(),
                LocalPathDetector(self.cfg, state_hint=default),
                RemoteConfigDetector(self.cfg),
                BosDetector(self.cfg),
                CustomAddressDetector(self.cfg),
            ]
        )
        candidates = scanner.discover()
        # Build display choices containing kind and address so a single prompt
        # can represent candidates. The prompt adapter will handle interactive
        # arrow-key selection (questionary) or numeric input (fallback).
        display_choices = [f"[{c.kind}] {c.address}" for c in candidates]

        # If we have a default and it's not already among discovered addresses,
        # include it at the front as a raw entry so users can pick it quickly.
        addresses = [c.address for c in candidates]
        if default and default not in addresses:
            display_choices.insert(0, default)

        if display_choices:
            selected = self.prompt.select("选择目标设备:", choices=display_choices, default_index=0)
        else:
            selected = self.prompt.text("请输入目标设备地址", default=default or "")

        # Extract address from display string if needed
        if selected.startswith("[") and "] " in selected:
            _, addr = selected.split("] ", 1)
            selected_address = addr
        else:
            selected_address = selected

        save_dir = self.prompt.text("请输入保存目录(相对设备根)", default="copy_output")
        return self._join_destination(selected_address, save_dir)

    @staticmethod
    def _join_destination(device: str, save_dir: str) -> str:
        clean_dir = save_dir.strip().strip("/")
        if device.startswith("bos://"):
            return f"{device.rstrip('/')}/{clean_dir}" if clean_dir else device

        if "@" in device and ":" in device:
            user_host, remote_base = device.split(":", 1)
            remote_base = remote_base.rstrip("/")
            if clean_dir:
                return f"{user_host}:{remote_base}/{clean_dir}"
            return f"{user_host}:{remote_base}"

        device_path = Path(device).expanduser()
        return str(device_path / clean_dir) if clean_dir else str(device_path)

    def _configure_filters(self, default_filter_type: Optional[str]) -> Tuple[FilterConfig, Optional[str]]:
        self._write("\n[Step 3] Filter Pipeline")
        presets = self.profile_store.get_presets()
        filter_types = self.profile_store.get_filter_types()

        preset_names = [preset.get("name", "") for preset in presets if preset.get("name")]
        choices = [*preset_names, "自定义过滤..."]
        selected = self.prompt.select("选择过滤预设:", choices=choices, default_index=0)

        if selected != "自定义过滤...":
            selected_filter = self.profile_store.build_filter_from_preset(selected)
            if selected_filter:
                return selected_filter, selected

        available_filter_types = list(filter_types.keys()) or ["Custom"]
        # Allow selecting multiple target types (e.g. Logs, records, Configs).
        default_selected = [default_filter_type] if default_filter_type and default_filter_type in available_filter_types else []

        selected_types = self.prompt.multi_select(
            "选择目标类型(可多选, 用空格/数字选择):",
            choices=available_filter_types,
            default_selected=default_selected,
        )

        # Build combined patterns from chosen atomic rule types.
        combined_patterns = []
        for t in selected_types:
            combined_patterns.extend(list(filter_types.get(t) or ["*"]))

        time_range = self.prompt.select(
            "选择时间范围:",
            choices=["近1小时", "今天", "不限"],
            default_index=2,
        )
        time_map = {
            "近1小时": "1h",
            "今天": "today",
            "不限": "unlimited",
        }

        size_choice = self.prompt.select(
            "选择大小限制:",
            choices=["1K", "1M", "1G", "不限"],
            default_index=3,
        )

        return (
            FilterConfig(
                filter_type=",".join(selected_types) if selected_types else "Custom",
                patterns=combined_patterns or ["*"],
                time_range=time_map[time_range],
                min_size_bytes=_SIZE_CHOICES.get(size_choice, 0),
            ),
            None,
        )

    def _resolve_min_modified_time(self, time_range: str) -> Optional[datetime]:
        rule = _TIME_PRESETS.get(time_range, "unlimited")
        if rule == "unlimited":
            return None
        if rule is None:
            now = datetime.now()
            return datetime(now.year, now.month, now.day)
        return datetime.now() - rule

    def _preview_files(self, plan: CopyPlan) -> Tuple[List[Path], int]:
        self._write("\n[Step 3.3] 文件预览")
        if self._is_remote(plan.source) or plan.source.startswith("bos://"):
            raise ValueError("Source must be a local working directory.")

        source_path = Path(plan.source).expanduser()
        if not source_path.exists():
            self._write(f"Source not found: {plan.source}")
            return [], 0

        candidates = [source_path] if source_path.is_file() else list(source_path.rglob("*"))
        files = [item for item in candidates if item.is_file()]
        filtered: List[Path] = []
        total_bytes = 0
        min_modified_time = self._resolve_min_modified_time(plan.filter_config.time_range)

        for file_path in files:
            if not any(fnmatch.fnmatch(file_path.name, pattern) for pattern in plan.filter_config.patterns):
                continue
            stat = file_path.stat()
            if plan.filter_config.min_size_bytes and stat.st_size < plan.filter_config.min_size_bytes:
                continue
            if min_modified_time:
                mtime = datetime.fromtimestamp(stat.st_mtime)
                if mtime < min_modified_time:
                    continue
            filtered.append(file_path)
            total_bytes += stat.st_size

        return filtered[:50], total_bytes

    def _print_preview(self, files: List[Path], total_bytes: int) -> None:
        self._write(f"Matched files (showing up to 50): {len(files)}")
        for file_path in files:
            self._write(f"  - {file_path}")
        self._write(f"Estimated total size: {self._format_size(total_bytes)}")

    def _print_estimate(self, total_bytes: int) -> None:
        speed_mbps = float(self.cfg.get("wizard", {}).get("estimated_speed_mbps", 80))
        seconds = 0 if total_bytes == 0 else int(total_bytes / max(1, speed_mbps * 1024 * 1024))
        self._write(f"Estimated transfer size: {self._format_size(total_bytes)}")
        self._write(f"Estimated transfer time: {self._format_duration(seconds)}")

    def _run_copy(self, plan: CopyPlan, total_bytes: int) -> None:
        self._write("\n[Step 4] Execution")
        self._progress_bar(0)

        if plan.source.startswith("bos://") or plan.destination.startswith("bos://"):
            raise RuntimeError("BOS transfer executor is not implemented in current skeleton.")

        if self._is_remote(plan.source):
            raise RuntimeError("Source must be local. For remote machine, run push from remote side.")

        if self._is_remote(plan.destination):
            user_host, path = plan.destination.split(":", 1)
            user, host = user_host.split("@", 1)
            rsync_push(src=plan.source, dst=path, host=host, user=user)
            self._progress_bar(100)
            return

        self._copy_local_with_progress(plan.source, plan.destination, total_bytes)
        self._progress_bar(100)

    def _copy_local_with_progress(self, source: str, destination: str, total_bytes: int) -> None:
        source_path = Path(source).expanduser()
        destination_root = Path(destination).expanduser()
        destination_root.mkdir(parents=True, exist_ok=True)

        pairs: List[Tuple[Path, Path]] = []
        if source_path.is_file():
            pairs.append((source_path, destination_root / source_path.name))
        else:
            target_root = destination_root / source_path.name
            for file_path in source_path.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(source_path)
                pairs.append((file_path, target_root / rel))

        copied = 0
        for src_file, dst_file in pairs:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            with src_file.open("rb") as src_fh, dst_file.open("wb") as dst_fh:
                while True:
                    chunk = src_fh.read(1024 * 1024 * 4)
                    if not chunk:
                        break
                    dst_fh.write(chunk)
                    copied += len(chunk)
                    if total_bytes > 0:
                        self._progress_bar(int(min(99, copied * 100 / total_bytes)))

            try:
                os.utime(dst_file, (src_file.stat().st_atime, src_file.stat().st_mtime))
            except OSError:
                pass

    def _show_candidates(self, candidates: List) -> None:
        if not candidates:
            self._write("  (no candidates discovered)")
            return
        for index, candidate in enumerate(candidates, start=1):
            self._write(f"  {index}) [{candidate.kind}] {candidate.address}")

    def _progress_bar(self, percent: int, width: int = 28) -> None:
        done = int(width * max(0, min(percent, 100)) / 100)
        bar = "#" * done + "-" * (width - done)
        self._write(f"\r[{bar}] {percent:3d}%", end="" if percent < 100 else "\n")
        if percent < 100:
            sys.stdout.flush()

    def _write(self, message: str, end: str = "\n") -> None:
        self.output(message, end=end)

    @staticmethod
    def _is_remote(address: str) -> bool:
        return "@" in address and ":" in address

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size_bytes)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size_bytes} B"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds <= 0:
            return "< 1s"
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m {sec}s"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"
