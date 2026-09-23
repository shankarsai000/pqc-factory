"""Main PQC Factory orchestration engine."""

from __future__ import annotations

import os
from typing import List, Optional

from pqc_factory.agents import (
    DocumentationAgent,
    ImplementerAgent,
    PerformanceAgent,
    SecurityAgent,
    VerifierAgent,
)
from pqc_factory.llm.client import LLMClient
from pqc_factory.models.metrics import BranchMetrics
from pqc_factory.models.pqc_report import PQCReport, PQCStatus
from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.planner import plan_approaches
from pqc_factory.orchestrator.scorer import select_winner
from pqc_factory.sandbox.logger import DecisionLogger
from pqc_factory.sandbox.manager import SandboxManager
from pqc_factory.memory.store import MemoryStore, record_from_report
from pqc_factory.hitl.gates import HITLStore


class PQCEngine:
    """End-to-end Production-Qualified Change Factory."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        sandbox: Optional[SandboxManager] = None,
        logger: Optional[DecisionLogger] = None,
        max_branches: int = 3,
        max_iterations: int = 5,
    ):
        self.llm = llm or LLMClient()
        self.sandbox = sandbox or SandboxManager(mode=os.getenv("SANDBOX_MODE", "local"))
        self.logger = logger or DecisionLogger()
        self.max_branches = max_branches
        self.max_iterations = max_iterations
        self.implementer = ImplementerAgent(self.llm, self.sandbox)
        self.verifier = VerifierAgent(self.llm, self.sandbox)
        self.security = SecurityAgent(self.llm, self.sandbox)
        self.performance = PerformanceAgent(self.llm, self.sandbox)
        self.documentation = DocumentationAgent(self.llm, self.sandbox)

    def run(self, ticket: Ticket) -> PQCReport:
        self.logger.log("run_started", {"title": ticket.title})
        approaches = plan_approaches(ticket, self.max_branches, memory=MemoryStore())
        self.logger.log("plan_created", {"approaches": approaches})
        base_id = self.sandbox.create_base("base")
        self.logger.log("base_sandbox_created", {"sandbox_id": base_id})
        all_metrics: List[BranchMetrics] = []
        for approach in approaches:
            branch_id = self.sandbox.fork(base_id, approach)
            self.logger.log("branch_forked", {"branch_id": branch_id, "approach": approach})
            metrics = self._run_branch(ticket, branch_id, approach)
            all_metrics.append(metrics)
        winner = select_winner(all_metrics)
        if not winner:
            return PQCReport(
                status=PQCStatus.FAILED,
                ticket_title=ticket.title,
                summary="No viable branch produced.",
            )
        self.logger.log("winner_selected", {"branch_id": winner.branch_id, "score": winner.overall_score})
        test_summary = f"Pass rate: {winner.test_pass_rate:.0%}"
        security_summary = f"Security score {winner.security_score:.0f}/100"
        performance_summary = f"Performance score {winner.performance_score:.0f}/100"
        changed_files = self.sandbox.list_files(winner.branch_id)
        doc = self.documentation.run(
            ticket=ticket,
            test_summary=test_summary,
            security_summary=security_summary,
            performance_summary=performance_summary,
            changed_files=changed_files,
            overall_score=winner.overall_score,
        )
        status = (
            PQCStatus.PRODUCTION_QUALIFIED
            if winner.overall_score >= 70 and winner.critical_security_issues == 0
            else PQCStatus.NEEDS_REVIEW
        )
        report = PQCReport(
            status=status,
            ticket_title=ticket.title,
            winner_branch_id=winner.branch_id,
            winner_approach=winner.approach_name,
            overall_score=winner.overall_score,
            risk_score=doc.risk_score,
            summary=doc.summary,
            changes_made=[f"Approach: {winner.approach_name}"] + changed_files[:5],
            test_summary=test_summary,
            security_summary=security_summary,
            performance_summary=performance_summary,
            rollback_plan=doc.rollback_plan,
            recommended_next_steps=["Human review", "Merge if satisfied", "Monitor after deploy"],
            changed_files=changed_files,
            branches_evaluated=len(all_metrics),
            scores={m.branch_id: m.overall_score for m in all_metrics},
            decision_log_path=str(self.logger.path),
            pr_ready=status == PQCStatus.PRODUCTION_QUALIFIED,
        )
        self.logger.log("run_finished", {"status": status.value, "score": winner.overall_score})
        try:
            mem = MemoryStore()
            record_from_report(
                mem,
                ticket_title=ticket.title,
                language=getattr(ticket, "language", "python") or "python",
                report=report,
                approaches=approaches,
            )
            gate = HITLStore().create(
                ticket_title=ticket.title,
                risk_score=report.risk_score,
                overall_score=report.overall_score,
                risk_threshold=40,
            )
            report.summary = (report.summary or "") + f"\n\nHITL run_id={gate.run_id} status={gate.status}"
        except Exception:
            pass
        return report

    def _run_branch(self, ticket: Ticket, branch_id: str, approach: str) -> BranchMetrics:
        feedback = ""
        changed_files: list[str] = []
        final_verifier = None
        i = 0
        for i in range(self.max_iterations):
            impl = self.implementer.run(
                task=ticket.summary(),
                sandbox_id=branch_id,
                feedback=feedback,
                language=getattr(ticket, "language", "python") or "python",
            )
            changed_files = impl.changed_files or changed_files
            self.logger.log("implementer_step", {"branch": branch_id, "iteration": i + 1})
            ver = self.verifier.run(
                task=ticket.summary(),
                sandbox_id=branch_id,
                changed_files=changed_files,
            )
            final_verifier = ver
            self.logger.log("verifier_step", {"branch": branch_id, "overall": ver.overall})
            if ver.overall == "PASS":
                break
            feedback = ver.feedback
        sec = self.security.run(branch_id, changed_files)
        perf = self.performance.run(branch_id, changed_files)
        pass_rate = 0.0
        if final_verifier and final_verifier.total > 0:
            pass_rate = final_verifier.passed / final_verifier.total
        elif final_verifier and final_verifier.overall == "PASS":
            pass_rate = 1.0
        metrics = BranchMetrics(
            branch_id=branch_id,
            approach_name=approach,
            test_pass_rate=pass_rate,
            coverage=final_verifier.coverage if final_verifier else 0.0,
            security_score=sec.score,
            performance_score=perf.score,
            code_quality_score=75.0 if pass_rate > 0.8 else 50.0,
            iterations_used=i + 1 if final_verifier else 0,
            critical_security_issues=sec.critical,
            high_security_issues=sec.high,
            notes=f"Approach: {approach}",
        )
        metrics.compute_overall()
        return metrics
