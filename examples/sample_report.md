# zkML Gap Analysis Report

<!-- NOTE: This is a sample report for illustration purposes.
     All file paths (e.g., src/ops/matmul.rs) are fictional and do not
     correspond to actual files in this repository. -->

> **Paper**: Efficient Zero-Knowledge Proofs for Neural Network Inference
> **Codebase**: ./example-zkml-project/
> **Date**: 2026-03-14
> **Analyzer**: zkml-inspector v0.1.0

---

## Executive Summary

**Overall Assessment**: 3 CRITICAL, 4 WARNING, 2 INFO issues found

The implementation is missing LayerNorm constraints entirely (CRITICAL), uses a 3-segment
piecewise-linear Softmax approximation instead of the paper's specified 8 segments (WARNING),
and does not commit bias vectors (CRITICAL). The GELU activation uses ReLU as a drop-in
replacement — a significant behavioral change not documented in the paper.

| Metric | Value |
|--------|-------|
| Operators in paper | 6 |
| Operators in code | 5 |
| Coverage | 83% |
| Missing operators | 1 (LayerNorm) |
| Critical issues | 3 |
| Warnings | 4 |

---

## 1. Operator Coverage Matrix

| # | Operator | Paper | Code | Status | Implementation | Notes |
|---|----------|-------|------|--------|----------------|-------|
| 1 | MatMul | §3.1 | src/ops/matmul.rs:45 | ✅ IMPLEMENTED | exact | Standard MAC constraints |
| 2 | Softmax | §3.2 | src/ops/softmax.rs:12 | ⚠️ APPROXIMATED | piecewise-linear | 3 segments vs paper's 8 |
| 3 | LayerNorm | §3.3 | — | ❌ MISSING | — | Not implemented at all |
| 4 | GELU | §3.4 | src/ops/relu.rs:1 | ⚠️ APPROXIMATED | ReLU substitute | Replaced with ReLU |
| 5 | ReLU | §3.5 | src/ops/relu.rs:30 | ✅ IMPLEMENTED | exact | Sign decomposition |
| 6 | Attention | §2 | src/model/attention.rs:88 | ✅ IMPLEMENTED | composite | Uses Softmax internally |

---

## 2. Commitment Audit

### 2.1 Missing Commitments

| # | Severity | Value | Paper Location | Expected Commitment | Status |
|---|----------|-------|----------------|---------------------|--------|
| 1 | CRITICAL | Bias vectors | §5, para 2 | Poseidon hash in src/commitment.rs | Not committed |
| 2 | WARNING | Intermediate activations | §5, para 3 | Binding commitment after each layer | Partial — only final output committed |

---

## 3. Soundness Findings

### 3.1 Missing Constraints

| # | Severity | Constraint | Paper Location | Expected in Code | Status |
|---|----------|-----------|----------------|-------------------|--------|
| 1 | CRITICAL | Weight commitment via Poseidon hash | §5, para 2 | src/commitment.rs | Missing for bias vectors |
| 2 | CRITICAL | Intermediate activation constraints | §5, para 3 | src/circuit.rs | Missing for LayerNorm output |
| 3 | WARNING | Range check on all intermediates | §5, para 4 | src/range.rs | Present but threshold is 2^12 not 2^15 |

### 3.2 Wire Disconnect

| # | Severity | Finding | Location(s) | Description | Recommendation |
|---|----------|---------|-------------|-------------|----------------|
| 1 | CRITICAL | Wire disconnect between layer 2 and layer 3 | src/layers/linear.rs:120, src/layers/norm.rs:15 | Layer 2 output (linear.rs) uses wire w_42 but layer 3 input (norm.rs) reads from w_99. Prover can substitute arbitrary values between layers. | Add copy constraint: w_42 === w_99 |

### 3.3 Non-Deterministic Operations

| # | Severity | Operation | Location(s) | Issue |
|---|----------|-----------|-------------|-------|
| 1 | WARNING | Dropout | src/model/transformer.rs:42 | Dropout still present in forward pass |

### 3.4 Unconstrained Intermediate Values

- LayerNorm output is unconstrained — a prover could substitute arbitrary normalized values
- This allows a "layer-skipping attack" where the prover skips normalization entirely

---

## 4. Precision Findings

### 4.1 Fixed-Point Configuration

| Parameter | Paper | Code | Match? |
|-----------|-------|------|--------|
| Scale bits | 16-bit (8 fractional) | 12-bit (6 fractional) | ❌ |
| Quantization method | Symmetric per-tensor | Symmetric per-tensor | ✅ |
| Field size | Not specified | BN254 (254-bit prime) | ✅ |

### 4.2 Precision Gaps

| # | Severity | Operator | Required Bits | Actual Bits | Gap | Recommendation |
|---|----------|----------|---------------|-------------|-----|----------------|
| 1 | CRITICAL | Softmax | ≥16 | 12 | -4 | Increase to 16-bit; Softmax exp() is sensitive to precision |
| 2 | WARNING | GELU | ≥14 | 12 | -2 | Increase to 14-bit if GELU is restored (currently using ReLU) |
| 3 | WARNING | MatMul | ≥10 | 12 | +2 | Sufficient — no action needed |

---

## 5. Protocol Transcript Findings

### 5.1 Critical Soundness Issues

| # | Check | Status | Location(s) | Description | Recommendation |
|---|-------|--------|-------------|-------------|----------------|
| 1 | CHECK-1.1 | ❌ FAIL | src/commitment.rs:30, src/model/weights.rs:72 | Bias vectors not committed — weight commitment in commitment.rs omits biases, and weight loading in weights.rs skips bias registration | Add bias commitment alongside weight commitment |
| 2 | CHECK-2.1 | ❌ FAIL | — | LayerNorm output unconstrained (entire operator missing) | Implement LayerNorm constraints |
| 3 | CHECK-3.1 | ❌ FAIL | src/model/transformer.rs:42 | Dropout present | Remove dropout for inference mode |

### 5.2 Zero-Knowledge Property

| # | Check | Status | Description |
|---|-------|--------|-------------|
| 1 | CHECK-7.1 | ✅ PASS | Private inputs not exposed in public output |
| 2 | CHECK-7.2 | ✅ PASS | Proof system (Plonk) provides computational ZK |

---

## 6. Algorithmic Critiques

### 6.1 Potential Soundness Risks in Paper's Math

- **Theorem 1 (Soundness)**: The proof sketch references the discrete log assumption but
  does not formally reduce the circuit soundness to DL. This is a proof gap — the claim
  may be correct but is not rigorously established.
- **Approximation error**: The paper claims ε ≤ 0.01 for Softmax but does not prove this
  bound holds under fixed-point quantization (only for real-valued computation).

### 6.2 Missing Security Analysis

- No analysis of how approximation error affects the soundness guarantee
- No extraction proof (needed for knowledge-soundness, not just soundness)
- No discussion of malleability — can a valid proof be transformed into another valid proof?

---

## 7. Recommendations

### Critical (Must Fix)

1. **Implement LayerNorm** — Paper defines it in §3.3 but code is missing it entirely
   - **Location**: Should be added to src/ops/
   - **Action**: Implement using Newton's method (3 iterations) for 1/√x + lookup table (256 entries) as specified in paper
   - **Impact**: Without this, the prover can skip normalization — breaks model correctness

2. **Commit bias vectors** — All weight+bias parameters must be Poseidon-committed
   - **Location(s)**: src/commitment.rs:30, src/commitment.rs:58
   - **Action**: Add bias vectors to the commitment tree alongside weight matrices
   - **Impact**: Prover can shift all layer outputs by arbitrary constants

3. **Remove dropout** — Non-deterministic operation breaks proof validity
   - **Location**: src/model/transformer.rs:42
   - **Action**: Set dropout probability to 0 or remove the dropout layer for inference
   - **Impact**: Proof may be invalid or non-reproducible

### Warnings (Should Fix)

1. **Increase Softmax segments from 3 to 8** — Paper specifies K=8 for ε ≤ 0.01
   - **Location**: src/ops/softmax.rs:12
   - **Action**: Add 5 more piecewise-linear segments; update breakpoints and slopes

2. **Restore GELU activation** — Currently replaced with ReLU, changing model behavior
   - **Location**: src/ops/relu.rs
   - **Action**: Implement GELU via lookup table as specified in paper §3.4

3. **Increase fixed-point precision from 12 to 16 bits** — Paper specifies 16-bit
   - **Location**: src/config.rs
   - **Action**: Update SCALE constant and all range check bounds

4. **Fix range check threshold** — Code uses 2^12, paper specifies 2^15
   - **Location**: src/range.rs
   - **Action**: Update range check bounds to match paper

### Informational (Nice to Have)

1. **Fold BatchNorm into preceding Linear** — If BatchNorm is added later, fold it to save gates
2. **Document the ReLU→GELU substitution** — If intentional, add a comment explaining the tradeoff

---

## 8. Benchmark Findings (machine-readable)

A flat JSON array of every deduplicated finding above, in the
zkML-inspector-benchmark schema. The batch step (`/analyze-batch`) parses
this block, injects the manifest's `entry-id`, and concatenates entries
into `agent_output.json`.

```json
[
  {
    "issue-name": "LayerNorm Missing",
    "issue-explanation": "The paper specifies LayerNorm in §3.3 with Newton's-method reciprocal square root and a 256-entry lookup, but the implementation has no LayerNorm operator at all. Without normalization constraints, a malicious prover can skip the layer entirely and substitute arbitrary normalized values, breaking the inference relation the verifier accepts.",
    "severity": "Critical",
    "category": "Specification Mismatch",
    "security-concern": "Semantic Subversion (Integrity)",
    "relevant-code": "",
    "paper-reference": "Section 3.3"
  },
  {
    "issue-name": "Bias vectors uncommitted",
    "issue-explanation": "The paper commits weights via Poseidon (§5) but the implementation only commits weight matrices, never bias vectors. An uncommitted bias lets the prover shift each layer's output by an arbitrary constant per proof, so the verifier cannot bind the proof to a fixed model.",
    "severity": "Critical",
    "category": "Witness/Commitment Mismatch",
    "security-concern": "Semantic Subversion (Integrity)",
    "relevant-code": "src/commitment.rs:30, src/model/weights.rs:72",
    "paper-reference": "Section 5"
  },
  {
    "issue-name": "Dropout in proof path",
    "issue-explanation": "A dropout layer with non-zero probability is still active in the forward pass that feeds the circuit. Non-deterministic operations make the witness unreproducible and let the prover choose values that pass verification non-uniformly.",
    "severity": "Critical",
    "category": "Under-constrained Circuit",
    "security-concern": "Proof Forgery (Soundness)",
    "relevant-code": "src/model/transformer.rs:42",
    "paper-reference": "-"
  },
  {
    "issue-name": "Softmax under-segmented",
    "issue-explanation": "The paper specifies an 8-segment piecewise-linear Softmax with worst-case error 0.01, but the code uses only 3 segments (~0.05 error). The proof attests to a coarser approximation than the paper's stated bound covers.",
    "severity": "Warning",
    "category": "Numerical/Quantization Bug",
    "security-concern": "Semantic Subversion (Integrity)",
    "relevant-code": "src/ops/softmax.rs:12",
    "paper-reference": "Section 3.2: \"K = 8 piecewise-linear segments yield epsilon <= 0.01.\""
  },
  {
    "issue-name": "GELU replaced by ReLU",
    "issue-explanation": "The paper's GELU activation (§3.4) is implemented as a ReLU drop-in. ReLU is exact and cheaper but encodes a different function, so the proof attests to a different model than the paper claims.",
    "severity": "Warning",
    "category": "Specification Mismatch",
    "security-concern": "Semantic Subversion (Integrity)",
    "relevant-code": "src/ops/relu.rs:1",
    "paper-reference": "Section 3.4"
  },
  {
    "issue-name": "Fixed-point precision low",
    "issue-explanation": "The paper specifies 16-bit fixed-point with 8 fractional bits; the code uses 12-bit with 6 fractional bits. The 4-bit precision gap propagates into Softmax and other normalizations whose error analyses assume the larger scale.",
    "severity": "Warning",
    "category": "Numerical/Quantization Bug",
    "security-concern": "Semantic Subversion (Integrity)",
    "relevant-code": "src/config.rs",
    "paper-reference": "Section 6.1"
  }
]
```
