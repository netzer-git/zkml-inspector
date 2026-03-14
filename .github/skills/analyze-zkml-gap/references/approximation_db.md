# Approximation Strategy Database

Reference database of known approximation strategies for non-polynomial operations
in zkML circuits. Each entry includes the method, error bounds, gate cost estimates,
and known issues in popular implementations.

---

## 1. Piecewise-Linear Approximation

### Method
Divide the input range [a, b] into N equal segments. In each segment, approximate
f(x) with a linear function: `f(x) ≈ αᵢ·x + βᵢ` where i is the segment index.

### Error Bounds
- **Max error**: `ε ≤ (b-a)² · max|f''(x)| / (8N²)` (for smooth functions)
- **Sigmoid (3 segments, [-8,8])**: ε ≈ 0.05 — often unacceptable
- **Sigmoid (8 segments, [-8,8])**: ε ≈ 0.008 — acceptable for most models
- **Sigmoid (16 segments, [-8,8])**: ε ≈ 0.002 — good
- **Softmax**: Not directly applicable (involves exp) — apply to exp() first

### Gate Cost
- Segment selection: ~N comparison gates
- Linear evaluation: 1 multiplication + 1 addition per evaluation
- Total: ~(2N + 20) gates per invocation

### Known Issues
- **EZKL**: Uses piecewise-linear for Sigmoid/Tanh with configurable segments. Default is often too few segments.
- **Input range violation**: If input falls outside [a, b], result is clamped — this can cause silent accuracy degradation.
- **Continuity**: Segments may not join smoothly at boundaries → discontinuous gradients (doesn't affect inference but can cause numerical instability).

---

## 2. Polynomial Approximation (Taylor Series)

### Method
Approximate f(x) with a polynomial of degree d around a center point c:
$$f(x) \approx \sum_{k=0}^{d} \frac{f^{(k)}(c)}{k!}(x-c)^k$$

### Error Bounds
- **Taylor remainder**: `|R_d(x)| ≤ |f^(d+1)(ξ)|·|x-c|^(d+1) / (d+1)!`
- **Sigmoid (degree 3, center 0)**: Good for |x| < 2, error explodes for |x| > 3
- **exp(x) (degree 5)**: Accurate for |x| < 3, error > 1% for |x| > 4

### Gate Cost
- Degree-d polynomial: d multiplications + d additions
- With Horner's method: d multiplications + d additions (no extra storage)
- Total: ~(2d + 5) gates

### Known Issues
- **Range limitation**: Taylor series converges slowly far from center — poor for wide-range inputs
- **Fixed-point overflow**: High-degree terms (x^d) can overflow fixed-point representation
- **Not used alone**: Usually combined with range reduction (see Hybrid approaches)

---

## 3. Polynomial Approximation (Chebyshev)

### Method
Approximate f(x) on [a, b] using Chebyshev polynomials of the first kind:
$$f(x) \approx \sum_{k=0}^{d} c_k T_k\left(\frac{2x - a - b}{b - a}\right)$$

### Error Bounds
- **Minimax property**: Chebyshev gives the best polynomial approximation (minimizes max error)
- **Sigmoid (degree 5, [-6,6])**: ε ≈ 0.003 — better than same-degree Taylor
- **exp(x) (degree 4, [0, ln2])**: ε ≈ 0.0001 — excellent with range reduction

### Gate Cost
- Same as polynomial: ~(2d + 5) gates
- But typically needs lower degree than Taylor for same accuracy

### Known Issues
- **Coefficients are irrational**: Fixed-point representation of Chebyshev coefficients introduces quantization error
- **Recurrence relation**: Computing T_k(x) via recurrence may accumulate error in fixed-point

---

## 4. Lookup Table

### Method
Pre-compute f(x) for all possible input values (or a quantized subset) and store in a table.
Circuit verifies: "the output value was indeed looked up from the table."

### Error Bounds
- **Quantization error only**: `ε = |f(x) - f(quantize(x))| ≤ Δ · max|f'(x)|` where Δ is quantization step
- **With 8-bit input quantization**: 256 table entries, Δ = range/256
- **With 16-bit input**: 65536 entries — large but feasible

### Gate Cost
- **Per lookup**: 1 lookup gate (~50 constraints in Halo2/Plonk with lookup arguments)
- **Table setup**: One-time cost proportional to table size
- **Total per invocation**: ~50 gates (very cheap!)

### Known Issues
- **Table size explosion**: For multi-input functions (e.g., x·sigmoid(x) for SiLU), table size grows exponentially
- **Range limitation**: Input outside table range is undefined — must be caught with a range check
- **EZKL**: Supports lookup tables via `--bits` flag for activation functions
- **Halo2**: Native lookup argument support; table must be committed as fixed columns

---

## 5. Range Reduction + Core Approximation (Hybrid)

### Method
Combine range reduction with a core approximation:
1. **Range reduce**: Transform x into a small range [a, b] using mathematical identities
2. **Approximate**: Apply polynomial/lookup on the reduced range
3. **Reconstruct**: Transform back to the original output

### Examples
- **exp(x)**: x = n·ln2 + r (where r ∈ [0, ln2]), then exp(x) = 2^n · exp(r), approximate exp(r) only
- **sigmoid(x)**: For x > 0, σ(x) = 1/(1+exp(-x)); for x < 0, σ(x) = exp(x)/(1+exp(x)); only need exp on [0, ∞)
- **sin/cos**: Reduce to [0, π/4] using periodicity and symmetry

### Error Bounds
- Error of core approximation in reduced range (typically small)
- Reconstruction is exact if using integer arithmetic for range reduction step

### Gate Cost
- Range reduction: ~100-500 gates (comparison + integer arithmetic)
- Core approximation: depends on method (polynomial or lookup)
- Reconstruction: ~50-200 gates
- Total: typically 500-2000 gates — good balance of accuracy and cost

### Known Issues
- **Integer arithmetic in range reduction**: The n·ln2 decomposition requires integer floor/ceil
- **Edge cases**: 0, -∞, +∞, NaN handling — paper may not address these
- **Fixed-point overflow during reconstruction**: 2^n may overflow for large n

---

## 6. Newton's Method (for Division / Inverse Square Root)

### Method
Iteratively refine an estimate of 1/x or 1/√x:
- **1/x**: x_{n+1} = x_n · (2 - a·x_n)
- **1/√x**: x_{n+1} = x_n · (3 - a·x_n²) / 2

### Error Bounds
- Quadratic convergence: error halves with each iteration
- 3-4 iterations from a lookup-based initial guess gives ~32 bits of precision

### Gate Cost
- Per iteration: 2-3 multiplications + 1-2 additions
- Total for 1/x with 3 iterations: ~100 gates
- Total for 1/√x with 3 iterations: ~150 gates

### Known Issues
- **Initial guess quality**: Poor initial guess → more iterations → more gates
- **Division by zero**: Not caught unless explicit range check added
- **Used in LayerNorm**: The 1/√(σ²+ε) term — commonly approximated with Newton's method

---

## Operator → Recommended Strategy Matrix

| Operator   | Recommended Strategy     | Alternative              | Notes                                |
|------------|--------------------------|--------------------------|--------------------------------------|
| Sigmoid    | Lookup (8-bit input)     | Piecewise-linear (8 seg) | Lookup preferred for < 10-bit input  |
| Tanh       | Lookup (8-bit input)     | Piecewise-linear (8 seg) | Derive from sigmoid if possible      |
| GELU       | Lookup (8-bit input)     | Chebyshev degree-5       | Tanh-approximation form adds cost    |
| SiLU       | Lookup (8-bit input)     | Piecewise-linear         | 2D lookup impractical; decompose     |
| Softmax    | Range-reduce + lookup    | Piecewise exp + Newton   | Range reduction critical for exp()   |
| LayerNorm  | Newton (1/√x) + lookup  | Lookup for full expr     | Division is the bottleneck           |
| BatchNorm  | Fold into Linear/Conv   | Newton (1/√x)            | Folding eliminates all gates         |
| exp(x)     | Range-reduce + poly/LUT | Taylor degree-5 on [0,1] | Never use raw Taylor on full range   |
| 1/x        | Newton (3 iterations)    | Lookup table             | Newton better for high precision     |
| 1/√x      | Newton (3 iterations)    | Lookup table             | Used by LayerNorm/BatchNorm          |
