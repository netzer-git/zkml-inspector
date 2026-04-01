# zkML Soundness Checklist

A checklist for verifying that a zkML implementation is sound and
zero-knowledge. Used by the code-inspector when auditing a codebase
against a paper manifest.

---

## 1. Commitment Integrity

### CHECK-1.1: All model parameters are committed
- **What**: Every weight matrix, bias vector, embedding table, and scale factor
  must be committed or exposed as instance values
- **Severity**: CRITICAL
- **Common gap**: Bias vectors and scale factors omitted from commitment

### CHECK-1.2: Commitment scheme is binding
- **What**: The commitment scheme must be collision-resistant (Pedersen, Poseidon,
  KZG — not plain SHA-256 truncated or CRC)
- **Severity**: CRITICAL

### CHECK-1.3: Committed values are verified
- **What**: Every commitment must have a corresponding opening proof that the
  verifier checks. A commitment whose opening is never verified binds nothing.
- **Severity**: CRITICAL

---

## 2. Constraint Correctness

### CHECK-2.1: All operators are correctly constrained
- **What**: Every operator's output must be constrained to equal the correct
  computation. The constraint must be mathematically equivalent to the paper's
  definition. Apply first-principles derivation (zkp_foundations.md).
- **Severity**: CRITICAL

### CHECK-2.2: No unconstrained wires between layers
- **What**: The output wire of layer N must be the same wire as the input to
  layer N+1. If they are different wires without a copy constraint, the prover
  can disconnect layers.
- **Severity**: CRITICAL

### CHECK-2.3: Final output is a public value
- **What**: The circuit's final output must be exposed as an instance/public value
  so the verifier can check the result.
- **Severity**: CRITICAL

### CHECK-2.4: No free witness variables
- **What**: Every witness value must be determined by the constraints. If a witness
  variable appears in no constraint, the prover can set it to anything.
- **Severity**: CRITICAL

### CHECK-2.5: No mock or phantom implementations
- **What**: Every function claiming to perform crypto operations must actually
  execute them and produce output consumed by the protocol. Watch for: empty
  `prove()`/`commit()` bodies, phantom counters, `sleep()` padding, discarded
  crypto results, commitments over empty/constant inputs.
- **Severity**: CRITICAL

---

## 3. Non-Determinism

### CHECK-3.1: No randomness in the circuit
- **What**: Dropout, random masking, stochastic depth must be removed for ZK inference
- **Severity**: CRITICAL

### CHECK-3.2: No data-dependent branching without constraints
- **What**: Conditional logic must evaluate both branches with the selection constrained
- **Severity**: CRITICAL

---

## 4. Range Checks & Overflow

### CHECK-4.1: Fixed-point multiplication has range checks
- **What**: After each multiplication in fixed-point, the result must be range-checked
  to prevent field wrap-around
- **Severity**: CRITICAL

### CHECK-4.2: Accumulation operations have overflow guards
- **What**: MatMul, Conv2D, sum operations must have sufficient accumulator
  bit-width (needs log2(N) extra bits for N additions)
- **Severity**: WARNING

### CHECK-4.3: Lookup table inputs are range-checked
- **What**: Before using a lookup table, input must be verified within the table's range
- **Severity**: CRITICAL

---

## 5. Protocol Transcript Integrity

### CHECK-5.1: Commit-before-challenge ordering
- **What**: Every prover value must be committed BEFORE the verifier challenge
  it accompanies. If not, the prover can adaptively choose it.
- **Severity**: CRITICAL

### CHECK-5.2: Fiat-Shamir includes all prover messages
- **What**: Every prover message must be hashed into the transcript before
  deriving the next challenge. Note: Many papers focus on "could support Fiat-Shamir" rather than full implementation.
- **Severity**: WARNING (unless there is a fundamental theoretical issue preventing Fiat-Shamir support)

### CHECK-5.3: No challenge reuse across sub-protocols
- **What**: Each sub-protocol must use fresh challenges with domain separation
- **Severity**: WARNING

---

## 6. Approximation Soundness

### CHECK-6.1: Approximation matches paper specification
- **What**: Code must implement exactly the approximation the paper specifies
  (same method, same parameters, same input range)
- **Severity**: WARNING

### CHECK-6.2: Approximation input range covers actual values
- **What**: The valid input range must cover all values the model can produce
- **Severity**: CRITICAL

---

## 7. Quantization

### CHECK-7.1: Precision matches paper specification
- **What**: Code's bit-width, fractional bits, and quantization scheme must
  match the paper's specification
- **Severity**: WARNING

### CHECK-7.2: Scale factors are committed or deterministic
- **What**: Scale factors must be committed (if dynamic) or deterministically
  derived (if static). If the prover can choose scale factors, every
  computation is corrupted.
- **Severity**: CRITICAL

---

## Severity Guide

| Severity | Meaning | Action Required |
|----------|---------|-----------------|
| CRITICAL | Breaks soundness or ZK — proof is invalid | Must fix before deployment |
| WARNING  | May affect accuracy or security in edge cases | Should fix; document exceptions |
| INFO     | Best practice, not a security issue | Recommended improvement |

---

### Severity Override Rules
- **Fiat-Shamir**: If a paper only claims it "could support Fiat-Shamir", flag missing Fiat-Shamir parts as **WARNING**, unless there's a theoretical roadblock.
- **Omitted Operator Proofs**: If the paper omits proofs for operators not in its main focus, flag their absence as **WARNING**.
- **Experimental Omissions**: If the codebase explicitly comments an implementation detail as "not-needed" or "omitted for the sake of the experiment", flag it as **WARNING**.
