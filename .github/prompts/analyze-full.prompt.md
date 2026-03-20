---
description: "Full discrepancy & optimization analysis of a zkML paper vs codebase"
agent: "zkml-inspector"
tools:
  - read
  - search
  - agent
  - todo
argument-hint: "paper=<path_to_paper> codebase=<path_to_codebase>"
---

# Full zkML Analysis

Perform a comprehensive analysis comparing the research paper against the implementation codebase using the sub-agent pipeline.

## Instructions

1. Confirm the paper path and codebase path with the user
2. Run the full orchestrator pipeline, dispatching agents in order:
   - **paper-analyst + code-inspector** (parallel): Extract structured data from both
   - **zkp-auditor**: Core soundness analysis with follow-up questions to agents 1 & 2, plus precision & gate cost analysis
   - **report-writer**: Assemble the final Markdown report

3. The report must cover ALL of these sections:
   - Executive Summary
   - Operator Coverage Matrix (✅/⚠️/❌/➕)
   - ZKP Lifecycle Audit (setup/commitment, proving/constraints, verification)
   - Soundness Findings (from the 7-point checklist)
   - Precision Analysis (fixed-point scaling mismatches)
   - Performance Bottlenecks (gate costs, Transformer Killers)
   - Recommendations (prioritized by severity: CRITICAL → WARNING → INFO)

4. Present the report to the user and offer to dive deeper into any section
