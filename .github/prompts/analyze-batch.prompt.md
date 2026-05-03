---
description: "Batch analysis of multiple zkML papers against their codebases from a manifest file"
agent: "zkml-inspector"
tools:
  - read
  - search
  - agent
  - todo
  - createFile
  - pdf-reader/read_pdf
argument-hint: "manifest=<absolute_path_to_batch_manifest.json>"
---

# Batch zkML Gap Analysis

You are performing a **batch analysis** of multiple zkML paper+codebase pairs
defined in a JSON manifest file. For each entry you run the full zkml-inspector
pipeline (`paper-analyst → code-inspector → report-writer`), then produce a
flat benchmark JSON aggregating every report's CRITICAL findings.

## Manifest Format

The manifest is a JSON file with this structure:

```json
{
  "analyses": [
    {
      "entry-id": "zkllm",
      "paper": "./Papers/zkLLM.pdf",
      "codebase": "./Codebases/zkllm-ccs2024/"
    }
  ],
  "output_dir": "./Batch-Reports/v0.1"
}
```

- `analyses` — array of entries, each with `entry-id`, `paper`, `codebase`
- `output_dir` — output folder for reports, relative to the manifest file
- All paths inside the manifest are **relative to the manifest file's location**

## Execution Plan

### Phase 0 — Setup

1. Read the manifest JSON at the user-provided path.
2. Resolve all `paper` and `codebase` paths relative to the manifest directory.
3. Resolve `output_dir` relative to the manifest directory; **create it** if it
   does not exist.
4. Validate that every paper file and codebase directory exists. List any
   missing paths and skip those entries (do not abort the batch).
5. Use the todo list to track progress across all entries.

### Phase 1 — Sequential Analysis (one entry at a time)

For **each** entry in the `analyses` array, in order:

1. **Check for existing report** — if `<output_dir>/<entry-id>_report.md` already
   exists, **skip** this entry and log "Skipping <entry-id> — report already exists".

2. **Print progress** — e.g., `[1/4] Analyzing: zkllm`

3. **Run the full analysis** — Execute the `/analyze-full` workflow for this
   entry, providing:
   - `paper` = the entry's absolute paper path
   - `codebase` = the entry's absolute codebase path
   - `output_path` = `<output_dir>/<entry-id>_report.md`

   This runs the standard `paper-analyst → code-inspector → report-writer`
   pipeline as defined in `analyze-full.prompt.md`. Do NOT duplicate the
   pipeline logic here — follow `analyze-full` exactly.

4. **Confirm** the report file was written. If report-writer could not write
   it, write the report yourself using `createFile`.

5. **Context compaction** — After finishing each entry, mentally discard the
   paper-specific details (manifest, findings). Carry forward **only**:
   - The overall batch plan (which entries remain)
   - The output directory path
   - Any skipped entries and why

   Do NOT carry forward finding counts or per-entry summaries — those will be
   re-read from the report files in Phase 2.

6. Move to the next entry.

### Phase 2 — Benchmark JSON

After **all** entries are complete (or skipped), generate a single flat
output file at `<output_dir>/agent_output.json` for Critical findings only.

**Procedure:**

1. For each completed entry, read its `<output_dir>/<entry-id>_report.md`.
2. Locate the trailing **Benchmark Findings (machine-readable)** fenced
   JSON code block at the end of the report. Parse it as JSON.
3. For each Critical finding object in that array, inject `"entry-id":
   "<entry-id>"` (use the manifest key verbatim, preserving casing).
   The result is an object with **all 5 required fields**:

   | Field | Source |
   |-------|--------|
   | `entry-id` | Manifest key for this entry |
   | `issue-name` | From the report's Benchmark Findings block |
   | `issue-explanation` | From the report's Benchmark Findings block |
   | `relevant-code` | Comma-separated `file:line` references, or `""` |
   | `paper-reference` | Section + optional quote, or `"-"` |

4. **Validate** every finding before adding it to the output array:
   - All 5 keys present and non-null (empty string is allowed for
     `relevant-code` only).

   On validation failure: log the offending `entry-id` and finding
   `issue-name`, then **omit that finding** from the output. Do NOT
   silently coerce. Do NOT abort the whole batch.

5. **Sort** the final array deterministically for stable diffs:
   - Primary key: `entry-id` (case-insensitive ASCII order).
   - Secondary key: `issue-name` (case-insensitive ASCII order).

6. Write the resulting flat JSON array to `<output_dir>/agent_output.json`
   using `createFile` (pretty-printed with 2-space indent, UTF-8).

7. Do NOT also write the legacy per-entry summary file — that format is
   removed; only the flat benchmark-schema array is produced.

**Schema reminder — the file is a flat array:**

```json
[
  {
    "entry-id": "zkllm",
    "issue-name": "Model Binding",
    "issue-explanation": "...",
    "relevant-code": "proof.cu:3",
    "paper-reference": "Section 3.3: \"...\""
  }
]
```

You should NEVER include any findings from Warning or Info categories in this output — only Critical findings are benchmarked.
Part of the report-writer agent is to filter out non-Critical findings from the benchmark JSON block, so if you see any Warning or Info findings in that block, remove it.

### Phase 3 — Final Summary Table

Print a summary table to the user:

```
| Paper    | Codebase           | Critical | Warning | Info | Total | Report                |
|----------|--------------------|----------|---------|------|-------|-----------------------|
| zkLLM    | zkllm-ccs2024      |       14 |       9 |    9 |    32 | zkllm_report.md       |
| ...      | ...                |      ... |     ... |  ... |   ... | ...                   |
```

Then confirm: "All reports saved to `<output_dir>/`. Benchmark output at `agent_output.json`."

## Important Constraints

- **Isolation**: Each paper analysis must be independent. Never use findings
  from one paper to inform the analysis of another.
- **Reports next to manifest**: Write all output to the manifest's `output_dir`,
  NOT inside the zkml-inspector workspace. This prevents code-inspector from
  picking up past report text during codebase searches.
- **No code execution**: Only read and parse files from target codebases. Never
  execute code.
- **Resume**: Skip entries whose report file already exists. This allows
  resuming an interrupted batch by re-invoking with the same manifest.
- **One at a time**: Do NOT parallelize analyses. Run them strictly sequentially
  so each sub-agent gets a clean context.
