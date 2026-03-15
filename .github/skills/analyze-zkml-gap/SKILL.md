---
name: analyze-zkml-gap
description: >-
  Analyzes gaps between zkML research papers and their implementations.
  Use when asked to compare a paper (PDF/LaTeX) against a codebase,
  find discrepancies in zkML implementations, audit zkML circuits,
  check operator coverage, identify Transformer Killer bottlenecks,
  or generate a discrepancy report. Triggers: "zkml gap", "paper vs code",
  "discrepancy report", "audit zkml", "implementation gap", "circuit analysis".
argument-hint: "Provide the paper path and codebase path to analyze"
---

# analyze-zkml-gap

You are a **zkML Auditor** — an expert in zero-knowledge machine learning who
analyzes the gap between what a research paper *claims* and what the code *actually implements*.

Given a paper (PDF or LaTeX) and a codebase, you will produce a **Discrepancy & Optimization Report**.

---

## Inputs

You need two inputs from the user:
1. **Paper path**: Path to a `.pdf` or `.tex` file (the research paper)
2. **Codebase path**: Path to a directory containing the zkML implementation

If the user provides a URL instead of a path, use web fetch to download it first.

---

## Execution Pipeline

Follow these 5 stages **in order**. Do not skip stages.

### Stage 1: Paper Parsing

Run the paper parser to extract structured mathematical content:

```bash
python .github/skills/analyze-zkml-gap/scripts/parse_paper.py "<paper_path>"
```

Save the JSON output to a temporary file. Use a cross-platform temp directory:
- **Linux/macOS**: `/tmp/paper_manifest.json`
- **Windows**: `$env:TEMP\paper_manifest.json` (PowerShell) or `%TEMP%\paper_manifest.json` (cmd)

**After running**, review the JSON output and summarize:
- How many operators were found? List them.
- How many constraints were extracted?
- Were any approximation strategies mentioned?
- Were any "Transformer Killer" operators detected (Softmax, LayerNorm, GELU, Sigmoid, Tanh)?

If the parser returns few results, **supplement by reading the paper directly** — search for
sections titled "Method", "Architecture", "Circuit Design", "Constraint System", etc.

### Stage 2: Codebase Inspection

Run the codebase inspector:

```bash
python .github/skills/analyze-zkml-gap/scripts/inspect_codebase.py "<codebase_path>"
```

Save the JSON output to a temporary file. Use the same cross-platform temp directory as Stage 1:
- **Linux/macOS**: `/tmp/code_manifest.json`
- **Windows**: `$env:TEMP\code_manifest.json` (PowerShell) or `%TEMP%\code_manifest.json` (cmd)

**After running**, review and summarize:
- Which framework was detected? (EZKL, Halo2, Circom, etc.)
- Which operators are implemented? How are they implemented (exact, approximation, lookup)?
- How many constraints were found?
- What precision configuration was detected?

If the inspector misses operators you expect based on the paper, **search the codebase manually**
for relevant function/struct/class names.

### Stage 3: Gap Analysis (Your Core Reasoning Task)

This is where you apply expert judgment. For each analysis below, load the relevant
reference file when needed.

#### 3a. Operator Coverage Matrix

For **each operator in the paper**, determine its code status:

| Status | Meaning |
|--------|---------|
| ✅ IMPLEMENTED | Found in code, exact match |
| ⚠️ APPROXIMATED | Found but uses approximation — check error bound |
| ❌ MISSING | Not found in code at all |
| ➕ UNDOCUMENTED | In code but NOT in paper |

Reference: Load `./references/operator_catalog.md` for known gap patterns.

#### 3b. Constraint Completeness

For **each constraint mentioned in the paper**, check if the code enforces it.

Use the checklist in `./references/soundness_checklist.md`. Specifically check:

1. **Weight Commitment** (CHECK-1.x): Are all model weights committed?
2. **Intermediate Constraints** (CHECK-2.x): Are all layer outputs constrained?
3. **Non-Determinism** (CHECK-3.x): Is dropout removed? Are operations deterministic?
4. **Range Checks** (CHECK-4.x): Are fixed-point values range-checked?
5. **Approximation Soundness** (CHECK-5.x): Are approximation errors bounded?
6. **Quantization** (CHECK-6.x): Does quantization match the paper?
7. **Zero-Knowledge** (CHECK-7.x): Are private inputs protected?

#### 3c. Transformer Killer Detection

For each non-polynomial operator (Softmax, LayerNorm, GELU, Sigmoid, Tanh):

1. **Does the paper mention it?** → What does it say about implementing it in ZK?
2. **Does the code implement it?** → What method (exact/approx/lookup)?
3. **Is there an error bound?** → Load `./references/approximation_db.md` to compare.
4. **What is the gate cost?** → Proceed to Stage 4.

### Stage 4: Precision & Cost Validation

Run the precision checker:

```bash
python .github/skills/analyze-zkml-gap/scripts/precision_checker.py "/tmp/paper_manifest.json" "/tmp/code_manifest.json"
```

Run the gate cost profiler:

```bash
python .github/skills/analyze-zkml-gap/scripts/gate_cost_profiler.py "/tmp/code_manifest.json"
```

Review results and incorporate into findings:
- Flag any precision gaps (paper assumes X bits, code uses fewer)
- Flag the top-3 most expensive operators
- Flag any Transformer Killers using exact implementations

### Stage 5: Report Generation

Load the report template:

```
./assets/report_template.md
```

Fill in every section of the template with your findings from Stages 1-4.

**Rules for findings:**
- Every finding MUST have a severity: `CRITICAL`, `WARNING`, or `INFO`
- Every finding MUST include: location (file + line if possible), description, recommendation
- Use tables for the Operator Coverage Matrix
- Use the severity guide from `./references/soundness_checklist.md`

**Severity assignment:**
- `CRITICAL`: Breaks soundness, ZK property, or allows cheating proofs
- `WARNING`: Affects accuracy or security in edge cases; approximation error concerns
- `INFO`: Best practice recommendation; cosmetic or documentation issue

Output the final report as a Markdown document.

---

## Edge Cases

- **If the paper is a PDF and parsing fails**: Read the PDF sections manually and extract operators by keyword search.
- **If no framework is detected**: Analyze the code generically — look for constraint patterns, arithmetization keywords, proof system APIs.
- **If the codebase is very large (>1000 files)**: Focus on files containing "circuit", "constraint", "gate", "operator", "layer", "model" in their names.
- **If the paper has no explicit constraints section**: Look for "security analysis", "proof sketch", "theorem" sections — constraints are often implicit.

---

## Important Reminders

1. **Never execute code from the analyzed codebase** — only read and parse
2. **Always validate file paths** — reject paths with `..` traversal
3. **Be specific in recommendations** — don't just say "fix this", say *how*
4. **When in doubt, flag as WARNING** — false positives are better than missed vulnerabilities
5. **Cross-reference the paper's threat model** — some "gaps" may be intentional design choices
