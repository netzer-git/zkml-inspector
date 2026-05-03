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

**Overall Assessment**: 3 CRITICAL, 4 WARNING, 2 INFO issues found.

The most serious gap is that LayerNorm, which the paper specifies in §3.3, is
absent from the implementation entirely; the prover never produces or attests
to layer-normalized activations. The implementation also omits bias-vector
binding (§5) and leaves a non-deterministic dropout layer in the proving
path. Several smaller divergences (Softmax segment count, GELU substituted
with ReLU, lower fixed-point precision than the paper specifies) further
shift the proven function away from what the paper describes.

---

## Findings

### CRITICAL

#### LayerNorm operator missing
- **Locations:** —
- **Paper Reference:** Section 3.3 — "We normalize each token's activations
  via LayerNorm with a Newton's-method reciprocal-square-root subroutine and
  a 256-entry lookup table over the standard interval."
- **Paper says:** Each layer applies LayerNorm before the residual connection.
- **Code does:** No LayerNorm operator exists; activations flow into the next
  layer untouched.
- **Impact:** The proof attests to a model with no normalization, which a
  malicious or careless prover can exploit to substitute arbitrary
  activations.
- **Recommendation:** Implement LayerNorm to match the paper's specification.

#### Bias vectors uncommitted
- **Locations:** src/commitment.rs:30, src/model/weights.rs:72
- **Paper Reference:** Section 5 — "Prior to proving, the prover commits to
  the model parameters W = (w_i, b_i) via the Poseidon hash, producing a
  digest sent to the verifier as a public input."
- **Paper says:** Both weight matrices and bias vectors are committed.
- **Code does:** Only weight matrices are hashed; bias vectors are loaded
  from disk and never bound to the proof.
- **Impact:** A malicious prover can shift each layer's output by an
  arbitrary constant per proof without the verifier detecting it.
- **Recommendation:** Add bias vectors to the commitment construction at
  the same step where weights are hashed.

#### Dropout in proof path
- **Locations:** src/model/transformer.rs:42
- **Paper Reference:** —
- **Paper says:** *Missing paper reference — pure engineering observation.*
- **Code does:** A dropout layer with non-zero probability is still active
  in the forward pass that feeds the circuit.
- **Impact:** Non-deterministic operations make the witness unreproducible,
  so the prover can choose values that pass verification non-uniformly.
- **Recommendation:** Disable dropout in the inference / proving path.

### WARNING

#### Softmax under-segmented
- **Locations:** src/ops/softmax.rs:12
- **Paper Reference:** Section 3.2 — "Softmax is approximated by an
  8-segment piecewise-linear interpolant over the input interval [-8, 8],
  guaranteeing absolute error at most 0.01."
- **Paper says:** Softmax uses 8 piecewise-linear segments (worst-case
  error ≤ 0.01).
- **Code does:** 3 piecewise-linear segments (~0.05 error in practice).
- **Impact:** The proof attests to a coarser approximation than the
  paper's stated error bound covers.
- **Recommendation:** Increase to 8 segments and re-derive breakpoints
  from the paper's specification.

#### GELU replaced by ReLU
- **Locations:** src/ops/relu.rs:1
- **Paper Reference:** Section 3.4 — "Each MLP block uses a GELU
  activation, implemented in-circuit via a 256-entry lookup table over
  the input range [-8, 8]."
- **Paper says:** MLP blocks use GELU.
- **Code does:** GELU sites call into ReLU.
- **Impact:** ReLU encodes a different function, so the proof attests to
  a different model than the paper.
- **Recommendation:** Restore GELU using the lookup table specified.

#### Fixed-point precision low
- **Locations:** src/config.rs
- **Paper Reference:** Section 6.1 — "All experiments use 16-bit
  fixed-point arithmetic with 8 fractional bits across the entire
  inference path."
- **Paper says:** 16-bit fixed-point (8 fractional bits).
- **Code does:** 12-bit fixed-point (6 fractional bits).
- **Impact:** Lower precision propagates into Softmax and other
  operators whose error analyses assume the larger scale.
- **Recommendation:** Raise the scale to 16 bits to match the paper.

#### Range-check threshold mismatch
- **Locations:** src/range.rs
- **Paper Reference:** Section 5 — "Every intermediate value is range-checked
  against the bound 2^15 to prevent field-overflow attacks against the
  fixed-point multipliers."
- **Paper says:** Range checks bound intermediates to 2^15.
- **Code does:** Range checks bound to 2^12.
- **Impact:** A tighter bound than the paper specifies risks rejecting
  honestly-computed proofs at extreme inputs.
- **Recommendation:** Update the bound to 2^15.

### INFO

#### BatchNorm-folding opportunity
- **Locations:** —
- **Paper Reference:** —
- **Paper says:** *Missing paper reference — observational.*
- **Code does:** Linear layers do not fold any later normalization.
- **Impact:** None today (BatchNorm is not present), but worth
  documenting for future maintainers.
- **Recommendation:** If BatchNorm is added later, fold it into the
  preceding Linear layer to save gates.

#### ReLU→GELU substitution undocumented
- **Locations:** src/ops/relu.rs:1
- **Paper Reference:** Section 3.4 — "Each MLP block uses a GELU
  activation, implemented in-circuit via a 256-entry lookup table over
  the input range [-8, 8]."
- **Paper says:** MLP uses GELU.
- **Code does:** Calls ReLU instead, with no comment explaining why.
- **Impact:** Future readers will find the divergence confusing.
- **Recommendation:** If the substitution is intentional, document it
  inline with a comment that points at the relevant tradeoff.

---

## Recommendations

### Critical (Must Fix)

1. **Implement LayerNorm** — Paper §3.3 defines it; code is missing it
   entirely. Without it, the prover can substitute arbitrary normalized
   activations and the proof would still verify.
2. **Commit bias vectors** — Add bias vectors to the commitment step in
   `src/commitment.rs:30`. Otherwise the prover can shift each layer's
   output per proof.
3. **Remove dropout from the proving path** — `src/model/transformer.rs:42`.
   Non-determinism breaks witness reproducibility.

### Warning (Should Fix)

1. **Increase Softmax segments from 3 to 8** — `src/ops/softmax.rs:12` to
   match the paper's stated error bound.
2. **Restore GELU activation** — `src/ops/relu.rs` is the current site;
   add the lookup table specified in Paper §3.4.
3. **Raise fixed-point precision to 16-bit** — `src/config.rs`.
4. **Fix range-check threshold to 2^15** — `src/range.rs`.

### Info (Nice to Have)

1. **Plan for BatchNorm folding** if BatchNorm is ever added.
2. **Document the ReLU→GELU substitution** if it is intentional.

---

## Benchmark Findings (machine-readable)

A flat JSON array of every CRITICAL deduplicated finding above. The batch
step (`/analyze-batch`) parses this block, injects the manifest's
`entry-id`, and concatenates entries into `agent_output.json`.

```json
[
  {
    "issue-name": "LayerNorm operator missing",
    "issue-explanation": "The paper specifies LayerNorm in §3.3 with a Newton's-method reciprocal-square-root subroutine and a 256-entry lookup, but the implementation has no LayerNorm operator at all. The prover never produces or attests to layer-normalized activations, so a malicious party can substitute arbitrary values between layers and the proof would still verify.",
    "relevant-code": "",
    "paper-reference": "Section 3.3: \"We normalize each token's activations via LayerNorm with a Newton's-method reciprocal-square-root subroutine and a 256-entry lookup table over the standard interval.\""
  },
  {
    "issue-name": "Bias vectors uncommitted",
    "issue-explanation": "The paper commits both weight matrices and bias vectors via Poseidon (§5), but the code only hashes weight matrices and loads bias vectors from disk without binding them to the proof. An uncommitted bias lets the prover shift each layer's output by an arbitrary constant per proof, so the verifier cannot bind the proof to a fixed model.",
    "relevant-code": "src/commitment.rs:30, src/model/weights.rs:72",
    "paper-reference": "Section 5: \"Prior to proving, the prover commits to the model parameters W = (w_i, b_i) via the Poseidon hash, producing a digest sent to the verifier as a public input.\""
  },
  {
    "issue-name": "Dropout in proof path",
    "issue-explanation": "A dropout layer with non-zero probability is still active in the forward pass that feeds the circuit. Non-deterministic operations make the witness unreproducible and let the prover choose values that pass verification non-uniformly.",
    "relevant-code": "src/model/transformer.rs:42",
    "paper-reference": "-"
  }
]
```
