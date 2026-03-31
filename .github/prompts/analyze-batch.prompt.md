---
description: "Batch analysis of multiple zkML papers against their codebases from a manifest file"
agent: "batch-runner"
tools:
  - read
  - search
  - agent
  - todo
argument-hint: "manifest=<path_to_batch_manifest.json>"
---

# Batch zkML Analysis

Process multiple paper+codebase pairs from a JSON manifest file. Each analysis
runs the full zkml-inspector pipeline (paper-analyst → code-inspector →
report-writer) with isolated context.

## Instructions

1. Read the manifest JSON file at the provided path
2. Validate all paper and codebase paths exist
3. Create a timestamped output folder next to the manifest
4. For each entry, invoke zkml-inspector (full or quick mode per entry)
5. Save each report to the timestamped folder
6. Print a summary table when complete

## Resume

If interrupted, re-invoke this prompt in a fresh conversation with the same
manifest path. It will detect the incomplete run folder and skip already-completed
analyses.

## Manifest Format

```json
{
  "analyses": [
    { "name": "ezkl", "paper": "./ezkl/paper.pdf", "codebase": "./ezkl/code/" },
    { "name": "zkllm", "paper": "./zkllm/paper.tex", "codebase": "./zkllm/src/" }
  ],
  "mode": "full"
}
```

Paths are relative to the manifest file. Per-entry `mode` overrides the top-level default.
