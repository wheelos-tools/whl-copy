"""Rsync remote SSH storage backend."""

from __future__ import annotations

import subprocess
from typing import List

from whl_copy.storage.operations import rsync_push, rsync_pull, _build_ssh_cmd
from whl_copy.core.destination_service import DestinationAddressResolver
from whl_copy.core.domain import CopyPlan


class RsyncStorage:
    def __init__(self, address_resolver: DestinationAddressResolver | None = None):
        self.address_resolver = address_resolver or DestinationAddressResolver()

    def connect(self) -> bool:
        # We could run a fast ssh command to verify connection
        # ssh -o BatchMode=yes -o ConnectTimeout=5 user@host echo OK
        return True

    def _get_remote_path(self, plan: CopyPlan) -> str:
        if self.address_resolver.is_remote(plan.destination):
            return plan.destination
        return plan.source

    def exists(self, path: str) -> bool:
        if not self.address_resolver.is_remote(path):
            import os
            return os.path.exists(path)
        try:
            user, host, remote_path = self.address_resolver.split_remote_destination(path)
            ssh_cmd = _build_ssh_cmd(None)
            cmd = f"{ssh_cmd} {user}@{host} test -e '{remote_path}'"
            return subprocess.run(cmd, shell=True).returncode == 0
        except Exception:
            return False

    def mkdir(self, path: str) -> None:
        if not self.address_resolver.is_remote(path):
            import os
            os.makedirs(path, exist_ok=True)
            return
        user, host, remote_path = self.address_resolver.split_remote_destination(path)
        ssh_cmd = _build_ssh_cmd(None)
        cmd = f"{ssh_cmd} {user}@{host} mkdir -p '{remote_path}'"
        subprocess.run(cmd, shell=True, check=True)

    def get_free_space(self, path: str) -> int:
        if not self.address_resolver.is_remote(path):
            import shutil
            try:
                return shutil.disk_usage(path).free
            except:
                return -1
        try:
            user, host, remote_path = self.address_resolver.split_remote_destination(path)
            ssh_cmd = _build_ssh_cmd(None)
            cmd = f"{ssh_cmd} {user}@{host} df -k '{remote_path}' | tail -1 | awk '{{print $4}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return int(result.stdout.strip()) * 1024
        except Exception:
            return -1

    def list_dirs(self, path: str) -> List[str]:
        if not self.address_resolver.is_remote(path):
            import os
            try:
                return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            except:
                return []
        try:
            user, host, remote_path = self.address_resolver.split_remote_destination(path)
            ssh_cmd = _build_ssh_cmd(None)
            cmd = f"{ssh_cmd} {user}@{host} find '{remote_path}' -maxdepth 1 -mindepth 1 -type d -exec basename {{}} \;"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            return []

    def transfer(self, plan: CopyPlan, resume: bool = True, verify: bool = False) -> None:
        extra_args = ["--checksum"] if verify else []

        is_push = self.address_resolver.is_remote(plan.destination)
        is_pull = self.address_resolver.is_remote(plan.source)

        if is_push:
            user, host, remote_path = self.address_resolver.split_remote_destination(plan.destination)
            rsync_push(src=plan.source, dst=remote_path, host=host, user=user, resume=resume, extra_args=extra_args)
        elif is_pull:
            user, host, remote_path = self.address_resolver.split_remote_destination(plan.source)
            rsync_pull(src=remote_path, dst=plan.destination, host=host, user=user, resume=resume, extra_args=extra_args)
        else:
            raise NotImplementedError("Local to Local should use LocalStorage plugin.")
