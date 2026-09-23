# Production-Qualified Change (PQC) Factory

**Multi-agent system that turns a high-level ticket into a Production-Qualified Change**  
using **Nebius Token Factory Sandboxes** + **NVIDIA Nemotron** models.

Built for the **Nebius x NVIDIA Global AI Hackathon** – Coding & Agentic Engineering Track.

---

## What it does

1. Accepts a natural-language ticket  
2. Plans 2–3 alternative approaches  
3. Forks isolated sandbox branches  
4. Runs **Implementer ↔ Verifier** loops on each branch  
5. Runs **Security** and **Performance** gates  
6. Scores every branch and selects the winner  
7. Generates a full **Production-Qualified Change report** (ready for human review / PR)

---

## Architecture

```
Ticket
  ↓
Orchestrator (Nemotron-Ultra)
  ↓
┌─────────────┬─────────────┬─────────────┐
│  Branch A   │  Branch B   │  Branch C   │   ← Token Factory Sandboxes
│ Implementer │ Implementer │ Implementer │
│  Verifier   │  Verifier   │  Verifier   │
│  Security   │  Security   │  Security   │
│ Performance │ Performance │ Performance │
└─────────────┴─────────────┴─────────────┘
  ↓
Score → Select Winner → Documentation Agent → PQC Report
```

---

## Quick start

```bash
# 1. Clone & install
pip install -e ".[dev]"

# 2. (Optional) set real Nebius credentials
cp .env.example .env
# edit .env with your NEBIUS_API_KEY

# 3. Run on the sample ticket (works offline in local mode)
pqc run --ticket pqc_factory/examples/sample_ticket.json -v
```

---

## Local vs Nebius mode

| Mode     | Behavior                                      | When to use          |
|----------|-----------------------------------------------|----------------------|
| `local`  | Filesystem sandboxes + deterministic agents   | Development & tests  |
| `contree`| Real Nebius Token Factory Sandboxes           | Production / demo    |

Set `SANDBOX_MODE=local` (default) or `contree` in `.env`.

---

## Project layout

```
pqc_factory/
├── models/          # Ticket, Metrics, PQCReport, Agent I/O
├── llm/             # Nebius Token Factory client
├── sandbox/         # SandboxManager + DecisionLogger
├── agents/          # Implementer, Verifier, Security, Performance, Documentation
├── orchestrator/    # Engine, Planner, Scorer
├── cli/             # Typer CLI (pqc run / status / report)
├── examples/        # Sample tickets
└── tests/           # Unit + integration tests
```

---

## Tests

```bash
pytest pqc_factory/tests/ -v
```

---

## Hackathon highlights

- **Heavy use of Token Factory Sandboxes** (branch / fork / isolated execution)
- **Nemotron models** for planning, implementation, verification and reporting
- Complete product experience (not a POC)
- Transparent decision log (JSONL)
- Clear PQC definition and risk scoring

---

## License

MIT
