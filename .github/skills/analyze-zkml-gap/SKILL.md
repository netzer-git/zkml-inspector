---
name: analyze-zkml-gap
description: >-
  Shared library of scripts, references, and templates for zkML gap analysis.
  Used by the sub-agent pipeline (paper-analyst, code-inspector, zkp-auditor,
  report-writer) orchestrated by the zkml-inspector agent.
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

### References (loaded by sub-agents as needed)

| Reference | Used By | Purpose |
|-----------|---------|---------|
| `references/zkp_foundations.md` | paper-analyst, code-inspector, zkp-auditor | Shared ZKP knowledge (commit/prove/verify lifecycle) |
| `references/operator_catalog.md` | paper-analyst, zkp-auditor | Known operators with ZK implementation patterns |
| `references/soundness_checklist.md` | zkp-auditor | 7-point soundness & ZK security audit |
| `references/approximation_db.md` | paper-analyst, zkp-auditor | Approximation strategies with error bounds |
| `references/gate_cost_table.md` | zkp-auditor | Gate cost estimates by operator and proof system |

### Assets

| Asset | Used By | Purpose |
|-------|---------|---------|
| `assets/report_template.md` | report-writer | Markdown template for final report |

## Agent Pipeline

The orchestrator (`zkml-inspector`) dispatches agents in this order:

```
1. paper-analyst + code-inspector  (parallel — independent)
2. zkp-auditor                     (uses outputs from 1, can ask follow-ups, runs precision & cost analysis)
3. report-writer                   (uses all outputs)
```

See `.github/agents/` for individual agent definitions.
See `.github/prompts/` for user-facing prompt files.
