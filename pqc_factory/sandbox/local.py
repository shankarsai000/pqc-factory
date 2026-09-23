"""Local filesystem sandbox backend (dev / offline / tests)."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pqc_factory.sandbox.base import SandboxBackend


class LocalSandboxBackend(SandboxBackend):
    def __init__(self, root: Optional[str | Path] = None):
        self.root = Path(root or "./.pqc_sandboxes").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._branches: Dict[str, Path] = {}

    def create_base(self, name: str = "base") -> str:
        sandbox_id = f"{name}-{uuid.uuid4().hex[:8]}"
        path = self.root / sandbox_id
        path.mkdir(parents=True, exist_ok=True)
        self._branches[sandbox_id] = path
        return sandbox_id

    def fork(self, parent_id: str, approach_name: str = "approach") -> str:
        if parent_id not in self._branches:
            raise ValueError(f"Unknown parent sandbox: {parent_id}")
        parent_path = self._branches[parent_id]
        branch_id = f"{approach_name}-{uuid.uuid4().hex[:8]}"
        branch_path = self.root / branch_id
        if parent_path.exists():
            shutil.copytree(parent_path, branch_path, dirs_exist_ok=True)
        else:
            branch_path.mkdir(parents=True, exist_ok=True)
        self._branches[branch_id] = branch_path
        return branch_id

    def path(self, sandbox_id: str) -> Path:
        if sandbox_id not in self._branches:
            raise ValueError(f"Unknown sandbox: {sandbox_id}")
        return self._branches[sandbox_id]

    def write_file(self, sandbox_id: str, relative_path: str, content: str) -> None:
        target = self.path(sandbox_id) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read_file(self, sandbox_id: str, relative_path: str) -> str:
        target = self.path(sandbox_id) / relative_path
        if not target.exists():
            return ""
        return target.read_text(encoding="utf-8")

    def list_files(self, sandbox_id: str) -> List[str]:
        root = self.path(sandbox_id)
        out: List[str] = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(root))
            if "__pycache__" in rel or rel.endswith(".pyc"):
                continue
            out.append(rel)
        return out

    def run_command(self, sandbox_id: str, command: str) -> Tuple[int, str, str]:
        cwd = self.path(sandbox_id)
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60,
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def cleanup(self, sandbox_id: Optional[str] = None) -> None:
        if sandbox_id:
            path = self._branches.pop(sandbox_id, None)
            if path and path.exists():
                shutil.rmtree(path, ignore_errors=True)
        else:
            for sid in list(self._branches):
                self.cleanup(sid)
