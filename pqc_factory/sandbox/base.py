"""Abstract sandbox protocol shared by local and Contree backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class SandboxBackend(ABC):
    """Interface every sandbox implementation must satisfy."""

    @abstractmethod
    def create_base(self, name: str = "base") -> str:
        """Create a base sandbox and return its id."""

    @abstractmethod
    def fork(self, parent_id: str, approach_name: str = "approach") -> str:
        """Fork an isolated branch from parent; return new branch id."""

    @abstractmethod
    def write_file(self, sandbox_id: str, relative_path: str, content: str) -> None:
        ...

    @abstractmethod
    def read_file(self, sandbox_id: str, relative_path: str) -> str:
        ...

    @abstractmethod
    def list_files(self, sandbox_id: str) -> List[str]:
        ...

    @abstractmethod
    def run_command(self, sandbox_id: str, command: str) -> Tuple[int, str, str]:
        """Run command inside the sandbox. Returns (exit_code, stdout, stderr)."""

    @abstractmethod
    def cleanup(self, sandbox_id: Optional[str] = None) -> None:
        ...

    def path(self, sandbox_id: str) -> str:
        """Optional local path (local mode only). Default: sandbox_id."""
        return sandbox_id
