# Production-Qualified Change (PQC) Factory

**Multi-agent system that turns a high-level ticket into a Production-Qualified Change**  
using **Nebius Token Factory Sandboxes** + **NVIDIA Nemotron** models.

> Built for the **Nebius x NVIDIA Global AI Hackathon** - *Coding & Agentic Engineering Track*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Problem

Coding agents today stop at "code that compiles."  
The real bottleneck is turning agent-generated code into **production-qualified changes**: tested, scanned, risk-scored, and ready for human review.

## Solution

PQC Factory is an orchestrated multi-agent pipeline that:

1. Accepts a natural-language ticket  
2. Plans 2-3 alternative approaches  
3. Forks isolated **Token Factory Sandbox** branches  
4. Runs **Implementer <-> Verifier** loops on each branch  
5. Runs **Security** and **Performance** gates  
6. Scores every branch and selects the winner  
7. Emits a full **Production-Qualified Change report** (risk score, rollback plan, PR-ready package)

---

## Architecture

```
Ticket
  |
Orchestrator (Nemotron-Ultra planning)
  |
+--------------+--------------+--------------+
|  Branch A    |  Branch B    |  Branch C    |  <- Nebius Token Factory Sandboxes
|  Implementer |  Implementer |  Implementer |     (fork / isolate / rollback)
|  Verifier    |  Verifier    |  Verifier    |
|  Security    |  Security    |  Security    |
|  Performance |  Performance |  Performance |
+--------------+--------------+--------------+
  |
Score -> Select Winner -> Documentation Agent -> PQC Report
```

### Agents

| Agent | Role | Model (recommended) |
|-------|------|---------------------|
| Orchestrator | Plan, coordinate, decide | Nemotron-3-Ultra |
| Implementer | Write and edit code in sandbox | Nemotron-3-Super / Nano |
| Verifier | Generate and run tests | Nemotron-3-Super |
| Security | Dependency and static analysis | Nemotron-3-Super |
| Performance | Latency / memory impact | Nemotron-3-Nano |
| Documentation | PQC report + risk score | Nemotron-3-Nano |

---

## Quick start

```bash
git clone https://github.com/shankarsai000/pqc-factory.git
cd pqc-factory
pip install -e ".[dev]"

# Optional: real Nebius credentials
cp .env.example .env

# End-to-end demo (works offline in local mode)
python scripts/run_demo.py

# CLI
python -m pqc_factory.cli.main run --ticket pqc_factory/examples/sample_ticket.json -v
```

| Mode | Behavior | Use when |
|------|----------|----------|
| `local` (default) | Filesystem sandboxes + deterministic agents | Dev, tests, offline demo |
| `contree` | Real Nebius Token Factory Sandboxes | Production / live demo |

---

## Sample output

```
Status:     production_qualified
Score:      91.2/100
Risk:       25/100
Branches:   2
PR ready:   True
```

Produces a Markdown **PQC Report** with summary, tests, security, performance, risk score, rollback plan, and next steps.

---

## How we use Nebius + NVIDIA

- **Nebius Token Factory Sandboxes** - every approach runs in an isolated branch (fork, execute, rollback). Parallel exploration is first-class.
- **Nemotron models** - Orchestrator uses Ultra for long-horizon planning; specialists use Super/Nano for speed and cost.
- **Serverless-ready** - LLM client is OpenAI-compatible against `api.tokenfactory.nebius.com`.
- **Decision log** - every agent step is written to JSONL for auditability.

---

## Project layout

```
pqc_factory/
├── models/          # Ticket, Metrics, PQCReport, Agent I/O
├── llm/             # Nebius Token Factory client
├── sandbox/         # SandboxManager + DecisionLogger
├── agents/          # Implementer, Verifier, Security, Performance, Documentation
├── orchestrator/    # Engine, Planner, Scorer
├── cli/             # Typer CLI
├── examples/        # Sample tickets
└── tests/
scripts/run_demo.py
```

## Tests

```bash
pytest pqc_factory/tests/ -v
```

## Judging alignment

| Criterion | How PQC Factory addresses it |
|-----------|------------------------------|
| Technological Implementation | Deep use of Token Factory Sandboxes + Nemotron routing |
| Design | Complete product: ticket -> parallel exploration -> gates -> PQC report |
| Potential Impact | Attacks the verification tax after code generation |
| Quality of Idea | Parallel sandbox search + explicit Production-Qualified definition |

## License

MIT - see [LICENSE](LICENSE)
