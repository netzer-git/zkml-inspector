---
description: "Audit ZKP soundness of a zkML codebase without a paper"
agent: "zkml-inspector"
tools:
  - read
  - search
  - agent
argument-hint: "codebase=<path_to_codebase>"
---

# Soundness Audit (Code Only)

Audit a zkML codebase for soundness vulnerabilities without comparing to a paper.

## Instructions

1. Dispatch code-inspector to analyze the codebase
2. Dispatch zkp-auditor with the code manifest and an empty paper manifest
3. The auditor will check universal soundness properties:
   - Are all layer outputs constrained?
   - Are weights committed?
   - Are wires connected between layers?
   - Are range checks present after multiplications?
   - Is the final output exposed as a public value?
   - Are non-deterministic operations removed?
4. Present findings as a soundness report, ordered by severity
