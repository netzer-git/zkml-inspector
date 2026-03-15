# zkML Discrepancy & Optimization Report

<!-- TEMPLATE USAGE: Replace all {{PLACEHOLDER}} tokens with actual values.
     These are filled in by the zkml-inspector agent during Stage 5 (Report Generation).
     Do not use this template directly — it is consumed by the LLM agent. -->

> **Paper**: {{PAPER_TITLE}}
> **Codebase**: {{CODEBASE_PATH}}
> **Framework**: {{FRAMEWORK_NAME}} ({{FRAMEWORK_LANGUAGE}})
> **Date**: {{DATE}}
> **Analyzer**: zkml-inspector v0.1.0

---

## Executive Summary

**Overall Assessment**: {{OVERALL_ASSESSMENT — e.g., "3 CRITICAL, 5 WARNING, 2 INFO issues found"}}

{{2-3 sentence summary of the most important findings. Lead with the most critical issue.}}

| Metric | Value |
|--------|-------|
| Operators in paper | {{N}} |
| Operators in code | {{M}} |
| Coverage | {{M/N × 100}}% |
| Missing operators | {{MISSING_COUNT}} |
| Transformer Killers | {{KILLER_COUNT}} |
| Total estimated gates | {{TOTAL_GATES}} |
| Critical issues | {{CRITICAL_COUNT}} |
| Warnings | {{WARNING_COUNT}} |

---

## 1. Operator Coverage Matrix

| # | Operator | Paper | Code | Status | Implementation | Notes |
|---|----------|-------|------|--------|----------------|-------|
| 1 | {{OP_NAME}} | {{PAPER_SECTION}} | {{CODE_FILE:LINE}} | ✅/⚠️/❌/➕ | exact/approx/lookup | {{NOTES}} |

**Legend:**
- ✅ IMPLEMENTED — exact match between paper and code
- ⚠️ APPROXIMATED — implemented with approximation; verify error bound
- ❌ MISSING — defined in paper but not found in code
- ➕ UNDOCUMENTED — found in code but not described in paper

---

## 2. Logic Gaps

### 2.1 Missing Constraints

| # | Severity | Constraint | Paper Location | Expected in Code | Status |
|---|----------|-----------|----------------|-------------------|--------|
| 1 | {{SEVERITY}} | {{DESCRIPTION}} | {{PAPER_LOC}} | {{EXPECTED_FILE}} | Missing/Partial |

### 2.2 Non-Deterministic Operations

| # | Severity | Operation | File | Line | Issue |
|---|----------|-----------|------|------|-------|
| 1 | {{SEVERITY}} | {{OP_NAME}} | {{FILE}} | {{LINE}} | {{DESCRIPTION}} |

### 2.3 Unconstrained Intermediate Values

{{List any layer outputs that are not constrained — these allow proof cheating.}}

---

## 3. Precision Analysis

### 3.1 Fixed-Point Configuration

| Parameter | Paper | Code | Match? |
|-----------|-------|------|--------|
| Scale bits | {{PAPER_BITS}} | {{CODE_BITS}} | ✅/❌ |
| Quantization method | {{PAPER_METHOD}} | {{CODE_METHOD}} | ✅/❌ |
| Field size | {{PAPER_FIELD}} | {{CODE_FIELD}} | ✅/❌ |

### 3.2 Precision Gaps

| # | Severity | Operator | Required Bits | Actual Bits | Gap | Recommendation |
|---|----------|----------|---------------|-------------|-----|----------------|
| 1 | {{SEVERITY}} | {{OP}} | {{REQ}} | {{ACTUAL}} | {{DIFF}} | {{REC}} |

---

## 4. Performance Bottlenecks

### 4.1 Gate Cost Summary

| # | Operator | Implementation | Est. Gates | % of Total | Severity |
|---|----------|----------------|------------|------------|----------|
| 1 | {{OP}} | {{IMPL_TYPE}} | {{GATES}} | {{PCT}}% | {{SEV}} |

**Total Estimated Gates**: {{TOTAL}} ({{ASSESSMENT — e.g., "moderate, proving time ~5s on GPU"}})

### 4.2 Transformer Killer Analysis

| Operator | Paper Specifies | Code Uses | Cost (exact) | Cost (current) | Savings if Optimized |
|----------|-----------------|-----------|-------------|----------------|----------------------|
| {{OP}} | {{PAPER_SPEC}} | {{CODE_IMPL}} | {{EXACT_COST}} | {{CURRENT_COST}} | {{SAVINGS}} |

{{For each Transformer Killer, explain the gap between paper and code, and recommend an optimization strategy.}}

---

## 5. Soundness & Zero-Knowledge Risks

### 5.1 Critical Soundness Issues

| # | Check | Status | Location | Description | Recommendation |
|---|-------|--------|----------|-------------|----------------|
| 1 | CHECK-{{N}} | ❌ FAIL | {{FILE:LINE}} | {{DESC}} | {{REC}} |

### 5.2 Zero-Knowledge Property

| # | Check | Status | Description |
|---|-------|--------|-------------|
| 1 | CHECK-7.{{N}} | ✅/❌ | {{DESC}} |

---

## 6. Algorithmic Critiques

{{This section contains higher-level critiques of the paper's mathematical approach itself — not just the implementation gap.}}

### 6.1 Potential Soundness Risks in Paper's Math

{{Identify any mathematical claims that seem unsupported, proofs with gaps, or assumptions that may not hold.}}

### 6.2 Missing Security Analysis

{{Note any aspects of the system that the paper does not analyze for security (e.g., no discussion of extraction, no analysis of approximation error on soundness).}}

---

## 7. Recommendations

### Critical (Must Fix)

1. **{{TITLE}}** — {{ONE_SENTENCE}}
   - **Location**: {{FILE:LINE}}
   - **Action**: {{SPECIFIC_STEPS}}
   - **Impact**: {{WHAT_HAPPENS_IF_NOT_FIXED}}

### Warnings (Should Fix)

1. **{{TITLE}}** — {{ONE_SENTENCE}}
   - **Location**: {{FILE:LINE}}
   - **Action**: {{SPECIFIC_STEPS}}

### Informational (Nice to Have)

1. **{{TITLE}}** — {{ONE_SENTENCE}}

---

## Appendix

### A. Paper Manifest (Parsed)

```json
{{PAPER_JSON}}
```

### B. Codebase Manifest (Parsed)

```json
{{CODE_JSON}}
```

### C. Files Analyzed

{{LIST_OF_FILES_SCANNED}}
