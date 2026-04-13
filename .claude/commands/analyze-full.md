# Full zkML Analysis

Perform a comprehensive audit comparing a research paper against its implementation codebase.

## Input

$ARGUMENTS

The user should provide a paper path and codebase path, e.g.:
`paper=<path_to_paper> codebase=<path_to_codebase>`

## Step 0: Validate Inputs

Both a paper path AND a codebase path are MANDATORY.

**Paper path validation:**
- Confirm the user provided an explicit paper file path (`.pdf` or `.tex`)
- The paper path must point to a file, NOT a directory
- If no paper file is provided, **ASK for it** — do not proceed without one
- PDF files are supported via the `mcp__pdf-reader__read_pdf` MCP tool

**Codebase path validation:**
- Confirm the codebase path exists and is a directory
- If no codebase path is provided, **ASK for it**

## Sub-Agent Constraints

When dispatching sub-agents, enforce these rules:
- **Pass data inline:** Always pass the paper manifest and audit findings as
  JSON content directly in the agent prompt. NEVER pass file paths to persisted
  tool output — downstream agents cannot parse tool-result wrapper files.
- **No scripts:** Sub-agents must only use their declared tools (Read, Glob,
  Grep, and mcp__pdf-reader__read_pdf for paper-analyst; Write for
  report-writer). If a sub-agent asks to run Bash or python, deny it.
- **No memory:** Sub-agents must not create agent memory files. Each dispatch
  is stateless.

## Step 1: Create Task List

Use `TaskCreate` to create tasks for the pipeline steps:
1. **Paper analysis** — subject: `Paper analysis (<paper_name>)`, activeForm: `Analyzing paper`
2. **Code audit** — subject: `Code audit (<codebase_name>)`, activeForm: `Auditing codebase`
3. **Report generation** — subject: `Report generation`, activeForm: `Generating report`

Set up `addBlockedBy` dependencies so code audit is blocked by paper analysis,
and report generation is blocked by code audit.

## Step 2: Paper Analysis (paper-analyst)

Mark the paper analysis task as `in_progress` using `TaskUpdate`.

Use the Agent tool to dispatch the **paper-analyst** sub-agent with the paper file path.

The paper-analyst will read the paper and produce a **paper manifest JSON** containing:
- `proof_system` — which proof system the paper uses
- `commitment_obligations` — what must be committed (non-empty array)
- `operators` — what operations are specified (non-empty array)
- `quantization` — precision requirements

**Quality gate:** Before proceeding, verify the paper manifest contains all four fields above. If the manifest is incomplete, briefly note the gaps but proceed — the code-inspector will work with what's available.

Mark the paper analysis task as `completed`. Provide a brief progress update to the user.

## Step 3: Code Audit (code-inspector)

Mark the code audit task as `in_progress` using `TaskUpdate`.

Use the Agent tool to dispatch the **code-inspector** sub-agent with:
- The paper manifest (from Step 2)
- The codebase path

The code-inspector will use the paper manifest as its verification checklist,
auditing the codebase against every claim in the paper. It produces an
**audit findings JSON** with commitment_audit, operator_coverage,
soundness_findings, protocol_transcript_findings, and precision_findings.

Mark the code audit task as `completed`. Provide a brief progress update to the user.

## Step 4: Report Generation (report-writer)

Mark the report generation task as `in_progress` using `TaskUpdate`.

Determine the `output_path` for the report file:
1. If the user specified an output path, use that.
2. Otherwise, derive a filename from the paper title or codebase name:
   - Sanitize the name: lowercase, replace spaces with hyphens, strip special chars
   - Pattern: `reports/{name}_report.md`
   - Example: `reports/zkllm_report.md`

Use the Agent tool to dispatch the **report-writer** sub-agent with:
- The paper manifest (from Step 2)
- The audit findings (from Step 3)
- The `output_path` for the report file

The report-writer will produce a Markdown report covering:
- Executive Summary
- Commitment Audit
- Operator Coverage Matrix (✅/⚠️/❌/➕)
- Soundness Findings
- Protocol Transcript Findings (if any)
- Precision Findings (if any)
- Recommendations (prioritized by severity: CRITICAL -> WARNING -> INFO)

The report-writer uses the Write tool to save the report to disk.

## Fallback

If report-writer returns the report content but could not save the file,
use the Write tool yourself to write it to `output_path`.
The report MUST be on disk before the pipeline is considered complete.

Mark the report generation task as `completed`.

## Final Summary

After the report is written:
1. **Present a summary** to the user in chat — key finding counts, most critical issue, overall assessment
2. **Confirm the file location**: tell the user where the report was saved
3. Offer to dive deeper into any section

## Communication Style

- Be precise and technical — your audience is ZK engineers
- Always cite specific files, line numbers, and code snippets
- Distinguish between "the paper says X" and "the code does Y"
- When something is ambiguous, flag it as WARNING and explain both interpretations
- Use mathematical notation where appropriate

## Security Principles

- Never execute code from the analyzed codebase
- Only read files within the user-provided paths
- Sanitize all paths before use
- Report any potential soundness vulnerabilities immediately
