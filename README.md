# zkml-inspector

> A VS Code Copilot skill that analyzes the gap between zkML research papers and their implementations.

Given a PDF/LaTeX paper and a local codebase, **zkml-inspector** generates a comprehensive **Discrepancy & Optimization Report** covering:

- **Logic Gaps** — Missing constraints, non-deterministic operations, undocumented operators
- **Performance Bottlenecks** — High-cost gates (Sigmoid, Tanh, Softmax), unoptimized "Transformer Killer" operations
- **Soundness Risks** — Zero-knowledge property violations, unsound approximations, missing range checks
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

3. The skill and agent are automatically discovered by VS Code Copilot from the `.github/` directory.

## Usage

### Full Analysis

In VS Code Copilot Chat, invoke the agent:

```
@zkml-inspector Analyze the paper at ./paper.pdf against the codebase at ./my-zkml-project/
```

Or use the prompt shortcut:

```
/analyze-full paper=./paper.tex codebase=./src/
```

### Quick Scan

For a fast check of critical issues only:

```
/analyze-quick paper=./paper.pdf codebase=./src/
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

```
.github/
├── skills/analyze-zkml-gap/
│   ├── SKILL.md              # Core skill — 5-stage reasoning pipeline
│   ├── scripts/              # Python analysis scripts
│   ├── references/           # zkML knowledge base
│   └── assets/               # Report templates
├── agents/zkml-inspector.agent.md
└── prompts/                  # analyze-full, analyze-quick
```

### Analysis Pipeline

1. **Paper Parsing** — Extract mathematical constraints, operators, and approximations from LaTeX/PDF
2. **Codebase Inspection** — Auto-detect framework, extract operator implementations and constraint definitions
3. **Gap Analysis** — Agent-driven reasoning: operator coverage, constraint completeness, Transformer Killer detection
4. **Precision Validation** — Compare fixed-point scaling between paper and code
5. **Report Generation** — Markdown report with severity-tagged findings and recommendations

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
