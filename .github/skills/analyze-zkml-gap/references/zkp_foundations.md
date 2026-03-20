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

**Key question for paper-analyst:** Does the paper specify WHAT is committed?
Which values are public vs. private? What is the threat model — who are we
protecting against?

**Key question for code-inspector:** WHERE in the code are commitments made?
Is there a setup phase? Are ALL parameters bound, or only some?

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

**Key question for paper-analyst:** For each operator, does the paper define
the EXACT constraint being enforced? Or does it hand-wave ("we implement
softmax in the circuit")? Does it specify the approximation method and
bound the error?

**Key question for code-inspector:** For each layer, can you trace the
constraint from input → computation → output? Are there any unconstrained
wires? Any intermediate values that are assigned but never constrained?

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

**Key question for paper-analyst:** What does the paper claim the verifier
checks? What's the verification complexity?

**Key question for code-inspector:** Is the final output exposed as a
public/instance value? Can the verifier actually read the result?

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

**What the paper-analyst must extract:** What precision does the paper assume?
What scale factor? What quantization scheme (symmetric/asymmetric, per-tensor/per-channel)?

**What the code-inspector must extract:** What is the actual scale/bits config?
Are there range checks after multiplications? Does the accumulator have sufficient bit-width?

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

## Transformer Killers — Why Non-Polynomial Ops Matter

Arithmetic circuits can only express polynomial constraints natively
(addition and multiplication over the field). Any non-polynomial operation
requires special treatment:

| Operation | Why it's hard | The fundamental problem |
|-----------|---------------|----------------------|
| Softmax | Requires exp(x) and division | exp() is transcendental — cannot be expressed as a finite polynomial |
| LayerNorm | Requires mean, variance, division, sqrt | Division and square root are not polynomial |
| GELU | Requires erf() or tanh() | erf() is a special function, tanh() is transcendental |
| Sigmoid | Requires exp(x) and division | Same as softmax but simpler |
| Comparison (for ReLU) | Requires determining sign of x | Bit decomposition needed — costs range-check gates |

**The approximation tradeoff:** You can approximate any function with
polynomials (Taylor, Chebyshev) or piecewise-linear segments or lookup
tables. Each has a cost:
- **Polynomial degree d**: d multiplications + d additions, but error grows
  rapidly outside the approximation range
- **Piecewise-linear with N segments**: N comparisons + 1 linear eval,
  error ∝ 1/N² for smooth functions
- **Lookup table**: ~50 gates per lookup (in Plonk/Halo2), but table
  size grows with input precision

**The paper must specify:** Which approximation method, what degree/segments,
what input range, what error bound.

**The code must implement:** Exactly what the paper says, or document the
deviation. A different approximation = a different function being proven.

---

## Proof Systems — What Matters for Analysis

Different proof systems have different constraint models:

| System | Constraint Model | Lookup Support | Key Feature |
|--------|-----------------|----------------|-------------|
| Groth16 | R1CS (rank-1 constraint system) | No native lookups | Smallest proofs, trusted setup |
| Plonk | Plonkish (custom gates + wiring) | Yes (lookup arguments) | Flexible, universal setup |
| Halo2 | Plonkish with advice/fixed/instance columns | Yes (strong lookup support) | No trusted setup, recursive |
| Plonky2 | Plonkish over Goldilocks field | Yes | Fast proving, small field |
| Nova/IVC | R1CS with folding | Via secondary circuit | Incremental verification |

**Why this matters for analysis:**
- A Groth16 circuit that uses a "lookup table" is doing something non-standard
- A Halo2 circuit without lookup arguments for Softmax is leaving performance
  on the table
- The proof system determines what optimizations are possible

---

## Accountability Extraction Checklists

### What paper-analyst MUST extract (or flag as missing)

1. **Proof system**: Which system? (Groth16, Plonk, Halo2, Nova, custom?)
2. **Threat model**: What is public? What is private? Who is the adversary?
3. **Commitment scheme**: How are weights committed? What hash/commitment?
4. **Operator list**: Every mathematical operation in the model
5. **For each operator**: Exact definition, constraint count (if given), implementation strategy
6. **For each non-polynomial op**: Approximation method, degree/segments, input range, error bound
7. **Quantization**: Bit-width, scale factor, quantization scheme
8. **Soundness claims**: What theorems/proofs are stated?
9. **Completeness assumptions**: Any restrictions on valid inputs?
10. **ZK claims**: What exactly is hidden from the verifier?

If the paper is vague on any of these, the paper-analyst MUST flag it as
`UNDERSPECIFIED` with its own assessment of what the paper likely means.

### What code-inspector MUST extract (or flag as missing)

1. **Framework**: Which zkML framework? (EZKL, Halo2, Circom, custom?)
2. **Proof system used**: What backend does the code target?
3. **Setup/commitment code**: Where are parameters committed? Which ones?
4. **For each operator**: File, line, implementation type (exact/approx/lookup), code snippet
5. **Constraint structure**: How are constraints defined? Are they complete per layer?
6. **Wire connectivity**: Are layer outputs connected to next layer inputs?
7. **Range checks**: Where? After which operations? What bounds?
8. **Precision config**: Scale bits, field size, quantization parameters
9. **Non-determinism**: Any dropout, random ops, data-dependent branches?
10. **Public outputs**: Is the final result exposed to the verifier?

If the code is ambiguous on any of these, the code-inspector MUST flag it as
`UNCLEAR` with its best interpretation and the code location.

---

## When the zkp-auditor Should Ask Follow-Up Questions

The zkp-auditor receives the outputs of paper-analyst and code-inspector.
It should request clarification (via the orchestrator re-invoking a sub-agent)
when:

1. **Paper says X but paper-analyst didn't extract it**: "The paper mentions
   Poseidon commitments in Section 5, but your manifest doesn't include a
   commitment scheme. Re-analyze Section 5 focusing on commitment construction."

2. **Code does Y but code-inspector didn't explain the constraint logic**:
   "You found softmax at ops.rs:45 but didn't trace the constraint chain.
   Re-inspect ops.rs:40-80 and report: is the output constrained? Are inputs
   range-checked before the lookup?"

3. **Gap between paper and code but unclear if intentional**: "Paper specifies
   8-segment piecewise approximation but code uses 3 segments. Check if there's
   a configuration file or CLI flag that controls segment count."

4. **Missing lifecycle phase**: "I can't find any commitment code in your
   manifest. Re-scan for: Pedersen, Poseidon, hash, commit, bind, instance
   column setup, or any setup/keygen function."
