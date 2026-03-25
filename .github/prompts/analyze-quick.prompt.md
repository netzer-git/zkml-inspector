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

Perform a rapid scan focusing only on CRITICAL issues.

## Instructions

1. Run the sequential pipeline (paper-analyst → code-inspector → report)
2. Tell the code-inspector to focus ONLY on critical findings:
   - Missing operator implementations (paper defines it, code doesn't have it)
   - Uncommitted values (weights, biases, scale factors not committed)
   - Missing or incorrect constraints (allows proof cheating)
   - Unconstrained wires between layers (layer-skip attack)
   - Mock/phantom implementations (empty prove/commit functions)
   - Non-deterministic operations still present
   - Final output not exposed as public value
3. Output a concise finding list: each CRITICAL finding with file, line, and one-sentence recommendation
4. End with a total count: "X critical issues found"
