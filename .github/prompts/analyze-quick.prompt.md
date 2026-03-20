---
description: "Quick scan for critical zkML implementation issues"
agent: "zkml-inspector"
tools:
  - read
  - search
  - agent
argument-hint: "paper=<path_to_paper> codebase=<path_to_codebase>"
---

# Quick zkML Scan

Perform a rapid scan focusing only on CRITICAL issues using the sub-agent pipeline.

## Instructions

1. Dispatch paper-analyst and code-inspector in parallel
2. Dispatch zkp-auditor with instruction to focus ONLY on critical findings:
   - Missing operator implementations (paper defines it, code doesn't have it)
   - Transformer Killer operations using exact implementations
   - Missing weight/bias commitments (soundness violation)
   - Missing intermediate constraints (allows proof cheating)
   - Unconstrained wires between layers (layer-skip attack)
   - Non-deterministic operations still present
   - Final output not exposed as public value
3. Output a concise finding list: each CRITICAL finding with file, line, and one-sentence recommendation
4. End with a total count: "X critical issues found"
