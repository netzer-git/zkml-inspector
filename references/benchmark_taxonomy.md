# Benchmark Finding Taxonomy

Every finding emitted by the pipeline carries two closed-list classification
fields used by the benchmark grader:

- `category` — *what went wrong in the implementation*
- `security_concern` — *what an attacker gains if the gap is exploited*

These are **independent dimensions** — do not collapse them. Strings must
match the lists below byte-for-byte (capitalization, punctuation,
parentheses included). When nothing fits, use `Other` and record a
one-sentence justification in `category_reasoning`. Prefer the
highest-impact classification when borderline (e.g. `Proof Forgery` over
`Semantic Subversion` when a malicious prover can use the gap to forge).

---

## Category (closed list)

| Value | When to use |
|-------|-------------|
| `Under-constrained Circuit` | Constraints are too loose; verifier accepts non-deterministic or arbitrary values that should be pinned. Wire disconnects, missing copy/range constraints, unconstrained activation outputs. |
| `Protocol/Transcript Logic` | Errors in the interactive→non-interactive transformation: missing/weak Fiat-Shamir, missing domain separation, transcript reuse, sampling a challenge before the prover commits the relevant witness. |
| `Specification Mismatch` | Code deviates from the paper in a way not better described by the other categories — wrong operator parameters, wrong segment count, omitted bias term, different rounding mode. |
| `Numerical/Quantization Bug` | Precision loss, fixed-point overflow, accumulator too narrow, scale mismatch, missing range check on rescale. |
| `Witness/Commitment Mismatch` | Proof does not bind to external data commitments. Uncommitted weights, Merkle root never verified in-circuit, advice cells appended after commitment, public input not exposed as instance. |
| `Engineering/Prototype Gap` | Lazy implementation: hardcoded constants standing in for crypto, mock `prove()` / `commit()` bodies, feature flags that disable security checks, placeholder weights, debug branches. |
| `Other` | None of the above fits. Justify in `category_reasoning`. |

---

## Security Concern (closed list)

| Value | When to use |
|-------|-------------|
| `Proof Forgery (Soundness)` | Malicious prover can produce a valid proof for an incorrect result, a different model, or a statement the verifier should reject. |
| `Information Leakage (Privacy)` | Private data (prompt, weights, activations) is recoverable from the proof transcript or commitment material. |
| `Semantic Subversion (Integrity)` | Proof is mathematically sound but binds to the wrong inputs/outputs (right relation, wrong statement; or right model, placeholder data). |
| `Proof Malleability` | A valid proof can be transformed into another valid proof for the same statement without knowing the witness. |
| `Denial of Proof (Reliability)` | Honest prover cannot produce a valid proof — kernel crash on legitimate input, unprovable corner case, OOM. |
| `Governance Bypass` | The system claims to enforce an audit/policy rule but does not. |
| `Other` | None of the above fits. Justify in `category_reasoning`. |

---

## Common defaults (starting points, not a lookup table)

| Finding pattern | Default `category` | Default `security_concern` |
|-----------------|--------------------|----------------------------|
| Wire disconnect / missing copy or range constraint | `Under-constrained Circuit` | `Proof Forgery (Soundness)` |
| Non-determinism in circuit (`dropout`, `random`) | `Under-constrained Circuit` | `Proof Forgery (Soundness)` |
| Mock `prove()` / `commit()` body or phantom counter | `Engineering/Prototype Gap` | `Proof Forgery (Soundness)` |
| Placeholder/random weights stand in for the real model | `Engineering/Prototype Gap` | `Semantic Subversion (Integrity)` |
| Operator `MISSING` or `SUBSTITUTION` | `Specification Mismatch` | `Semantic Subversion (Integrity)` |
| Operator `MISMATCH` — wrong segments/degree | `Numerical/Quantization Bug` | `Semantic Subversion (Integrity)` |
| Operator under-constrained (admits y ≠ f(x,w)) | `Under-constrained Circuit` | `Proof Forgery (Soundness)` |
| Value never committed (or committed but never verified) | `Witness/Commitment Mismatch` | `Semantic Subversion (Integrity)` (escalate to `Proof Forgery` if the value participates in a soundness equation) |
| Challenge sampled before prover commits witness | `Protocol/Transcript Logic` | `Proof Forgery (Soundness)` |
| Transcript reused across sessions (no domain sep) | `Protocol/Transcript Logic` | `Proof Malleability` |
| Scale / bit-width mismatch with paper | `Numerical/Quantization Bug` | `Semantic Subversion (Integrity)` |
| Accumulator overflow reachable | `Numerical/Quantization Bug` | `Proof Forgery (Soundness)` |

Override these when the specifics of the finding warrant a different choice.
