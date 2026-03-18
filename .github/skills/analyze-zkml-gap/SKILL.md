---
name: analyze-zkml-gap
description: >-
  Shared library of scripts, references, and templates for zkML gap analysis.
  Used by the sub-agent pipeline (paper-analyst, code-inspector, zkp-auditor,
  precision-cost, report-writer) orchestrated by the zkml-inspector agent.
  Do NOT invoke this skill directly — use the zkml-inspector agent or one of
  the prompt files instead. Triggers: "zkml gap", "paper vs code",
  "discrepancy report", "audit zkml", "implementation gap", "circuit analysis".
argument-hint: "Use the zkml-inspector agent instead of invoking this skill directly"
---

# analyze-zkml-gap — Shared Library

This skill folder contains the **shared resources** used by the zkml-inspector
agent pipeline. It is NOT a standalone pipeline — the orchestrator agent
dispatches sub-agents that use these resources.

## Contents

### Scripts (used by sub-agents)

| Script | Used By | Purpose |
|--------|---------|---------|
| `scripts/parse_paper.py` | paper-analyst | Extract operators, constraints, math from LaTeX/PDF |
| `scripts/inspect_codebase.py` | code-inspector | Detect framework, extract operators, constraints from code |
| `scripts/precision_checker.py` | precision-cost | Compare fixed-point precision between paper and code |
| `scripts/gate_cost_profiler.py` | precision-cost | Estimate circuit gate costs per operator |

### References (loaded by sub-agents as needed)

| Reference | Used By | Purpose |
|-----------|---------|---------|
| `references/zkp_foundations.md` | paper-analyst, code-inspector, zkp-auditor | Shared ZKP knowledge (commit/prove/verify lifecycle) |
| `references/operator_catalog.md` | paper-analyst, zkp-auditor | Known operators with ZK implementation patterns |
| `references/soundness_checklist.md` | zkp-auditor | 7-point soundness & ZK security audit |
| `references/approximation_db.md` | paper-analyst, precision-cost | Approximation strategies with error bounds |
| `references/gate_cost_table.md` | precision-cost | Gate cost estimates by operator and proof system |

### Assets

| Asset | Used By | Purpose |
|-------|---------|---------|
| `assets/report_template.md` | report-writer | Markdown template for final report |

## Agent Pipeline

The orchestrator (`zkml-inspector`) dispatches agents in this order:

```
1. paper-analyst + code-inspector  (parallel — independent)
2. zkp-auditor                     (uses outputs from 1, can ask follow-ups)
3. precision-cost                  (uses outputs from 1, after auditor corrections)
4. report-writer                   (uses all outputs)
```

See `.github/agents/` for individual agent definitions.
See `.github/prompts/` for user-facing prompt files.
