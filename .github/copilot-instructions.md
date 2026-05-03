# zkml-inspector — Project Guidelines

## Project Overview

zkml-inspector is a multi-agent VS Code Copilot system that compares zkML (zero-knowledge machine learning) research papers against their implementations and reports gaps.

This branch is the **knowledgeless** variant: the curated `references/` knowledge base that the knowledge-rich variant loads has been removed deliberately so the system can be benchmarked against runs that did receive that knowledge. Each agent works only from its model's background knowledge plus the paper and codebase it is given. The orchestration shape and the grader-compatible output schema are unchanged.

No runtime dependencies — the agent pipeline uses built-in LLM capabilities.

PDF reading requires the `pdf-reader` MCP server (configured in `.vscode/mcp.json`). It uses `npx @sylphx/pdf-reader-mcp` — Node.js must be available.

## Architecture: Orchestrator + 3 Sub-Agents

```
zkml-inspector (orchestrator)              .github/agents/zkml-inspector.agent.md
  ├── paper-analyst     (step 1)           .github/agents/paper-analyst.agent.md
  ├── code-inspector    (step 2)           .github/agents/code-inspector.agent.md
  └── report-writer     (step 3)           .github/agents/report-writer.agent.md
```

Pipeline: `paper-analyst → code-inspector → report-writer` (strictly sequential)

### Agent Capabilities & Responsibilities

| Agent | Responsibility | Tools | Inputs | Output |
|-------|---------------|-------|--------|--------|
| **zkml-inspector** | Orchestrates the sequential pipeline, validates inputs, dispatches sub-agents | read, search, agent, todo, web, createFile | Paper path + codebase path | Final report file |
| **paper-analyst** | Reads the paper and produces a list of claims it makes about the implementation | read, search, mcp::pdf-reader::read_pdf | Paper file path (.pdf/.tex only) | Paper manifest JSON |
| **code-inspector** | Audits the codebase against each paper claim | read, search | Paper manifest + codebase path | Audit findings JSON |
| **report-writer** | Assembles deduplicated, severity-ordered findings into a Markdown report and writes it to disk; report ends with the 4-field benchmark JSON of CRITICAL findings | read, createFile | Paper manifest + audit findings + output_path | Markdown report file |

### Key Design Constraints
- Pipeline is **strictly sequential** — each agent's output feeds the next
- paper-analyst **REQUIRES** an actual paper file — refuses codebase-as-substitute
- code-inspector uses the paper manifest as its checklist — every finding ties back to a paper claim
- report-writer **deduplicates** findings with shared root causes
- All sub-agents are `user-invocable: false`
- Batch analysis (`/analyze-batch`) saves reports **next to the manifest file** (not in the zkml-inspector workspace) to prevent code-inspector search contamination

### Workflows

| Prompt | When | Agents Used |
|--------|------|-------------|
| `/analyze-full` | Paper + codebase comparison | All 3 agents |
| `/analyze-batch` | Multiple papers + codebases from manifest | zkml-inspector → all 3 agents (per entry), then `agent_output.json` (flat benchmark schema) |

## Build & Test

```bash
python -m pytest tests/ -v           # Validates agent configs and consistency
```

## Security Boundaries
- Agents MUST only read files within the user-provided paper path and codebase path
- Never execute code from the analyzed codebase — only read and parse
- Never write outside the current working directory
- Sanitize all file paths before use (resolve symlinks, reject `..` traversals)

## Code Style
- Python 3.10+ with type hints on all signatures; UTF-8 everywhere
- All agents output JSON to stdout (parseable by orchestrator); errors to stderr
- Exit code 0 = success, 1 = error

## Report Conventions
- Severity levels: `CRITICAL`, `WARNING`, `INFO`
- Every finding: severity + location (file + line) + description + recommendation
- Tables use GitHub-Flavored Markdown
- Reports saved to `reports/{name}_report.md` unless user specifies a path
- Report ends with a fenced JSON block of CRITICAL findings in the 4-field benchmark schema (`issue-name`, `issue-explanation`, `relevant-code`, `paper-reference`)
