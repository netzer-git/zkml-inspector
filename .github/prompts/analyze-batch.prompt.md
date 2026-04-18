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
summary JSON covering all analyses.

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
   paper-specific details (manifest, findings, operator lists). Carry forward
   **only**:
   - The overall batch plan (which entries remain)
   - The output directory path
   - Any skipped entries and why

   Do NOT carry forward finding counts or per-entry summaries — those will be
   re-read from the report files in Phase 2.

6. Move to the next entry.

### Phase 2 — Summary JSON

After **all** entries are complete (or skipped), generate a summary file at
`<output_dir>/summary.json`.

The summary JSON has one top-level key per analysis `entry-id`. Each key maps to
an array of **every deduplicated finding** from that report, using this schema:

```json
{
  "<entry-id>": [
    {
      "name": "1-3 word finding name",
      "severity": "Critical | Warning | Info",
      "explanation": "One sentence explaining the finding.",
      "location": "file:line — or empty string if not applicable"
    }
  ]
}
```

**Rules for the summary:**
- Read each `<entry-id>_report.md` to extract findings (do not rely on memory from
  Phase 1 — context was compacted).
- Include **all** deduplicated findings, not just criticals.
- `severity` must be exactly one of: `Critical`, `Warning`, `Info`.
- `explanation` is a single sentence — concise but self-contained.
- `location` is a code reference like `file.rs:42` or `module.cu:18-23`. Use
  an empty string `""` when no specific code location applies.
- Do NOT invent findings — only include what appears in the reports.

### Phase 3 — Final Summary Table

Print a summary table to the user:

```
| Paper    | Codebase           | Critical | Warning | Info | Total | Report                |
|----------|--------------------|----------|---------|------|-------|-----------------------|
| zkLLM    | zkllm-ccs2024      |       14 |       9 |    9 |    32 | zkllm_report.md       |
| ...      | ...                |      ... |     ... |  ... |   ... | ...                   |
```

Then confirm: "All reports saved to `<output_dir>/`. Summary at `summary.json`."

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
