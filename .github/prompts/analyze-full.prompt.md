---
description: "Full audit of a zkML paper vs codebase implementation"
agent: "zkml-inspector"
tools:
  - read
  - search
  - agent
  - todo
argument-hint: "paper=<path_to_paper> codebase=<path_to_codebase>"
---

# Full zkML Analysis

Perform a comprehensive audit comparing the research paper against the implementation codebase.

## Instructions

1. Confirm the paper path and codebase path with the user
2. Run the sequential pipeline:
   - **paper-analyst**: Extract verification checklist from the paper (commitment obligations, operator specs, constraints, precision requirements)
   - **code-inspector**: Audit the codebase against the paper manifest (commitment audit, operator coverage, soundness checks, protocol transcript, precision)
   - **report-writer**: Assemble the final Markdown report

3. The report must cover ALL of these sections:
   - Executive Summary
   - Commitment Audit
   - Operator Coverage Matrix (✅/⚠️/❌/➕)
   - Soundness Findings
   - Protocol Transcript Findings (if any)
   - Precision Findings (if any)
   - Recommendations (prioritized by severity: CRITICAL → WARNING → INFO)
   - **Benchmark Findings (machine-readable)** — a single fenced JSON
     code block at the end with the deduplicated findings in the 8-field
     benchmark schema. Required on every report.

   Note: every finding flows from code-inspector with `category` and
   `security_concern` already assigned (per
   `references/benchmark_taxonomy.md`); report-writer only renders these
   verbatim.

4. Present the report to the user and offer to dive deeper into any section
