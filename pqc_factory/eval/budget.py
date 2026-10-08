"""Token/cost budget — stop exploration before spend explodes."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Budget:
    max_tokens: int = 200_000
    max_branches: int = 3
    max_iterations: int = 5
    used_tokens: int = 0

    @classmethod
    def from_env(cls) -> "Budget":
        return cls(
            max_tokens=int(os.getenv("PQC_MAX_TOKENS", "200000")),
            max_branches=int(os.getenv("MAX_BRANCHES", "3")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "5")),
        )

    def record(self, tokens: int) -> None:
        self.used_tokens += max(0, tokens)

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    def exhausted(self) -> bool:
        return self.used_tokens >= self.max_tokens

    def status(self) -> str:
        return f"tokens {self.used_tokens}/{self.max_tokens} remaining={self.remaining()}"
