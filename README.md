# zkml-inspector

> A multi-agent VS Code Copilot system that analyzes gaps between zkML research papers and their implementations.

Given a PDF/LaTeX paper and a local codebase, **zkml-inspector** dispatches specialized sub-agents to find:

- **Soundness Violations** — Missing constraints, uncommitted weights, unconstrained wires, layer-skip attacks
- **ZKP Lifecycle Gaps** — Incomplete setup/commitment, proving, or verification phases
- **Precision Mismatches** — Fixed-point scaling errors between paper assumptions and code reality

## Installation

### Prerequisites
- VS Code with GitHub Copilot

### Setup

1. Clone this repository into your project (or as a standalone workspace):

   ```bash
   git clone https://github.com/zkml-inspector/zkml-inspector.git
   ```

2. The agents are automatically discovered by VS Code Copilot from the `.github/` directory. No runtime dependencies required.

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

### Batch Analysis (multiple papers)

Process multiple paper+codebase pairs from a JSON manifest:

```
/analyze-batch manifest=../zkml-targets/batch_manifest.json
```

Create a `batch_manifest.json` (see `examples/batch_manifest.json`):

```json
{
  "analyses": [
    { "name": "ezkl", "paper": "./ezkl/paper.pdf", "codebase": "./ezkl/code/" },
    { "name": "zkllm", "paper": "./zkllm/paper.tex", "codebase": "./zkllm/src/" }
  ],
  "output_dir": "./reports/v0.1"
}
```

- `output_dir` (optional): custom output folder for reports, relative to manifest.
  If omitted, auto-creates `<manifest_dir>/reports/run_<YYYYMMDD_HHMMSS>/`.

**Resume support**: If interrupted, re-invoke `/analyze-batch` in a fresh
conversation with the same manifest. It detects existing reports and
skips already-completed analyses.

> **Tip**: Use a multi-root VS Code workspace containing both the zkml-inspector
> folder and your targets folder for best results.

### Supported Inputs

| Input      | Formats                     |
|------------|-----------------------------|
| Paper      | PDF (`.pdf`), LaTeX (`.tex`) |
| Codebase   | Any language (Rust, Python, Circom, C++, etc.) |

> **Note**: LaTeX (`.tex`) input produces significantly better results than PDF.
> PDF parsing relies on text extraction which is inherently lossy — mathematical
> notation, equations, and operator definitions may be missed or garbled.
> When possible, prefer providing the original `.tex` source.

## Architecture

The system uses an **orchestrator + 3 sub-agents** pattern with a strictly sequential pipeline:

```
zkml-inspector (orchestrator)
  ├── paper-analyst     — Extracts verification checklist from research papers
  ├── code-inspector    — Audits codebase against the paper manifest
  └── report-writer     — Assembles findings into final Markdown report
```

### Pipeline Flow

```
1. paper-analyst   (extracts paper manifest: operators, commitment obligations, constraints)
2. code-inspector  (audits codebase against paper manifest, produces findings)
3. report-writer   (assembles findings into deduplicated Markdown report)
```

Each agent's output feeds the next. All analysis agents share a common ZKP knowledge
foundation (`references/zkp_foundations.md`) covering the commit → prove → verify lifecycle.

### File Structure

```
.github/
├── agents/
│   ├── zkml-inspector.agent.md   # Orchestrator
│   ├── paper-analyst.agent.md    # Paper extraction sub-agent
│   ├── code-inspector.agent.md   # Code audit sub-agent
│   └── report-writer.agent.md    # Report generation sub-agent
├── prompts/
│   ├── analyze-full.prompt.md    # Full paper vs. code analysis
│   └── analyze-batch.prompt.md   # Batch analysis from manifest
└── skills/analyze-zkml-gap/
    ├── SKILL.md                  # Shared library documentation
    └── references/               # ZKP knowledge base (foundations, operators, etc.)
```

## License

MIT
