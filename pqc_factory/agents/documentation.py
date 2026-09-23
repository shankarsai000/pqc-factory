"""Documentation agent – produces the final PQC report."""

from __future__ import annotations

from pqc_factory.agents.base import BaseAgent
from pqc_factory.agents.prompts import DOCUMENTATION_SYSTEM
from pqc_factory.models.agent_io import DocumentationResult
from pqc_factory.models.ticket import Ticket


class DocumentationAgent(BaseAgent):
    def run(
        self,
        ticket: Ticket,
        test_summary: str,
        security_summary: str,
        performance_summary: str,
        changed_files: list[str],
        overall_score: float,
    ) -> DocumentationResult:
        if self.llm.api_key.startswith("dummy"):
            risk = 25 if overall_score > 75 else 55
            md = f"""# Production-Qualified Change Report

## 1. Summary
Successfully implemented the requested change for ticket: **{ticket.title}**.
The change was explored across multiple sandbox branches and the best candidate was selected.

## 2. Changes Made
- Implemented core logic satisfying the acceptance criteria.
- Files touched: {', '.join(changed_files) or 'solution.py'}

## 3. Test Results
{test_summary}

## 4. Security Analysis
{security_summary}

## 5. Performance Impact
{performance_summary}

## 6. Risk Score (0-100) + Justification
Risk score: **{risk}/100**.  
Based on test pass rate, security findings and performance neutrality.

## 7. Rollback Plan
Revert the pull request or restore the previous commit on the base branch.

## 8. Recommended Next Steps
- Human review of the generated code
- Merge if satisfied
- Monitor after deployment
"""
            return DocumentationResult(
                markdown_report=md,
                risk_score=risk,
                rollback_plan="Revert the PR / restore previous commit.",
                summary=f"PQC generated for '{ticket.title}' with score {overall_score:.1f}",
            )

        user_content = (
            f"Ticket:\n{ticket.summary()}\n\n"
            f"Test summary:\n{test_summary}\n\n"
            f"Security summary:\n{security_summary}\n\n"
            f"Performance summary:\n{performance_summary}\n\n"
            f"Changed files: {changed_files}\n"
            f"Overall score: {overall_score}\n"
        )
        messages = [
            {"role": "system", "content": DOCUMENTATION_SYSTEM},
            {"role": "user", "content": user_content},
        ]
        raw = self.llm.chat(messages, model=self.model, max_tokens=1500)
        return DocumentationResult(
            markdown_report=raw,
            risk_score=40,
            rollback_plan="Revert the pull request.",
            summary=raw[:300],
        )
