"""Sandbox manager facade - picks local or Contree backend from env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple, Union

from pqc_factory.sandbox.base import SandboxBackend
from pqc_factory.sandbox.contree import ContreeSandboxBackend
from pqc_factory.sandbox.local import LocalSandboxBackend


def create_sandbox_backend(
    mode: Optional[str] = None,
    root: Optional[str | Path] = None,
) -> SandboxBackend:
    mode = (mode or os.getenv("SANDBOX_MODE", "local")).lower().strip()
    if mode in ("contree", "nebius", "tokenfactory", "remote"):
        return ContreeSandboxBackend()
    return LocalSandboxBackend(root=root)


class SandboxManager:
    def __init__(
        self,
        root: Optional[str | Path] = None,
        mode: str = "local",
        backend: Optional[SandboxBackend] = None,
    ):
        self.mode = mode
        self._backend: SandboxBackend = backend or create_sandbox_backend(mode=mode, root=root)

    @property
    def backend_name(self) -> str:
        return type(self._backend).__name__

    @property
    def is_contree(self) -> bool:
        return isinstance(self._backend, ContreeSandboxBackend)

    def create_base(self, name: str = "base") -> str:
        return self._backend.create_base(name)

    def fork(self, parent_id: str, approach_name: str = "approach") -> str:
        return self._backend.fork(parent_id, approach_name)

    def path(self, sandbox_id: str) -> Union[Path, str]:
        return self._backend.path(sandbox_id)

    def write_file(self, sandbox_id: str, relative_path: str, content: str) -> None:
        self._backend.write_file(sandbox_id, relative_path, content)

    def read_file(self, sandbox_id: str, relative_path: str) -> str:
        return self._backend.read_file(sandbox_id, relative_path)

    def list_files(self, sandbox_id: str) -> List[str]:
        return self._backend.list_files(sandbox_id)

    def run_command(self, sandbox_id: str, command: str) -> Tuple[int, str, str]:
        return self._backend.run_command(sandbox_id, command)

    def cleanup(self, sandbox_id: Optional[str] = None) -> None:
        self._backend.cleanup(sandbox_id)
