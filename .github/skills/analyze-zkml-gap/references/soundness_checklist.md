# zkML Soundness & Zero-Knowledge Checklist

A systematic checklist for verifying that a zkML implementation preserves
the soundness and zero-knowledge properties claimed in the paper.

---

## 1. Model Integrity (Weight Commitment)

### ✅ CHECK-1.1: All model weights are committed
- **What**: Every weight matrix, bias vector, and embedding table must be committed
  (hashed or included as public/instance values in the circuit)
- **Why**: Without commitment, the prover can substitute arbitrary weights — they could
  use a completely different model than claimed
- **Severity**: CRITICAL
- **How to verify**: Search for all parameter tensors in the model definition; confirm
  each has a corresponding commitment or instance column in the circuit
- **Common gap**: Bias vectors omitted from commitment (seems minor but allows the prover
  to shift all outputs)

### ✅ CHECK-1.2: Weight commitment uses collision-resistant hash
- **What**: The commitment scheme (Pedersen, Poseidon, SHA-256) must be collision-resistant
- **Why**: A weak hash allows the prover to find different weights that produce the same commitment
- **Severity**: CRITICAL
- **How to verify**: Identify the hash function used; check it's a standard, secure choice

### ✅ CHECK-1.3: Weight loading matches commitment order
- **What**: The order in which weights are loaded into the circuit must match the
  commitment order
- **Why**: Mismatched ordering could silently permute weights between layers
- **Severity**: WARNING
- **How to verify**: Trace the weight serialization and commitment pipeline

---

## 2. Intermediate Value Constraints

### ✅ CHECK-2.1: All intermediate activations are constrained
- **What**: Every layer's output must be constrained to equal the correct computation
  of that layer's function applied to its input
- **Why**: Without constraints, the prover can skip layers or substitute arbitrary
  intermediate values
- **Severity**: CRITICAL
- **How to verify**: For each layer in the model, find the constraint that enforces
  `output = f(input, weights)`

### ✅ CHECK-2.2: No unconstrained wires between layers
- **What**: The output wire of layer N must be the same wire as the input to layer N+1
- **Why**: Disconnected wires allow the prover to use different values for a layer's
  output and the next layer's input
- **Severity**: CRITICAL
- **How to verify**: Trace wire connectivity through the circuit; check for copy constraints

### ✅ CHECK-2.3: Final output is an instance (public) value
- **What**: The circuit's output must be exposed as a public/instance value so the
  verifier can read it
- **Why**: If the output is private, the prover can claim any result
- **Severity**: CRITICAL
- **How to verify**: Check that the last layer's output is assigned to an instance column

---

## 3. Non-Determinism Elimination

### ✅ CHECK-3.1: No dropout or random sampling in the circuit
- **What**: Dropout, random masking, stochastic depth, and similar techniques must be
  removed for ZK inference
- **Why**: Randomness breaks proof determinism — the same input must always produce
  the same output
- **Severity**: CRITICAL
- **How to verify**: Search for dropout, random, sample, stochastic in the codebase

### ✅ CHECK-3.2: No floating-point non-determinism
- **What**: Operations like parallel reduction (sum, mean) must be ordered deterministically
- **Why**: Floating-point addition is not associative — different orderings give different results
- **Severity**: WARNING (in fixed-point this is usually fine)
- **How to verify**: Check if any operations depend on execution order; verify fixed-point
  arithmetic is used

### ✅ CHECK-3.3: No data-dependent branching without constraints
- **What**: If the circuit has conditional logic (if/else based on data values),
  both branches must be evaluated and the selection constrained
- **Why**: In ZK, the prover could take either branch regardless of the condition
- **Severity**: CRITICAL
- **How to verify**: Search for conditional gates; verify the condition variable is constrained

---

## 4. Range Checks & Overflow Prevention

### ✅ CHECK-4.1: Fixed-point multiplication has range checks
- **What**: After each multiplication in fixed-point arithmetic, the result must be
  checked to fit within the field
- **Why**: Overflow wraps around the field modulus — produces silently wrong results
- **Severity**: CRITICAL
- **How to verify**: For each multiplication gate, check for a subsequent range check
  or truncation constraint

### ✅ CHECK-4.2: Accumulation operations have overflow guards
- **What**: MatMul, Conv2D, sum, mean — operations that accumulate many values —
  must have intermediate or final range checks
- **Why**: Accumulating N values can multiply the bit-width by log2(N)
- **Severity**: WARNING
- **How to verify**: Check accumulation loops; verify the accumulator bit-width is sufficient

### ✅ CHECK-4.3: Input range is validated
- **What**: The circuit should include range checks on the public input
- **Why**: Out-of-range inputs can cause overflow in the first layer, propagating errors
- **Severity**: WARNING
- **How to verify**: Check for range constraints on instance/public input values

### ✅ CHECK-4.4: Lookup table inputs are range-checked
- **What**: Before using a lookup table, the input must be verified to fall within
  the table's valid range
- **Why**: Out-of-range lookup returns undefined values — prover can choose any output
- **Severity**: CRITICAL
- **How to verify**: For each lookup table usage, find the preceding range check

---

## 5. Approximation Soundness

### ✅ CHECK-5.1: Approximation error is bounded and documented
- **What**: For each approximated operation (Softmax, Sigmoid, etc.), the maximum
  approximation error must be stated and justified
- **Why**: Unbounded error means the proof guarantees nothing about accuracy
- **Severity**: WARNING
- **How to verify**: For each approximation, find the error bound; verify it's provably
  correct (not just empirically measured)

### ✅ CHECK-5.2: Approximation matches paper's specification
- **What**: If the paper specifies a particular approximation (e.g., degree-7 Taylor),
  the code must implement exactly that
- **Why**: A different approximation may have different error characteristics
- **Severity**: WARNING
- **How to verify**: Compare paper's approximation formula with code implementation

### ✅ CHECK-5.3: Approximation input range matches actual input distribution
- **What**: The approximation's valid input range must cover all values the model
  can produce in practice
- **Why**: Outside the valid range, the approximation error is unbounded
- **Severity**: CRITICAL
- **How to verify**: Profile the model's intermediate value ranges; compare with
  approximation bounds

---

## 6. Quantization Consistency

### ✅ CHECK-6.1: Quantization scheme matches between paper and code
- **What**: The paper's quantization method (uniform, per-channel, symmetric/asymmetric)
  must match the implementation
- **Why**: Different quantization schemes have different error profiles
- **Severity**: WARNING
- **How to verify**: Compare paper's Section on quantization with code's quantization logic

### ✅ CHECK-6.2: Scale factors are committed or deterministic
- **What**: Quantization scale factors must be either committed (if dynamic) or
  deterministic (if static/calibrated)
- **Why**: If the prover can choose scale factors, they can distort the computation
- **Severity**: CRITICAL
- **How to verify**: Check whether scale factors are instance values or computed
  deterministically from committed weights

### ✅ CHECK-6.3: Quantization error is bounded end-to-end
- **What**: The accumulated quantization error across all layers must be bounded
- **Why**: Per-layer error bounds don't guarantee end-to-end accuracy
- **Severity**: WARNING
- **How to verify**: Look for end-to-end error analysis in the paper; compare with
  actual bit-widths in code

---

## 7. Zero-Knowledge Property

### ✅ CHECK-7.1: Private inputs are not leaked via public outputs
- **What**: The circuit's public output should not allow reconstruction of private inputs
- **Why**: This is the fundamental ZK property — violated if output leaks too much information
- **Severity**: CRITICAL
- **How to verify**: Analyze the circuit's input-output relationship; check if the output
  is a one-way function of the input

### ✅ CHECK-7.2: No auxiliary information leakage
- **What**: Proof transcripts, verifier queries, and circuit structure should not reveal
  private witness values
- **Why**: Side-channel leakage breaks zero-knowledge even if the circuit is correct
- **Severity**: WARNING
- **How to verify**: Check if the proof system used (Groth16, Plonk, etc.) provides
  computational or statistical ZK; verify no additional information is published

### ✅ CHECK-7.3: Model architecture is treated correctly (public vs private)
- **What**: Decide whether the model architecture itself is public or private, and
  handle accordingly
- **Why**: If architecture is meant to be private, the circuit structure shouldn't reveal it
- **Severity**: INFO
- **How to verify**: Check paper's threat model for what is public vs. private

---

## Quick Reference: Severity Guide

| Severity | Meaning | Action Required |
|----------|---------|-----------------|
| CRITICAL | Breaks soundness or ZK — proof is invalid | Must fix before deployment |
| WARNING  | May affect accuracy or security in edge cases | Should fix; document exceptions |
| INFO     | Best practice, not a security issue | Recommended improvement |
