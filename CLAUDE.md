# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
python -m pytest tests/ -v              # Run all tests
python -m pytest tests/ -v -k "batch"  # Run a single test class/pattern
```

No build step, no runtime dependencies. Python 3.10+ required. Node.js required only for PDF reading via the `pdf-reader` MCP server (`.vscode/mcp.json`, `.claude/mcp.json`).

## Architecture

**3 sub-agents**, strictly sequential pipeline, available for both GitHub Copilot and Claude Code:

### GitHub Copilot (`.github/`)

```
zkml-inspector (orchestrator)       .github/agents/zkml-inspector.agent.md
  ├── paper-analyst   (step 1)      .github/agents/paper-analyst.agent.md
  ├── code-inspector  (step 2)      .github/agents/code-inspector.agent.md
  └── report-writer   (step 3)      .github/agents/report-writer.agent.md
```

Each agent is defined as a `.agent.md` file with YAML frontmatter (`description`, `tools`, `agents`). Sub-agents have `user-invocable: false`. Prompt shortcuts live in `.github/prompts/`.

### Claude Code (`.claude/`)

```
/analyze-full or /analyze-batch     .claude/commands/analyze-full.md
  ├── paper-analyst   (step 1)      .claude/agents/paper-analyst.md
  ├── code-inspector  (step 2)      .claude/agents/code-inspector.md
  └── report-writer   (step 3)      .claude/agents/report-writer.md
```

In Claude Code, the main session acts as orchestrator (since sub-agents cannot dispatch further sub-agents). Commands in `.claude/commands/` contain the orchestration workflow. Sub-agents are dispatched via the Agent tool.

### Data flow

1. **paper-analyst** reads a `.pdf` or `.tex` paper → outputs **paper manifest JSON** (operators, commitment_obligations, proof_system, quantization)
2. **code-inspector** receives the paper manifest + codebase path → outputs **audit findings JSON** (commitment_audit, operator_coverage, soundness_findings)
3. **report-writer** receives both → writes a **Markdown report** to disk (via `createFile` in Copilot, `Write` in Claude Code)

The orchestrator never does analysis itself — it validates inputs, dispatches sub-agents in order, passes outputs forward, and saves the report to `reports/{name}_report.md` if no path is specified.

### Workflows

| Prompt | Behavior |
|--------|----------|
| `/analyze-full` | Full pipeline, complete report |
| `/analyze-batch` | Reads `batch_manifest.json`, runs full pipeline per entry, saves reports **next to the manifest** (NOT inside zkml-inspector workspace), produces `summary.json`, supports resume by skipping existing reports |

### Key constraints

- paper-analyst **requires** an actual paper file — never accepts a codebase as substitute
- code-inspector uses the paper manifest as a **verification checklist**, not a code manifest — every finding must tie back to a paper claim
- Sub-agents must never have the `execute` tool — analysis is read-only
- All agents output JSON to stdout; errors to stderr; exit 0 = success, 1 = error

## Reference Knowledge Base

Shared reference files live in the top-level `references/` directory — a single copy used by both Copilot and Claude Code agents at runtime:

| Reference | Path | Used by |
|-----------|------|---------|
| `zkp_foundations.md` | `references/` | paper-analyst, code-inspector |
| `soundness_checklist.md` | `references/` | code-inspector, report-writer |
| `operator_catalog.md` | `references/` | paper-analyst |
| `approximation_db.md` | `references/` | paper-analyst |

Single source of truth — both platforms read from the same files.

## Report Conventions

- Severity: `CRITICAL` > `WARNING` > `INFO`
- Every finding: severity + file + line + description + recommendation
- Tables use GitHub-Flavored Markdown; operator status: ✅/⚠️/❌/➕
- report-writer deduplicates findings with shared root causes

## Tests

`tests/test_scripts.py` validates the **Copilot layer** (`.github/`):
- All required agent, prompt, and reference files exist
- Agent frontmatter has required fields (`description`, `tools`, `agents` for orchestrator)
- Sub-agents are not user-invocable and don't have `execute` tool
- No references to removed scripts or removed components
- Content quality: paper-analyst outputs commitment_obligations, code-inspector references soundness_checklist.md, report-writer has dedup logic
- Batch prompt has resume logic, summary.json output, context compaction, and isolation between entries
- `examples/batch_manifest.json` is valid JSON with required fields (`entry-id`, `paper`, `codebase`)

`tests/test_claude_commands.py` validates the **Claude Code layer** (`.claude/`):
- `.claude/commands/analyze-full.md` and `analyze-batch.md` exist with required orchestration elements
- `.claude/mcp.json` is valid and consistent with `.vscode/mcp.json`
- Commands use Claude Code tool names (`Write`, `Agent`, `mcp__pdf-reader__read_pdf`) not Copilot names (`createFile`)

## zkML Domain Terms

- **Operator** — mathematical operation in the ML model (MatMul, Conv2D, ReLU, Softmax, etc.)
- **Constraint** — polynomial equality/inequality enforced in the ZK circuit
- **Commitment obligation** — a value that must be committed for soundness
- **Transformer Killer** — non-polynomial op expensive to prove (Softmax, LayerNorm, GELU, Sigmoid, Tanh)
- **Approximation** — simplified non-polynomial operation substituted for ZK circuits
