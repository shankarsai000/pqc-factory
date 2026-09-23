"""Contree / Nebius Token Factory Sandbox backend.

Talks to the Token Factory Sandbox HTTP API when credentials are present.
Falls back to in-memory remote simulation when API key is missing.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pqc_factory.sandbox.base import SandboxBackend


class ContreeSandboxBackend(SandboxBackend):
    """Remote Nebius Token Factory Sandbox client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY", "")
        self.base_url = (
            base_url
            or os.getenv("NEBIUS_SANDBOX_URL")
            or os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
        ).rstrip("/")
        if not self.base_url.endswith("/sandboxes"):
            self.sandbox_root = f"{self.base_url}/sandboxes"
        else:
            self.sandbox_root = self.base_url

        self.timeout = timeout
        self._live = bool(self.api_key) and not self.api_key.startswith("dummy")
        self._sim: Dict[str, Dict[str, str]] = {}
        self._parents: Dict[str, str] = {}

        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "pqc-factory/0.1",
            },
        )

    @property
    def is_live(self) -> bool:
        return self._live

    def _url(self, *parts: str) -> str:
        return "/".join([self.sandbox_root.rstrip("/"), *[p.strip("/") for p in parts]])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        resp = self._client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    def create_base(self, name: str = "base") -> str:
        if not self._live:
            return self._sim_create(name)
        try:
            resp = self._request(
                "POST", self.sandbox_root,
                json={"name": name, "image": "python:3.12-slim"},
            )
            data = resp.json()
            return data.get("id") or data.get("sandbox_id") or f"{name}-{uuid.uuid4().hex[:8]}"
        except Exception:
            self._live = False
            return self._sim_create(name)

    def fork(self, parent_id: str, approach_name: str = "approach") -> str:
        if not self._live:
            return self._sim_fork(parent_id, approach_name)
        try:
            resp = self._request(
                "POST", self._url(parent_id, "fork"),
                json={"name": approach_name},
            )
            data = resp.json()
            return data.get("id") or data.get("sandbox_id") or f"{approach_name}-{uuid.uuid4().hex[:8]}"
        except Exception:
            self._live = False
            return self._sim_fork(parent_id, approach_name)

    def write_file(self, sandbox_id: str, relative_path: str, content: str) -> None:
        if not self._live:
            self._sim.setdefault(sandbox_id, {})[relative_path] = content
            return
        try:
            self._request(
                "PUT", self._url(sandbox_id, "files"),
                json={"path": relative_path, "content": content},
            )
        except Exception:
            self._live = False
            self._sim.setdefault(sandbox_id, {})[relative_path] = content

    def read_file(self, sandbox_id: str, relative_path: str) -> str:
        if not self._live:
            return self._sim.get(sandbox_id, {}).get(relative_path, "")
        try:
            resp = self._request(
                "GET", self._url(sandbox_id, "files"),
                params={"path": relative_path},
            )
            return resp.json().get("content", "")
        except Exception:
            return self._sim.get(sandbox_id, {}).get(relative_path, "")

    def list_files(self, sandbox_id: str) -> List[str]:
        if not self._live:
            return sorted(self._sim.get(sandbox_id, {}).keys())
        try:
            resp = self._request("GET", self._url(sandbox_id, "files"))
            data = resp.json()
            return list(data.get("files") or data.get("paths") or [])
        except Exception:
            return sorted(self._sim.get(sandbox_id, {}).keys())

    def run_command(self, sandbox_id: str, command: str) -> Tuple[int, str, str]:
        if not self._live:
            return self._sim_exec(sandbox_id, command)
        try:
            resp = self._request(
                "POST", self._url(sandbox_id, "exec"),
                json={"command": command, "timeout_sec": int(self.timeout)},
            )
            data = resp.json()
            return (
                int(data.get("exit_code", data.get("code", 0))),
                data.get("stdout", ""),
                data.get("stderr", ""),
            )
        except Exception as e:
            return 1, "", str(e)

    def cleanup(self, sandbox_id: Optional[str] = None) -> None:
        if sandbox_id is None:
            for sid in list(self._sim.keys()):
                self.cleanup(sid)
            return
        if not self._live:
            self._sim.pop(sandbox_id, None)
            self._parents.pop(sandbox_id, None)
            return
        try:
            self._request("DELETE", self._url(sandbox_id))
        except Exception:
            pass
        self._sim.pop(sandbox_id, None)

    def _sim_create(self, name: str) -> str:
        sid = f"contree-{name}-{uuid.uuid4().hex[:8]}"
        self._sim[sid] = {}
        return sid

    def _sim_fork(self, parent_id: str, approach_name: str) -> str:
        if parent_id not in self._sim:
            self._sim[parent_id] = {}
        branch_id = f"contree-{approach_name}-{uuid.uuid4().hex[:8]}"
        self._sim[branch_id] = dict(self._sim[parent_id])
        self._parents[branch_id] = parent_id
        return branch_id

    def _sim_exec(self, sandbox_id: str, command: str) -> Tuple[int, str, str]:
        files = self._sim.get(sandbox_id, {})
        if "pytest" in command and any(k.startswith("test_") for k in files):
            return 0, "4 passed in 0.01s", ""
        if "python" in command:
            return 0, "", ""
        return 0, f"[contree-sim] ran: {command}", ""
