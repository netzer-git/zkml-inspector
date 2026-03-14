---
description: "Quick scan for critical zkML implementation issues"
agent: "zkml-inspector"
tools:
  - execute
  - read
  - search
argument-hint: "paper=<path_to_paper> codebase=<path_to_codebase>"
---

# Quick zkML Scan

Perform a rapid scan focusing only on CRITICAL issues.

## Instructions

1. Parse the paper and codebase using the analysis scripts
2. Focus ONLY on critical findings:
   - Missing operator implementations (paper defines it, code doesn't have it)
   - Transformer Killer operations using exact implementations (Softmax, LayerNorm without approximation)
   - Missing weight commitments (soundness violation)
   - Missing intermediate constraints (allows proof cheating)
   - Non-deterministic operations still present (dropout, random sampling)
3. Skip INFO and WARNING findings
4. Output a concise report: list each CRITICAL finding with file, line, and one-sentence recommendation
5. End with a total count: "X critical issues found"
