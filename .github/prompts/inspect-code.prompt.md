---
description: "Inspect a zkML codebase structure without paper comparison"
agent: "zkml-inspector"
tools:
  - read
  - search
  - agent
argument-hint: "codebase=<path_to_codebase>"
---

# Codebase Inspection

Analyze a zkML codebase to understand its structure, framework, operators, and ZKP lifecycle coverage.

## Instructions

1. Dispatch code-inspector to analyze the codebase
2. Present the code manifest in a readable format:
   - Framework detected and proof system
   - ZKP lifecycle coverage (setup/commitment, proving, verification)
   - Operators found with implementation types
   - Precision configuration
   - Any non-deterministic operations or unclear areas
3. Optionally dispatch precision-cost for gate cost estimation if user wants performance data
