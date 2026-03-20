# zkml-inspector

> A multi-agent VS Code Copilot system that analyzes gaps between zkML research papers and their implementations.

Given a PDF/LaTeX paper and a local codebase, **zkml-inspector** dispatches specialized sub-agents to generate a comprehensive **Discrepancy & Optimization Report** covering:

- **Soundness Violations** — Missing constraints, uncommitted weights, unconstrained wires, layer-skip attacks
- **ZKP Lifecycle Gaps** — Incomplete setup/commitment, proving, or verification phases
- **Performance Bottlenecks** — High-cost gates, unoptimized "Transformer Killer" operations (Softmax, LayerNorm, GELU)
- **Precision Mismatches** — Fixed-point scaling errors between paper assumptions and code reality

## Installation

### Prerequisites
- VS Code with GitHub Copilot
- Python 3.10+

### Setup

1. Clone this repository into your project (or as a standalone workspace):

   ```bash
   git clone https://github.com/zkml-inspector/zkml-inspector.git
   ```

2. Install Python dependencies:

   ```bash
   pip install -r .github/skills/analyze-zkml-gap/scripts/requirements.txt
   ```

3. The agents are automatically discovered by VS Code Copilot from the `.github/` directory.

## Usage

### Full Analysis (paper + code)

In VS Code Copilot Chat, invoke the orchestrator agent:

```
@zkml-inspector Analyze the paper at ./paper.pdf against the codebase at ./my-zkml-project/
```

Or use the prompt shortcut:

```
/analyze-full paper=./paper.tex codebase=./src/
```

### Quick Scan (critical issues only)

```
/analyze-quick paper=./paper.pdf codebase=./src/
```

### Soundness Audit (code only, no paper)

```
/audit-soundness codebase=./src/
```

### Code Inspection (structure overview)

```
/inspect-code codebase=./src/
```

### Supported Inputs

| Input      | Formats                     |
|------------|-----------------------------|
| Paper      | PDF (`.pdf`), LaTeX (`.tex`) |
| Codebase   | Rust (Halo2, EZKL), Python (EZKL), Circom, C++ |

> **Note**: LaTeX (`.tex`) input produces significantly better results than PDF.
> PDF parsing relies on text extraction which is inherently lossy — mathematical
> notation, equations, and operator definitions may be missed or garbled.
> When possible, prefer providing the original `.tex` source.

## Architecture

The system uses an **orchestrator + 4 sub-agents** pattern:

```
zkml-inspector (orchestrator)
  ├── paper-analyst     — Extracts claims from research papers with ZKP understanding
  ├── code-inspector    — Maps codebase to the commit/prove/verify lifecycle
  ├── zkp-auditor       — Core soundness reasoning, precision & cost analysis, can ask follow-ups to agents 1 & 2
  └── report-writer     — Assembles all findings into final Markdown report
```

All analysis agents share a common ZKP knowledge foundation
(`references/zkp_foundations.md`) covering the commit → prove → verify lifecycle.

### Pipeline Flow

```
1. paper-analyst + code-inspector  (parallel — independent extraction)
2. zkp-auditor                     (cross-references both, can ask follow-ups, runs precision & cost analysis)
3. report-writer                   (assembles final Markdown report)
```

### File Structure

```
.github/
├── agents/
│   ├── zkml-inspector.agent.md   # Orchestrator
│   ├── paper-analyst.agent.md    # Paper extraction sub-agent
│   ├── code-inspector.agent.md   # Code inspection sub-agent
│   ├── zkp-auditor.agent.md      # Soundness auditor + precision/cost sub-agent
│   └── report-writer.agent.md    # Report generation sub-agent
├── prompts/
│   ├── analyze-full.prompt.md    # Full paper vs. code analysis
│   ├── analyze-quick.prompt.md   # Quick scan for critical issues
│   ├── audit-soundness.prompt.md # Code-only soundness audit
│   └── inspect-code.prompt.md    # Code-only inspection
└── skills/analyze-zkml-gap/
    ├── SKILL.md                  # Shared library documentation
    ├── scripts/                  # Python analysis scripts
    ├── references/               # ZKP knowledge base (foundations, operators, etc.)
    └── assets/                   # Report templates
```

## Supported Frameworks

| Framework | Detection                | Support Level |
|-----------|--------------------------|---------------|
| EZKL      | `ezkl` config files      | Full          |
| Halo2     | `Cargo.toml` + halo2 dep | Full          |
| Circom    | `.circom` files          | Partial       |
| Python    | `setup.py`/`pyproject.toml` | Partial    |
| C++       | CMakeLists.txt           | Basic         |

## Recommended MCP Servers

For enhanced functionality, configure these MCP servers:

- **`@anthropic/mcp-server-fetch`** — Download papers from arXiv/IACR URLs
- **`github-mcp-server`** — Fetch reference implementations from GitHub
- **`@modelcontextprotocol/server-filesystem`** — Secure file access scoping

## License

MIT
