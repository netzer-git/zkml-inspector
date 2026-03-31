# zkml-inspector — Project Guidelines

## Project Overview

zkml-inspector is a multi-agent VS Code Copilot system that analyzes gaps between zkML (zero-knowledge machine learning) research papers and their implementations. It finds soundness violations, missing constraints, precision mismatches, and uncommitted values.

No runtime dependencies — the agent pipeline uses built-in LLM capabilities. Reference data is stored in Markdown under `.github/skills/analyze-zkml-gap/references/`.

PDF reading requires the `pdf-reader` MCP server (configured in `.vscode/mcp.json`). It uses `npx @sylphx/pdf-reader-mcp` — Node.js must be available.

## Architecture: Orchestrator + 3 Sub-Agents + Batch Runner

```
batch-runner (batch orchestrator)              .github/agents/batch-runner.agent.md
  └── invokes per entry:
        zkml-inspector (orchestrator)          .github/agents/zkml-inspector.agent.md
          ├── paper-analyst     (step 1)       .github/agents/paper-analyst.agent.md
          ├── code-inspector    (step 2)       .github/agents/code-inspector.agent.md
          └── report-writer     (step 3)       .github/agents/report-writer.agent.md
```

Pipeline: `paper-analyst → code-inspector → report-writer` (strictly sequential)

### Agent Capabilities & Responsibilities

| Agent | Responsibility | Tools | Inputs | Output |
|-------|---------------|-------|--------|--------|
| **zkml-inspector** | Orchestrates sequential pipeline, validates inputs, dispatches sub-agents | read, search, agent, todo, web, createFile | Paper path + codebase path | Final report file |
| **paper-analyst** | Extracts verification checklist from paper: commitment obligations, operator specs, constraints, precision requirements, protocol rounds | read, search, mcp::pdf-reader::read_pdf | Paper file path (.pdf/.tex only) | Paper manifest JSON |
| **code-inspector** | Audits codebase against paper manifest: commitment verification, operator coverage, soundness checks, protocol transcript audit, precision validation | read, search | Paper manifest + codebase path | Audit findings JSON |
| **report-writer** | Assembles findings into deduplicated Markdown report with severity ordering, writes report file to disk | read, createFile | Paper manifest + audit findings + output_path | Markdown report file |
| **batch-runner** | Processes multiple paper+codebase pairs from a JSON manifest, invokes zkml-inspector per entry with isolated context | read, search, agent, todo, edit, createFile | Manifest JSON path | Timestamped folder of reports |

### Key Design Constraints
- Pipeline is **strictly sequential** — each agent's output feeds the next
- paper-analyst **REQUIRES** an actual paper file — refuses codebase-as-substitute
- code-inspector receives the paper manifest and uses it as a **verification checklist** — reads only relevant code files
- code-inspector produces **audit findings** (not a code manifest) — each finding ties back to a paper claim
- report-writer **deduplicates** findings with shared root causes
- All sub-agents are `user-invocable: false`
- batch-runner saves reports **next to the manifest file** (not in the zkml-inspector workspace) to prevent code-inspector search contamination

### Workflows

| Prompt | When | Agents Used |
|--------|------|-------------|
| `/analyze-full` | Paper + codebase comparison | All 3 agents |
| `/analyze-quick` | Critical issues only | All 3 (code-inspector filters to CRITICAL) |
| `/analyze-batch` | Multiple papers + codebases from manifest | batch-runner → zkml-inspector → all 3 agents (per entry) |

## Build & Test

```bash
python -m pytest tests/ -v           # Validates agent configs, references, and consistency
```

## Security Boundaries
- Agents MUST only read files within the user-provided paper path and codebase path
- Never execute code from the analyzed codebase — only read and parse
- Never write outside the current working directory
- Sanitize all file paths before use (resolve symlinks, reject `..` traversals)

## Code Style
- Python 3.10+ with type hints on all signatures; UTF-8 everywhere
- Reference data lives in `.github/skills/analyze-zkml-gap/references/` as Markdown
- All agents output JSON to stdout (parseable by orchestrator); errors to stderr
- Exit code 0 = success, 1 = error

## Report Conventions
- Severity levels: `CRITICAL`, `WARNING`, `INFO`
- Every finding: severity + location (file + line) + description + recommendation
- Tables use GitHub-Flavored Markdown; operator status uses ✅/⚠️/❌/➕
- Reports saved to `examples/{name}_report.md` unless user specifies a path

## zkML Domain Terms
- **Operator** = mathematical operation (MatMul, Conv2D, ReLU, Softmax, etc.)
- **Constraint** = polynomial equality/inequality enforced in the circuit
- **Approximation** = simplified non-polynomial operation for ZK circuits
- **Commitment obligation** = a value that must be committed for soundness
- **Transformer Killer** = non-polynomial ops expensive to prove (Softmax, LayerNorm, GELU, Sigmoid, Tanh)

## Key Reference Files

See `CLAUDE.md` for the full file inventory. Critical references for agent development:
- `references/zkp_foundations.md` — Shared ZKP lifecycle knowledge (paper-analyst + code-inspector load this)
- `references/soundness_checklist.md` — Soundness audit checklist (code-inspector loads this)
- `references/operator_catalog.md` — 30+ operators with ZK patterns and gap signatures
- `references/approximation_db.md` — Approximation strategies with error bounds
