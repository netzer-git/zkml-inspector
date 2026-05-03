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

1. **paper-analyst** reads a `.pdf` or `.tex` paper → outputs a **paper manifest JSON** (a flat list of `claims`, each with `paper_reference: {section_anchor, verbatim_quote}`)
2. **code-inspector** receives the paper manifest + codebase path → outputs an **audit findings JSON** (a flat `findings` array; each finding ties back to a paper claim)
3. **report-writer** receives both → writes a **Markdown report** to disk (via `createFile` in Copilot, `Write` in Claude Code), ending with a 4-field benchmark JSON block of CRITICAL findings

The orchestrator never does analysis itself — it validates inputs, dispatches sub-agents in order, passes outputs forward, and saves the report to `reports/{name}_report.md` if no path is specified.

### Workflows

| Prompt | Behavior |
|--------|----------|
| `/analyze-full` | Full pipeline, complete report |
| `/analyze-batch` | Reads `batch_manifest.json`, runs full pipeline per entry, saves reports **next to the manifest** (NOT inside zkml-inspector workspace), produces `agent_output.json` (flat array in the zkML-inspector-benchmark schema), supports resume by skipping existing reports |

### Key constraints

- paper-analyst **requires** an actual paper file — never accepts a codebase as substitute
- code-inspector uses the paper manifest as its checklist — every finding ties back to a paper claim
- Sub-agents must never have the `execute` tool — analysis is read-only
- All agents output JSON to stdout; errors to stderr; exit 0 = success, 1 = error

## Knowledgeless variant

This branch deliberately omits the curated `references/` knowledge base that
the knowledge-rich variant of zkml-inspector loads. Each agent works only from
its own model's background knowledge plus the paper and codebase it is given.
The orchestration shape and the grader-compatible output schema are unchanged,
so runs from this branch can be benchmarked against runs from the
knowledge-rich branch.

## Report Conventions

- Severity: `CRITICAL` > `WARNING` > `INFO`
- Every finding: severity + file + line + description + recommendation
- Tables use GitHub-Flavored Markdown
- report-writer deduplicates findings with shared root causes
- Report ends with a fenced JSON block of CRITICAL findings in the 4-field benchmark schema (`issue-name`, `issue-explanation`, `relevant-code`, `paper-reference`)

## Tests

`tests/test_scripts.py` validates the **Copilot layer** (`.github/`):
- All required agent and prompt files exist
- Agent frontmatter has required fields (`description`, `tools`, `agents` for orchestrator)
- Sub-agents are not user-invocable and don't have the `execute` tool
- No references to removed scripts
- Batch prompt has resume logic, `agent_output.json` output, context compaction, and isolation between entries
- `examples/batch_manifest.json` is valid JSON with required fields (`entry-id`, `paper`, `codebase`)

`tests/test_claude_commands.py` validates the **Claude Code layer** (`.claude/`):
- `.claude/commands/analyze-full.md` and `analyze-batch.md` exist with required orchestration elements
- `.claude/mcp.json` is valid and consistent with `.vscode/mcp.json`
- Commands use Claude Code tool names (`Write`, `Agent`, `mcp__pdf-reader__read_pdf`) not Copilot names (`createFile`)
