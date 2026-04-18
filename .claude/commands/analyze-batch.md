# Batch zkML Gap Analysis

Perform a **batch analysis** of multiple zkML paper+codebase pairs defined in
a JSON manifest file. For each entry, run the full pipeline
(`paper-analyst -> code-inspector -> report-writer`), then produce a summary
JSON covering all analyses.

## Input

$ARGUMENTS

The user should provide an absolute path to a `batch_manifest.json` file, e.g.:
`manifest=<absolute_path_to_batch_manifest.json>`

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

## Phase 0 — Setup

1. Read the manifest JSON at the user-provided path.
2. Resolve all `paper` and `codebase` paths relative to the manifest directory.
3. Resolve `output_dir` relative to the manifest directory; **create it** if it
   does not exist.
4. Validate that every paper file and codebase directory exists. List any
   missing paths and skip those entries (do not abort the batch).
5. **Create tasks** — Use the `TaskCreate` tool to create a task list for the
   batch run. Create one task per valid analysis entry (subject format:
   `Analyze <entry-id> (<i>/<n>)`, e.g. `Analyze zkllm (1/4)`), plus one task
   for `Generate summary.json` and one for `Print final summary table`.
   Set up `addBlockedBy` dependencies so each analysis task is blocked by the
   previous one, the summary task is blocked by all analysis tasks, and the
   final table task is blocked by the summary task. Mark skipped entries'
   tasks as `completed` immediately with a note in the description.

## Phase 1 — Sequential Analysis (one entry at a time)

Process entries strictly sequential — do NOT parallelize analyses. Run them
one at a time so each sub-agent gets a clean context.

For **each** entry in the `analyses` array, in order:

1. **Check for existing report** — if `<output_dir>/<entry-id>_report.md` already
   exists, **skip** this entry and log "Skipping <entry-id> — report already exists".
   Mark its task as `completed` (description: "Skipped — report already exists").
   This enables resume: re-invoking with the same manifest after an interrupted
   batch will pick up where it left off.

2. **Mark task in_progress** — Use `TaskUpdate` to set this entry's task
   status to `in_progress`.

3. **Print progress** — e.g., `[1/4] Analyzing: zkllm`

4. **Run the full analysis** — Execute the `/analyze-full` workflow for this
   entry, providing:
   - `paper` = the entry's absolute paper path
   - `codebase` = the entry's absolute codebase path
   - `output_path` = `<output_dir>/<entry-id>_report.md`

   This runs the standard `paper-analyst → code-inspector → report-writer`
   pipeline as defined in `.claude/commands/analyze-full.md`. Do NOT duplicate
   the pipeline logic here — read and follow `analyze-full.md` exactly. The
   paper-analyst uses `mcp__pdf-reader__read_pdf` for PDF files. The
   report-writer uses the Write tool to save the report.

5. **Confirm** the report file was written. If report-writer could not write
   it, use the Write tool yourself to save the report.

6. **Mark task completed** — Use `TaskUpdate` to set this entry's task status
   to `completed`.

7. **Context compaction** — After finishing each entry, mentally discard the
   paper-specific details (manifest, findings, operator lists). Carry forward
   **only**:
   - The overall batch plan (which entries remain)
   - The output directory path
   - Any skipped entries and why

   Do NOT carry forward finding counts or per-entry summaries — those will be
   re-read from the report files in Phase 2.

6. Move to the next entry.

## Phase 2 — Summary JSON

Mark the `Generate summary.json` task as `in_progress` using `TaskUpdate`.

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

Use the Write tool to save summary.json to disk.

Mark the `Generate summary.json` task as `completed`.

## Phase 3 — Final Summary Table

Mark the `Print final summary table` task as `in_progress` using `TaskUpdate`.

Print a summary table to the user:

```
| Paper    | Codebase           | Critical | Warning | Info | Total | Report                |
|----------|--------------------|----------|---------|------|-------|-----------------------|
| zkLLM    | zkllm-ccs2024      |       14 |       9 |    9 |    32 | zkllm_report.md       |
| ...      | ...                |      ... |     ... |  ... |   ... | ...                   |
```

Then confirm: "All reports saved to `<output_dir>/`. Summary at `summary.json`."

Mark the `Print final summary table` task as `completed`.

## Important Constraints

- **Isolation**: Each paper analysis must be independent. Never use findings
  from one paper to inform the analysis of another.
- **Reports outside workspace**: Write all output to the manifest's `output_dir`,
  NOT inside the zkml-inspector workspace. This prevents code-inspector from
  picking up past report text during codebase searches.
- **No code execution**: Only read and parse files from target codebases. Never
  execute code.
- **Resume**: Skip entries whose report file already exists. This allows
  resuming an interrupted batch by re-invoking with the same manifest.
- **Sequential only**: Do NOT parallelize analyses. Run them strictly one at a
  time so each sub-agent gets a clean context.
- **No memory:** Sub-agents must not create agent memory files. If any
  `.claude/agent-memory/` files are created during a run, delete them after
  the batch completes to ensure no traces remain.
- **No scripts:** Sub-agents must only use their declared tools. Never approve
  Bash or python tool calls from sub-agents.
- **Inline data passing:** Always pass the paper manifest and audit findings
  as JSON content directly in sub-agent prompts — never as file path references.
