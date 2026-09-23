"""Base class for specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pqc_factory.llm.client import LLMClient
from pqc_factory.sandbox.manager import SandboxManager


class BaseAgent(ABC):
    def __init__(
        self,
        llm: LLMClient,
        sandbox: SandboxManager,
        model: str | None = None,
    ):
        self.llm = llm
        self.sandbox = sandbox
        self.model = model

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        ...
