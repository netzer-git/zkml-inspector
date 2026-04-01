# ZKP Foundations — Shared Knowledge for All Agents

Every agent in the zkml-inspector system MUST understand these fundamentals.
This is not a checklist to pattern-match — it is a reasoning framework.

---

## The ZKP Lifecycle

A zero-knowledge proof system has three phases. Every zkML implementation
maps onto this structure. If you can't identify all three phases in the paper
or code, something is missing.

### Phase 1: Setup & Commitment

**What happens:** The prover and verifier agree on what's being proven.
Public parameters are established. The prover commits to values that
cannot be changed later.

**In zkML this means:**
- **Model weights** are committed (hashed/bound into the circuit).
  If weights aren't committed, the prover can use any model and claim
  it's the one they committed to.
- **Circuit structure** is fixed. The computation graph (which layers,
  which operations, in which order) is part of the public setup.
- **Scale factors** (for fixed-point arithmetic) are either committed
  or deterministically derived. If the prover can choose scale factors,
  they can distort every computation.
- **Public inputs/outputs** are declared. The verifier needs to know
  what it's checking.

### Phase 2: Proving (Witness Construction + Constraint Satisfaction)

**What happens:** The prover executes the computation (ML inference),
producing intermediate values (the "witness"). The prover then generates
a proof that the witness satisfies all constraints defined by the circuit.

**In zkML this means:**
- **Forward pass** happens: input → layer 1 → layer 2 → ... → output.
  Every intermediate activation is a witness value.
- **Constraints enforce correctness**: For each layer, there must be a
  constraint saying `output_i = f(input_i, weights_i)`. Without this,
  the prover can substitute arbitrary intermediate values.
- **Wire connectivity**: The output of layer N must be the SAME wire as
  the input to layer N+1. If these are different unconstrained wires,
  the prover can disconnect layers.
- **Non-determinism is forbidden**: Dropout, random sampling, stochastic
  depth — all break proof determinism. The same input MUST always produce
  the same output.
- **Approximations introduce error**: When exact operations (softmax, exp)
  are replaced with approximations, the constraint now enforces the
  APPROXIMATED function, not the original. The error between them is
  the price of making it provable.

### Phase 3: Verification

**What happens:** The verifier checks the proof against the public
inputs/outputs without seeing the witness. The verifier accepts or rejects.

**In zkML this means:**
- The verifier sees: the committed model hash, the public input (if any),
  and the inference output.
- The verifier does NOT see: model weights (if private), intermediate
  activations, or the input (if private).
- The proof is valid only if ALL constraints are satisfied. One missing
  constraint means the prover can cheat in that spot.

---

## The Three Security Properties

### 1. Soundness (Can a cheating prover fool the verifier?)

A sound system means: if the prover didn't run the computation correctly,
they CANNOT produce a valid proof (except with negligible probability).

**What breaks soundness:**
- Missing constraints: prover can skip a layer
- Unconstrained wires: prover can substitute intermediate values
- Uncommitted weights: prover can use a different model
- Missing range checks: prover can exploit overflow to produce
  arbitrary values that wrap around the field modulus
- Unconstrained conditionals: if the circuit has if/else based on data,
  both branches must be evaluated and the selection constrained

### 2. Completeness (Can an honest prover always produce a valid proof?)

A complete system means: if the prover runs the computation correctly,
they can ALWAYS produce a valid proof.

**What breaks completeness:**
- Approximation input range too narrow: honest computation produces
  values outside the approximation's valid range → constraint fails
- Fixed-point overflow: honest accumulation exceeds field capacity
- Range check too tight: legitimate intermediate values fail range check

### 3. Zero-Knowledge (Does the proof leak private information?)

A zero-knowledge system means: the proof reveals NOTHING about the
witness beyond what's implied by the public inputs/outputs.

**What breaks zero-knowledge:**
- Output is too specific (leaks input features)
- Proof transcript contains correlatable metadata
- Side-channel: timing, proof size varies with input

---

## Fixed-Point Arithmetic in ZK Circuits

ZK circuits operate over finite fields (large prime numbers).
There are no floating-point numbers. Everything is integer arithmetic
modulo a prime p.

**Fixed-point representation:** A real number x is represented as
`x_fixed = round(x × 2^s)` where s is the scale (number of fractional bits).

**Multiplication requires rescaling:** `(a × 2^s) × (b × 2^s) = ab × 2^(2s)`.
After multiplication, you must divide by 2^s (right-shift) to get back
to scale s. This truncation is a source of error.

**Accumulation risk:** MatMul with inner dimension k accumulates k products.
The accumulator needs `log2(k)` extra bits to avoid overflow. For k=768
(typical transformer hidden dim), that's ~10 extra bits.

---

## Protocol Transcript Integrity (Commit-Before-Challenge)

The sections above describe what values must be committed at the **system**
level (weights, scale factors, public inputs). But commitment is also a
**per-round** requirement within every interactive sub-protocol.

**The fundamental rule:** In any interactive proof (or its Fiat-Shamir
transformation), the prover must commit to (or irrevocably send) every
message **before** receiving (or deriving) the verifier challenge that
depends on it. If a prover value is used alongside a challenge but was
not bound before that challenge was generated, the prover can adaptively
choose it to cheat.

This applies to EVERY multi-round protocol: sumcheck, lookup arguments,
inner-product arguments, polynomial commitment openings, folding schemes,
and any custom interactive protocol a paper may define.

### Why This Matters

Consider an interactive protocol with this intended flow:

```
1. Prover computes auxiliary value A
2. Prover commits to A  →  sends commitment to Verifier
3. Verifier sends random challenge β
4. Prover uses A and β to compute proof message
5. Verifier checks the proof using commitment(A) and β
```

If step 2 is skipped (A is never committed), the prover sees β first and
can pick an A′ that satisfies the verification equation for the *wrong*
underlying computation. The protocol loses soundness.

### What to Check

For EVERY interactive sub-protocol in the paper or code:

1. **Identify all prover messages** — witness values, auxiliary vectors,
   intermediate polynomials, multiplicity counts, etc.
2. **Identify all verifier challenges** — random field elements used in
   the protocol (α, β, r, challenge vectors, etc.)
3. **Verify ordering** — each prover message must be committed (or sent)
   BEFORE the challenge it precedes in the protocol. In Fiat-Shamir mode,
   this means the prover message must be hashed into the transcript before
   the challenge is derived from the transcript.
4. **Check the code** — does the code actually commit/hash the prover
   message before generating or using the challenge? Or does it receive
   both as function parameters with no enforced ordering?

### Common Violations

| Pattern | Example | Impact |
|---------|---------|--------|
| Sumcheck polynomial not recorded | Prover sends polynomial evaluations but they're not committed correctly | Prover can adaptively choose polynomials that satisfy the check |
| Opening proof skipped | Commitment exists but its opening at the evaluation point is never verified | Prover can commit to one value and open to another |
| Challenge reuse | Same challenge used across independent sub-protocols without domain separation | Cross-protocol attack: prover correlates responses |

---

## First-Principles Constraint Derivation

Static checklists and operator catalogs cannot cover novel mathematical
constructs introduced by new papers. Every agent MUST be able to derive
what correct constraints look like from the math itself.

For ANY mathematical operation — known or novel — apply this procedure:

### Step 1: State the mathematical claim

Write down the exact function: $y = f(x_1, ..., x_n)$.
Include every parameter (weights, biases, scale factors, lookup entries).

### Step 2: Decompose into field-representable parts

Arithmetic circuits only support addition and multiplication over a finite
field. Decompose $f$ into:
- **Polynomial parts** — directly expressible as constraints
- **Non-polynomial parts** — require approximation, lookup, or decomposition
- **Auxiliary variables** — intermediate values introduced by the decomposition

For each non-polynomial part, identify what strategy is used (approximation,
lookup, bit-decomposition) and what replacement function $\hat{f}$ it creates.

### Step 3: Derive the required constraints

For each part of the decomposition, write the constraint polynomial
$p(...) = 0$ that enforces correctness. Then verify:

1. **Sufficiency**: Does $p = 0$ actually force $y = f(x, w)$?
   (Or can the prover satisfy $p = 0$ with a wrong $y$?)
2. **Necessity**: Does $p = 0$ reject all invalid witness values?
   (Or are there "free variables" — witness values not pinned down?)
3. **Completeness of auxiliary variables**: Every helper variable introduced
   must itself be constrained. An unconstrained auxiliary is a free variable.

### Step 4: Check the boundaries

- **Inputs**: Is there a range assumption? What happens at the boundary?
- **Outputs**: Is the output bound to the next operation's input?
- **Committed values**: Every parameter that affects the constraint output
  must be committed, or the prover can choose it freely.

### Step 5: Characterize the gap

If the constraint is weaker than the stated math, describe precisely
what extra solutions it permits. This is the attack surface.

Example: A Softmax constraint that only enforces $\sum y_i = 1$ permits
the prover to output ANY probability distribution — the binding between
each $y_i$ and $e^{x_i}$ is missing.

**Agents must apply this procedure to EVERY construct they encounter,
especially novel ones not found in the operator catalog.**

---

## Non-Polynomial Operations (Transformer Killers)

Arithmetic circuits only support polynomial constraints (addition and
multiplication). Operations like Softmax, LayerNorm, GELU, Sigmoid require
approximation, lookup tables, or decomposition. A different approximation =
a different function being proven.

See `operator_catalog.md` for per-operator details and `approximation_db.md`
for strategy comparison.


