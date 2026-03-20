# CLAUDE.md — zkml-inspector

## Project Overview

zkml-inspector analyzes gaps between zkML (zero-knowledge machine learning) research papers and their implementations. It uses a multi-agent architecture where specialized sub-agents handle paper analysis, code inspection, ZKP soundness auditing, precision/cost analysis, and report generation.

## Architecture: Agent Dispatch Model

The system uses an **orchestrator + 4 sub-agents** pattern:

```
zkml-inspector (orchestrator)
  ├── paper-analyst     — Extracts claims from research papers with ZKP understanding
  ├── code-inspector    — Maps codebase to the commit/prove/verify lifecycle
  ├── zkp-auditor       — Core soundness reasoning, precision & cost analysis, can ask follow-ups to agents 1 & 2
  └── report-writer     — Assembles all findings into final Markdown report
```

All three analysis agents (paper-analyst, code-inspector, zkp-auditor) share a
common ZKP knowledge foundation: `.github/skills/analyze-zkml-gap/references/zkp_foundations.md`

### Key Design Principles:
- Every sub-agent understands ZKP fundamentals (commit → prove → verify lifecycle)
- paper-analyst is accountable for extracting ZKP-relevant claims, not just operators
- code-inspector is accountable for mapping code to ZKP lifecycle phases
- zkp-auditor can request follow-ups from paper-analyst and code-inspector
- zkp-auditor also handles precision gap analysis and gate cost profiling
- Each agent is independently invocable for standalone tasks

## Language & Runtime

- Python 3.10+ (for tests only)
- Type hints on all function signatures
- UTF-8 encoding everywhere

## Security Boundaries

- Agents MUST only read files within the user-provided paper path and codebase path
- Never execute code from the analyzed codebase — only read and parse
- Never write outside the current working directory
- Sanitize all file paths before use (resolve symlinks, reject `..` traversals)

## Report Formatting

- All output reports use Markdown
- Severity levels: `CRITICAL`, `WARNING`, `INFO`
- Every finding must include: severity, location (file + line), description, recommendation
- Tables use GitHub-Flavored Markdown syntax

## Code Style

- Reference data is stored in Markdown files under the skill directory
- All agents output JSON to stdout (parseable by the orchestrator)
- Errors go to stderr
- Exit code 0 = success, 1 = error

## zkML Domain Conventions

- "Operator" = a mathematical operation defined in the paper (MatMul, Conv2D, ReLU, Softmax, etc.)
- "Constraint" = a polynomial equality/inequality enforced in the circuit
- "Gate" = a single constraint in the arithmetic circuit
- "Approximation" = a simplified version of a non-polynomial operation used in the ZK circuit
- "Transformer Killer" = non-polynomial operations (Softmax, LayerNorm, GELU, Sigmoid, Tanh) that are expensive to prove in ZK

## Install Dependencies

No Python dependencies required. The agent pipeline relies on built-in
LLM capabilities for analysis. Reference data is stored in Markdown files
under `.github/skills/analyze-zkml-gap/references/`.

## Running Tests

```bash
python -m pytest tests/
```

## Agent Files

- `.github/agents/zkml-inspector.agent.md` — Orchestrator agent
- `.github/agents/paper-analyst.agent.md` — Paper extraction sub-agent
- `.github/agents/code-inspector.agent.md` — Code inspection sub-agent
- `.github/agents/zkp-auditor.agent.md` — Soundness auditor + precision/cost sub-agent
- `.github/agents/report-writer.agent.md` — Report generation sub-agent

## Prompt Files

- `.github/prompts/analyze-full.prompt.md` — Full paper vs. code analysis
- `.github/prompts/analyze-quick.prompt.md` — Quick scan for critical issues only
- `.github/prompts/audit-soundness.prompt.md` — Code-only soundness audit
- `.github/prompts/inspect-code.prompt.md` — Code-only inspection

## Reference Files

- `.github/skills/analyze-zkml-gap/references/zkp_foundations.md` — Shared ZKP knowledge for all agents
- `.github/skills/analyze-zkml-gap/references/operator_catalog.md` — 30+ operators with ZK patterns
- `.github/skills/analyze-zkml-gap/references/soundness_checklist.md` — 7-point security audit
- `.github/skills/analyze-zkml-gap/references/approximation_db.md` — Approximation strategies with error bounds
- `.github/skills/analyze-zkml-gap/references/gate_cost_table.md` — Cost estimates by operator

## Supported Inputs

| Input     | Formats                                          |
|-----------|--------------------------------------------------|
| Paper     | PDF (`.pdf`), LaTeX (`.tex`) — LaTeX is preferred |
| Codebase  | Rust (Halo2, EZKL), Python (EZKL), Circom, C++  |
