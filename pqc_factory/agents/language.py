"""Cross-language specialist routing - prompts and detection."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

SUPPORTED = ("python", "typescript", "javascript", "go", "rust", "java")

LANGUAGE_HINTS: Dict[str, List[str]] = {
    "python": [".py", "pytest", "django", "fastapi", "flask", "poetry"],
    "typescript": [".ts", ".tsx", "tsc", "jest", "vitest", "next.js", "nestjs"],
    "javascript": [".js", ".jsx", "npm", "node", "mocha"],
    "go": ["go", ".go", "golang", "go.mod", "testify"],
    "rust": ["rust", ".rs", "cargo", "rustc"],
    "java": [".java", "maven", "gradle", "junit"],
}

IMPLEMENTER_BY_LANG: Dict[str, str] = {
    "python": "You are the Implementer Agent for Python.\nWrite idiomatic Python 3.11+ with type hints. Output THOUGHT / ACTIONS / CHANGED_FILES.",
    "typescript": "You are the Implementer Agent for TypeScript.\nWrite strict TypeScript. Output THOUGHT / ACTIONS / CHANGED_FILES.",
    "javascript": "You are the Implementer Agent for JavaScript (ES2022). Output THOUGHT / ACTIONS / CHANGED_FILES.",
    "go": "You are the Implementer Agent for Go.\nWrite idiomatic Go with error handling. Output THOUGHT / ACTIONS / CHANGED_FILES.",
    "rust": "You are the Implementer Agent for Rust.\nWrite safe idiomatic Rust. Output THOUGHT / ACTIONS / CHANGED_FILES.",
    "java": "You are the Implementer Agent for Java.\nWrite modern Java with JUnit-style tests. Output THOUGHT / ACTIONS / CHANGED_FILES.",
}

VERIFIER_BY_LANG: Dict[str, str] = {
    "python": "You are the Verifier for Python. Prefer pytest. Report PASS/FAIL clearly.",
    "typescript": "You are the Verifier for TypeScript. Prefer vitest/jest. Report PASS/FAIL clearly.",
    "javascript": "You are the Verifier for JavaScript. Prefer node test runner or jest.",
    "go": "You are the Verifier for Go. Prefer go test. Report PASS/FAIL clearly.",
    "rust": "You are the Verifier for Rust. Prefer cargo test. Report PASS/FAIL clearly.",
    "java": "You are the Verifier for Java. Prefer JUnit. Report PASS/FAIL clearly.",
}

TEST_COMMAND: Dict[str, str] = {
    "python": "python -m pytest -q --tb=no 2>&1 || true",
    "typescript": "npx vitest run --reporter=dot 2>&1 || true",
    "javascript": "npm test --silent 2>&1 || true",
    "go": "go test ./... 2>&1 || true",
    "rust": "cargo test --quiet 2>&1 || true",
    "java": "mvn -q test 2>&1 || true",
}


def detect_language(
    ticket_language: Optional[str] = None,
    text: str = "",
    filenames: Optional[List[str]] = None,
) -> str:
    if ticket_language:
        lang = ticket_language.lower().strip()
        if lang in ("ts", "tsx"):
            return "typescript"
        if lang in ("js", "jsx", "node"):
            return "javascript"
        if lang in SUPPORTED:
            return lang
    blob = (text or "").lower()
    for name, hints in LANGUAGE_HINTS.items():
        for h in hints:
            if len(h) <= 3:
                if re.search(rf"(^|\W){re.escape(h)}(\W|$)", blob):
                    return name
            elif h in blob:
                return name
    for fn in filenames or []:
        lower = fn.lower()
        if lower.endswith(".py"):
            return "python"
        if lower.endswith((".ts", ".tsx")):
            return "typescript"
        if lower.endswith((".js", ".jsx")):
            return "javascript"
        if lower.endswith(".go"):
            return "go"
        if lower.endswith(".rs"):
            return "rust"
        if lower.endswith(".java"):
            return "java"
    return "python"


def implementer_prompt(language: str) -> str:
    return IMPLEMENTER_BY_LANG.get(language, IMPLEMENTER_BY_LANG["python"])


def verifier_prompt(language: str) -> str:
    return VERIFIER_BY_LANG.get(language, VERIFIER_BY_LANG["python"])


def get_test_command(language: str) -> str:
    return TEST_COMMAND.get(language, TEST_COMMAND["python"])


def route_specialists(language: str) -> Tuple[str, str, str]:
    return implementer_prompt(language), verifier_prompt(language), get_test_command(language)
