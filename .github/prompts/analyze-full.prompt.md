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
   - **paper-analyst**: Read the paper and produce a list of claims it makes about the implementation
   - **code-inspector**: Audit the codebase against the paper manifest and produce a flat list of findings
   - **report-writer**: Assemble the final Markdown report

3. The report must cover ALL of these sections:
   - Executive Summary
   - Findings (severity-ordered: CRITICAL → WARNING → INFO; deduplicated)
   - Recommendations (grouped by severity)
   - **Benchmark Findings (machine-readable)** — a single fenced JSON
     code block at the end with the deduplicated CRITICAL findings in
     the 4-field benchmark schema (`issue-name`, `issue-explanation`,
     `relevant-code`, `paper-reference`). Required on every report.

4. Present the report to the user and offer to dive deeper into any section
