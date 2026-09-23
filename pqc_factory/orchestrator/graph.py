"""LangGraph wiring for the PQC Factory pipeline.

Visible graph:
  START -> plan -> fork_branches -> run_branches -> select_winner -> build_report -> END
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, TypedDict

from pqc_factory.llm.client import LLMClient
from pqc_factory.models.metrics import BranchMetrics
from pqc_factory.models.pqc_report import PQCReport, PQCStatus
from pqc_factory.models.ticket import Ticket
from pqc_factory.orchestrator.planner import plan_approaches
from pqc_factory.orchestrator.scorer import select_winner
from pqc_factory.sandbox.logger import DecisionLogger
from pqc_factory.sandbox.manager import SandboxManager


class PQCState(TypedDict, total=False):
    ticket: Ticket
    approaches: List[str]
    base_id: str
    branch_ids: List[str]
    metrics: List[BranchMetrics]
    winner: Optional[BranchMetrics]
    report: Optional[PQCReport]
    error: Optional[str]
    max_branches: int
    max_iterations: int


def build_pqc_graph(
    llm: Optional[LLMClient] = None,
    sandbox: Optional[SandboxManager] = None,
    logger: Optional[DecisionLogger] = None,
):
    llm = llm or LLMClient()
    sandbox = sandbox or SandboxManager(mode=os.getenv("SANDBOX_MODE", "local"))
    logger = logger or DecisionLogger()

    from pqc_factory.agents import (
        DocumentationAgent,
        ImplementerAgent,
        PerformanceAgent,
        SecurityAgent,
        VerifierAgent,
    )

    implementer = ImplementerAgent(llm, sandbox)
    verifier = VerifierAgent(llm, sandbox)
    security = SecurityAgent(llm, sandbox)
    performance = PerformanceAgent(llm, sandbox)
    documentation = DocumentationAgent(llm, sandbox)

    def node_plan(state: PQCState) -> Dict[str, Any]:
        approaches = plan_approaches(state["ticket"], state.get("max_branches", 3))
        logger.log("plan_created", {"approaches": approaches})
        return {"approaches": approaches}

    def node_fork(state: PQCState) -> Dict[str, Any]:
        base_id = sandbox.create_base("base")
        logger.log("base_sandbox_created", {"sandbox_id": base_id})
        branch_ids = []
        for approach in state["approaches"]:
            bid = sandbox.fork(base_id, approach)
            branch_ids.append(bid)
            logger.log("branch_forked", {"branch_id": bid, "approach": approach})
        return {"base_id": base_id, "branch_ids": branch_ids}

    def node_run_branches(state: PQCState) -> Dict[str, Any]:
        ticket = state["ticket"]
        max_iter = state.get("max_iterations", 5)
        metrics_list: List[BranchMetrics] = []
        for approach, branch_id in zip(state["approaches"], state["branch_ids"]):
            feedback, changed_files, final_ver, i = "", [], None, 0
            for i in range(max_iter):
                impl = implementer.run(task=ticket.summary(), sandbox_id=branch_id, feedback=feedback)
                changed_files = impl.changed_files or changed_files
                logger.log("implementer_step", {"branch": branch_id, "iteration": i + 1})
                ver = verifier.run(task=ticket.summary(), sandbox_id=branch_id, changed_files=changed_files)
                final_ver = ver
                logger.log("verifier_step", {"branch": branch_id, "overall": ver.overall})
                if ver.overall == "PASS":
                    break
                feedback = ver.feedback
            sec = security.run(branch_id, changed_files)
            perf = performance.run(branch_id, changed_files)
            pass_rate = 0.0
            if final_ver and final_ver.total > 0:
                pass_rate = final_ver.passed / final_ver.total
            elif final_ver and final_ver.overall == "PASS":
                pass_rate = 1.0
            m = BranchMetrics(
                branch_id=branch_id,
                approach_name=approach,
                test_pass_rate=pass_rate,
                coverage=final_ver.coverage if final_ver else 0.0,
                security_score=sec.score,
                performance_score=perf.score,
                code_quality_score=75.0 if pass_rate > 0.8 else 50.0,
                iterations_used=i + 1 if final_ver else 0,
                critical_security_issues=sec.critical,
                high_security_issues=sec.high,
                notes=f"Approach: {approach}",
            )
            m.compute_overall()
            metrics_list.append(m)
        return {"metrics": metrics_list}

    def node_select(state: PQCState) -> Dict[str, Any]:
        winner = select_winner(state.get("metrics") or [])
        if winner:
            logger.log("winner_selected", {"branch_id": winner.branch_id, "score": winner.overall_score})
        return {"winner": winner}

    def node_report(state: PQCState) -> Dict[str, Any]:
        ticket, winner = state["ticket"], state.get("winner")
        metrics = state.get("metrics") or []
        if not winner:
            return {"report": PQCReport(status=PQCStatus.FAILED, ticket_title=ticket.title, summary="No viable branch.")}
        test_summary = f"Pass rate: {winner.test_pass_rate:.0%}"
        security_summary = f"Security score {winner.security_score:.0f}/100"
        performance_summary = f"Performance score {winner.performance_score:.0f}/100"
        changed_files = sandbox.list_files(winner.branch_id)
        doc = documentation.run(
            ticket=ticket, test_summary=test_summary, security_summary=security_summary,
            performance_summary=performance_summary, changed_files=changed_files,
            overall_score=winner.overall_score,
        )
        status = (
            PQCStatus.PRODUCTION_QUALIFIED
            if winner.overall_score >= 70 and winner.critical_security_issues == 0
            else PQCStatus.NEEDS_REVIEW
        )
        report = PQCReport(
            status=status, ticket_title=ticket.title, winner_branch_id=winner.branch_id,
            winner_approach=winner.approach_name, overall_score=winner.overall_score,
            risk_score=doc.risk_score, summary=doc.summary,
            changes_made=[f"Approach: {winner.approach_name}"] + changed_files[:5],
            test_summary=test_summary, security_summary=security_summary,
            performance_summary=performance_summary, rollback_plan=doc.rollback_plan,
            recommended_next_steps=["Human review", "Merge if satisfied"],
            changed_files=changed_files, branches_evaluated=len(metrics),
            scores={m.branch_id: m.overall_score for m in metrics},
            decision_log_path=str(logger.path),
            pr_ready=status == PQCStatus.PRODUCTION_QUALIFIED,
        )
        logger.log("run_finished", {"status": status.value})
        return {"report": report}

    try:
        from langgraph.graph import END, START, StateGraph
        graph = StateGraph(PQCState)
        graph.add_node("plan", node_plan)
        graph.add_node("fork_branches", node_fork)
        graph.add_node("run_branches", node_run_branches)
        graph.add_node("select_winner", node_select)
        graph.add_node("build_report", node_report)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "fork_branches")
        graph.add_edge("fork_branches", "run_branches")
        graph.add_edge("run_branches", "select_winner")
        graph.add_edge("select_winner", "build_report")
        graph.add_edge("build_report", END)
        return graph.compile()
    except ImportError:
        class _Seq:
            def invoke(self, state: PQCState) -> PQCState:
                s: Dict[str, Any] = dict(state)
                for fn in (node_plan, node_fork, node_run_branches, node_select, node_report):
                    s.update(fn(s))  # type: ignore
                return s  # type: ignore
        return _Seq()


def run_via_graph(ticket: Ticket, max_branches: int = 2, max_iterations: int = 3, **kwargs: Any) -> PQCReport:
    g = build_pqc_graph(**kwargs)
    final = g.invoke({"ticket": ticket, "max_branches": max_branches, "max_iterations": max_iterations})
    return final.get("report") or PQCReport(status=PQCStatus.FAILED, ticket_title=ticket.title, summary="No report")


def graph_mermaid() -> str:
    return """```mermaid
flowchart LR
  START([START]) --> plan[plan]
  plan --> fork[fork_branches]
  fork --> run[run_branches]
  run --> select[select_winner]
  select --> report[build_report]
  report --> END([END])
```"""
