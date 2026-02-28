"""Interactive wizard pipeline for universal copy workflow."""
from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, Any

from whl_copy.core.domain import CopyPlan, FilterConfig, WorkflowState, StorageEndpoint, SyncJob
from whl_copy.core.preset_repository import PresetRepository
from whl_copy.core.strategy_service import FilterStrategyService
from whl_copy.core.transport_service import TransportService
from whl_copy.core.workflow_state_repository import WorkflowStateRepository
from whl_copy.core.endpoint_repository import EndpointRepository
from whl_copy.core.job_repository import SyncJobRepository
from whl_copy.discovery.registry import DeviceDiscoveryManager
from whl_copy.discovery.base import DeviceConnection
from whl_copy.utils.interaction import PromptAdapter, build_prompt_adapter

class CopyWizard:
    """Job-Centric Wizard orchestration for source<->destination workflows."""

    def __init__(
        self,
        cfg: dict,
        state_file: str,
        presets_file: str,
        logger,
        prompt_adapter: Optional[PromptAdapter] = None,
        output_func=print,
    ):
        self.cfg = cfg
        self.logger = logger
        self.preset_repository = PresetRepository(presets_file)
        self.filter_policy = FilterStrategyService(self.preset_repository)
        self.store = WorkflowStateRepository(state_file)

        base_dir = Path(state_file).parent
        self.endpoint_repo = EndpointRepository(str(base_dir / "endpoints.json"))
        self.job_repo = SyncJobRepository(str(base_dir / "sync_jobs.json"))
        self.discovery_manager = DeviceDiscoveryManager(cfg)

        self.prompt = prompt_adapter or build_prompt_adapter()
        self.output = output_func
        self.state = self.store.load()
        self.transport_service = TransportService()

    def run(self) -> int:
        self._write("=== Whl-Copy Sync Manager (Bidirectional) ===")

        jobs = self.job_repo.get_all()

        choices = []
        if jobs:
            choices.append("[Run] Execute a saved Sync Job (Skip config)")
        choices.append("[New] Create new Sync Job (Save for future)")
        choices.append("[Quit] Exit manager")

        action = self.prompt.select("Select operation:", choices=choices, default_index=0)

        if "[Quit]" in action:
            self._write("Exiting manager.")
            return 0

        if "[Run]" in action:
            return self._flow_run_job(jobs)
        elif "[New]" in action:
            return self._flow_quick_copy(save_job=True)

        return 0

    def _flow_run_job(self, jobs: List[SyncJob]) -> int:
        job_choices = [f"{j.name} ({j.source.address} -> {j.destination.address})" for j in jobs]
        job_choices.append("[Cancel]")
        sel = self.prompt.select("Select job to execute:", choices=job_choices)
        if sel == "[Cancel]":
            return 1

        selected_job = next(j for j in jobs if sel.startswith(j.name))
        self._write(f"\nExecuting Job: {selected_job.name}")
        return self._execute_job(selected_job)

    def _flow_quick_copy(self, save_job: bool = False) -> int:
        self._write("\n--- Storage Endpoint Selection ---")
        endpoints = self.endpoint_repo.get_all()
        devices = self._discover_devices()

        # Select Source
        source_ep = self._prompt_endpoint("Select Source (From)", endpoints, devices, default_local=True)
        # Select Destination
        dest_ep = self._prompt_endpoint("Select Destination (To)", endpoints, devices, default_local=False)

        # Select Filter
        filter_config, preset_name = self._select_filter_policy(self.state.last_name)

        job_id = str(uuid.uuid4())[:8]
        job_name = f"Job-{job_id}: {source_ep.backend_key} -> {dest_ep.backend_key}"

        if save_job:
            job_name = self.prompt.text("Enter a name for this Sync Job:", default=job_name)

        job = SyncJob(
            id=job_id,
            name=job_name,
            source=source_ep,
            destination=dest_ep,
            filter_config=filter_config
        )

        if save_job:
            self.endpoint_repo.save(source_ep)
            self.endpoint_repo.save(dest_ep)
            self.job_repo.save(job)
            self._write(f"Job '{job.name}' saved successfully!")

        return self._execute_job(job)

    def _discover_devices(self) -> List[DeviceConnection]:
        self._write("Discovering local and network endpoints...")
        devices = self.discovery_manager.discover()
        self._write(f"-> Found {len(devices)} active connection(s).")
        return devices

    def _prompt_endpoint(self, msg: str, endpoints: List[StorageEndpoint], devices: List[DeviceConnection], default_local: bool) -> StorageEndpoint:
        choices = []
        for ep in endpoints:
            choices.append(f"[Saved] {ep.name} ({ep.backend_key}: {ep.full_path})")

        local_devs = []
        cloud_devs = []
        remote_devs = []
        network_devs = []

        for d in devices:
            if d.kind in ("local", "removable"):
                local_devs.append(d)
            elif d.kind == "cloud":
                cloud_devs.append(d)
            elif d.kind == "remote":
                remote_devs.append(d)
            else:
                network_devs.append(d)

        ordered_devices = local_devs + cloud_devs + remote_devs

        for d in ordered_devices:
            choices.append(f"[Discovered: {d.kind}] {d.label} ({d.address})")

        for d in network_devs:
            # Simple text label, no ANSI to prevent terminal issues
            tag = "[Discovered: network (Unverified)]"
            choices.append(f"{tag} {d.label} ({d.address})")

        local_dir = os.getcwd() if default_local else "/tmp/copy_test"
        choices.append(f"[Manual] Enter a custom path")

        selected = self.prompt.select(msg, choices=choices, default_index=0)

        # Remove ANSI escape sequences for matching
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        selected_clean = ansi_escape.sub('', selected)

        if selected_clean.startswith("[Saved]"):
            for ep in endpoints:
                if ep.name in selected_clean:
                    return ep

        elif selected_clean.startswith("[Discovered"):
            target_device = None
            for d in devices:
                if d.address in selected_clean:
                    target_device = d
                    break

            if target_device is None:
                target_device = devices[0]

            if target_device.backend_key == "filesystem":
                default_path = local_dir
                save_dir = self.prompt.text(f"Enter path (absolute, or relative to {target_device.address}):", default=default_path)

                if os.path.isabs(save_dir) and not target_device.address.startswith("bos"):
                    address = save_dir
                    path_str = ""
                else:
                    address = target_device.address
                    path_str = save_dir
            else:
                default_path = ""
                save_dir = self.prompt.text(f"Enter directory path on [{target_device.address}]:", default=default_path)
                address = target_device.address
                path_str = save_dir

            return StorageEndpoint(
                id=str(uuid.uuid4())[:8],
                name=f"Endpoint-{target_device.address}",
                backend_key=target_device.backend_key,
                address=address,
                path=path_str
            )

        # Manual entry
        dest = self.prompt.text("Enter explicit full path (e.g. root@1.2.3.4:/data or /mnt/usb):", default=local_dir)
        b_key = self.prompt.select("Select storage engine:", choices=["filesystem", "rsync", "bos"], default_index=0)

        # Simplified manual parser
        address, path = dest, ""
        if ":" in dest and "@" in dest:
            address, path = dest.split(":", 1)
        elif b_key == "filesystem":
            address, path = dest, ""

        return StorageEndpoint(
            id=str(uuid.uuid4())[:8],
            name="Manual-Endpoint",
            backend_key=b_key,
            address=address,
            path=path
        )

    def _execute_job(self, job: SyncJob) -> int:
        plan = CopyPlan(
            source=job.source.full_path,
            destination=job.destination.full_path,
            backend_key=job.destination.backend_key if job.destination.backend_key != "filesystem" else job.source.backend_key,
            filter_config=job.filter_config,
            preset_name=None,
        )

        preview_files, total_bytes = self._scan_with_policy(plan)
        self._print_preview(preview_files, total_bytes, plan)
        self._print_estimate(total_bytes)

        if not self.prompt.confirm("Proceed with sync?", default=True):
            self._write("Sync cancelled.")
            return 1

        self._transport(plan)
        self._complete(plan)
        return 0

    def _select_filter_policy(self, default_name: Optional[str]) -> Tuple[FilterConfig, Optional[str]]:
        self._write("\n[Step] Select Filter Strategy")
        choices = self.filter_policy.get_preset_choices()
        selected = self.prompt.select("Select Filter Preset:", choices=choices, default_index=0)

        selected_filter, preset_name = self.filter_policy.try_build_from_preset(selected)
        if selected_filter:
            return selected_filter, preset_name

        available_profiles = self.filter_policy.get_name_choices()
        default_selected = self.filter_policy.default_selected_types(available_profiles, default_name)

        selected_types = self.prompt.multi_select("Select target types (multiple allowed):", choices=available_profiles, default_selected=default_selected)
        time_range = self.prompt.select("Select time range:", choices=["Last 1 hour", "Today", "Unlimited"], default_index=2)
        size_choice = self.prompt.select("Select max size:", choices=["1K", "1M", "1G", "Unlimited"], default_index=3)

        return self.filter_policy.build_custom_filter(selected_types, time_range, size_choice), None

    def _scan_with_policy(self, plan: CopyPlan) -> Tuple[List[Path], int]:
        self._write("\n[Scanner] Scanning source...")
        return self._preview_files(plan)

    def _preview_files(self, plan: CopyPlan) -> Tuple[List[Path], int]:
        files, total_bytes = self.transport_service.preview(plan)
        if not files and not total_bytes and not Path(plan.source).expanduser().exists() and "://" not in plan.source and "@" not in plan.source:
            self._write(f"Source not found locally: {plan.source}")
        return files, total_bytes

    def _print_preview(self, files: List[Path], total_bytes: int, plan: CopyPlan = None) -> None:
        if plan and plan.filter_config:
            self._write(f"\nFilters Active: {plan.filter_config.summary}")
        self._write(f"Matched files (showing up to 50): {len(files)}")
        for file_path in files[:50]:
            self._write(f"  - {file_path}")
        if len(files) > 50:
            self._write(f"  ... and {len(files) - 50} more")

    def _print_estimate(self, total_bytes: int) -> None:
        speed_mbps = float(self.cfg.get("wizard", {}).get("estimated_speed_mbps", 80))
        seconds = 0 if total_bytes == 0 else int(total_bytes / max(1, speed_mbps * 1024 * 1024))
        self._write(f"Estimated transfer size: {self._format_size(total_bytes)}")
        self._write(f"Estimated transfer time: {self._format_duration(seconds)}")

    def _transport(self, plan: CopyPlan) -> None:
        self._write("\n[Transport] Executing engine...")
        self._progress_bar(0)
        self.transport_service.execute(plan)
        self._progress_bar(100)

    def _complete(self, plan: CopyPlan) -> None:
        self._write("\n[Complete] Sync workflow finished successfully.")

    def _progress_bar(self, percent: int, width: int = 28) -> None:
        done = int(width * max(0, min(percent, 100)) / 100)
        bar = "#" * done + "-" * (width - done)
        self._write(f"\r[{bar}] {percent:3d}%", end="" if percent < 100 else "\n")
        if percent < 100:
            sys.stdout.flush()

    def _write(self, message: str, end: str = "\n") -> None:
        self.output(message, end=end)

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
        if seconds <= 0: return "< 1s"
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours: return f"{hours}h {minutes}m {sec}s"
        if minutes: return f"{minutes}m {sec}s"
        return f"{sec}s"
