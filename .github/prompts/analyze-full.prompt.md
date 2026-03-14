---
description: "Full discrepancy & optimization analysis of a zkML paper vs codebase"
agent: "zkml-inspector"
tools:
  - execute
  - read
  - search
argument-hint: "paper=<path_to_paper> codebase=<path_to_codebase>"
---

# Full zkML Analysis

Perform a comprehensive 5-stage analysis comparing the research paper against the implementation codebase.

## Instructions

1. Confirm the paper path and codebase path with the user
2. Run the full `analyze-zkml-gap` skill pipeline:
   - **Stage 1**: Parse the paper (extract operators, constraints, approximations)
   - **Stage 2**: Inspect the codebase (detect framework, extract implementations)
   - **Stage 3**: Gap analysis (operator coverage, constraint completeness, Transformer Killers)
   - **Stage 4**: Precision & cost validation (fixed-point scaling, gate costs)
   - **Stage 5**: Generate the full Markdown report

3. The report must cover ALL of these sections:
   - Executive Summary
   - Operator Coverage Matrix
   - Logic Gaps (missing constraints, non-deterministic operations)
   - Precision Analysis (fixed-point scaling mismatches)
   - Performance Bottlenecks (high-cost gates, Transformer Killer issues)
   - Soundness & Zero-Knowledge Risks
   - Recommendations (prioritized by severity)

4. Present the report to the user and offer to dive deeper into any section
