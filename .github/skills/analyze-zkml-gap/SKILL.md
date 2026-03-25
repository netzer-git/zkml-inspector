---
name: analyze-zkml-gap
description: >-
  Shared library of references for zkML gap analysis. Used by the sub-agent
  pipeline (paper-analyst, code-inspector, report-writer) orchestrated by
  the zkml-inspector agent. Do NOT invoke this skill directly — use the
  zkml-inspector agent or one of the prompt files instead.
  Triggers: "zkml gap", "paper vs code", "discrepancy report",
  "audit zkml", "implementation gap", "circuit analysis".
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
| `references/zkp_foundations.md` | paper-analyst, code-inspector | Shared ZKP knowledge (commit/prove/verify lifecycle) |
| `references/operator_catalog.md` | paper-analyst | Known operators with ZK implementation patterns |
| `references/soundness_checklist.md` | code-inspector | Soundness & ZK security audit checklist |
| `references/approximation_db.md` | paper-analyst | Approximation strategies with error bounds |

## Agent Pipeline

The orchestrator (`zkml-inspector`) dispatches agents in this order:

```
1. paper-analyst       (extracts verification checklist from paper)
2. code-inspector      (audits codebase against the checklist)
3. report-writer       (assembles final Markdown report)
```

See `.github/agents/` for individual agent definitions.
See `.github/prompts/` for user-facing prompt files.
