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
pipeline (`paper-analyst → code-inspector → report-writer`). The report-writer
directly updates `agent_output.json` after each entry — no post-processing
phase is needed.

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
- `output_dir` — output folder for agent_output.json, relative to the manifest file
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

1. **Check for completed entry** — read `<output_dir>/completed_entries.json`
   (if it exists). If this entry's `entry-id` is listed, **skip** this entry
   and log "Skipping <entry-id> — already completed". This enables resume:
   re-invoking with the same manifest after an interrupted batch will pick up
   where it left off.

2. **Print progress** — e.g., `[1/4] Analyzing: zkllm`

3. **Run the full analysis** — Execute the `/analyze-full` workflow for this
   entry, providing:
   - `paper` = the entry's absolute paper path
   - `codebase` = the entry's absolute codebase path
   - `entry_id` = the entry's `entry-id` from the manifest (verbatim,
     preserving casing)
   - `output_path` = `<output_dir>/agent_output.json`

   This runs the standard `paper-analyst → code-inspector → report-writer`
   pipeline as defined in `analyze-full.prompt.md`. Do NOT duplicate the
   pipeline logic here — follow `analyze-full` exactly.

   The report-writer will:
   - Filter to CRITICAL-severity findings only
   - Deduplicate by root cause
   - Merge findings into `agent_output.json` (replacing any prior findings
     for this entry-id)
   - Update `completed_entries.json` sidecar

4. **Confirm** findings were written. If report-writer could not write the
   file, write the JSON yourself using `createFile`.

5. **Context compaction** — After finishing each entry, mentally discard the
   paper-specific details (manifest, findings, operator lists). Carry forward
   **only**:
   - The overall batch plan (which entries remain)
   - The output directory path
   - Any skipped entries and why

   Do NOT carry forward finding counts or per-entry details.

6. Move to the next entry.

### Phase 2 — Completion

After all entries are complete (or skipped):

1. Confirm: "All entries processed. Findings saved to
   `<output_dir>/agent_output.json`."
2. Report how many entries were analyzed vs skipped.

## Important Constraints

- **Isolation**: Each paper analysis must be independent. Never use findings
  from one paper to inform the analysis of another.
- **Output next to manifest**: Write all output to the manifest's `output_dir`,
  NOT inside the zkml-inspector workspace. This prevents code-inspector from
  picking up past output during codebase searches.
- **No code execution**: Only read and parse files from target codebases. Never
  execute code.
- **Resume**: Skip entries listed in `completed_entries.json`. This allows
  resuming an interrupted batch by re-invoking with the same manifest.
- **One at a time**: Do NOT parallelize analyses. Run them strictly sequentially
  so each sub-agent gets a clean context.
