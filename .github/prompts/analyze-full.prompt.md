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
   - **report-writer**: Filter to CRITICAL findings, deduplicate, and export to `agent_output.json`

3. The report-writer receives:
   - The paper manifest (from paper-analyst)
   - The audit findings (from code-inspector)
   - An `entry_id` derived from the paper filename (lowercase, no extension)
   - An `output_path` pointing to `agent_output.json`

   The output is a flat JSON array of findings in the 5-field benchmark
   schema (`entry-id`, `issue-name`, `issue-explanation`, `relevant-code`,
   `paper-reference`). Only CRITICAL-severity findings are included.

4. Present a summary to the user: how many CRITICAL findings exported,
   how many WARNING/INFO filtered out, and the file location.
