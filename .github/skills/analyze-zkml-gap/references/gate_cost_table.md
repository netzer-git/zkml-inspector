# Gate Cost Table

Estimated constraint counts for common zkML operations across proof systems.
Values are order-of-magnitude estimates per single invocation.

**Usage**: The `gate_cost_profiler.py` script parses this table. Keep the format
exactly as shown (pipe-delimited markdown table with Operator, Exact, Approx, Lookup columns).

---

## Core Operations

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| MatMul     | 5000   | 5000   | 5000   | O(n·m·k); scales with matrix dimensions         |
| Conv2D     | 8000   | 8000   | 8000   | O(k²·c_in·c_out·h·w); kernel-dependent          |
| Conv1D     | 4000   | 4000   | 4000   | O(k·c_in·c_out·l)                               |
| Linear     | 3000   | 3000   | 3000   | Same as MatMul for single vector                 |

## Activation Functions

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| ReLU       | 100    | 80     | 50     | Comparison + conditional; cheapest activation    |
| Sigmoid    | 50000  | 2000   | 500    | Exact requires exp(); lookup strongly preferred  |
| Tanh       | 50000  | 2000   | 500    | Derivable from Sigmoid                           |
| GELU       | 80000  | 3000   | 800    | Requires erf(); worst-case activation            |
| SiLU       | 55000  | 2500   | 600    | x·sigmoid(x); Sigmoid dominates cost             |

## Normalization (Transformer Killers)

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| Softmax    | 100000 | 5000   | 1500   | exp() + division; THE Transformer Killer         |
| LayerNorm  | 80000  | 4000   | 1200   | mean + variance + div + sqrt; very expensive     |
| BatchNorm  | 60000  | 3000   | 1000   | Can be folded into Linear (→ 0 gates)            |
| GroupNorm  | 70000  | 3500   | 1100   | Between LayerNorm and BatchNorm                  |

## Arithmetic

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| Add        | 10     | 10     | 10     | Single addition gate                             |
| Mul        | 20     | 20     | 20     | Single multiplication gate                       |

## Pooling

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| MaxPool    | 200    | 200    | 100    | O(k²) comparisons per output element             |
| AvgPool    | 300    | 300    | 200    | Addition + division                              |

## Composite

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| Attention  | 200000 | 15000  | 5000   | 2×MatMul + Scale + Softmax; per attention head   |
| Embedding  | 500    | 500    | 200    | Table lookup                                     |

## Infrastructure

| Operator   | Exact  | Approx | Lookup | Notes                                          |
|------------|--------|--------|--------|-------------------------------------------------|
| Lookup     | 50     | 50     | 50     | Per table entry; using lookup argument           |
| RangeCheck | 100    | 100    | 50     | Per range-checked value                          |
| Dropout    | 0      | 0      | 0      | Must be removed for ZK inference                 |

---

## Proof System Multipliers

The base costs above assume a Plonk-like system. Apply these multipliers for other systems:

| Proof System | Multiplier | Notes                                    |
|--------------|------------|------------------------------------------|
| Groth16      | 0.8×       | Slightly cheaper per gate, but no lookups |
| Plonk        | 1.0×       | Baseline (custom gates + lookups)         |
| Halo2        | 1.0×       | Plonk-based with lookup arguments         |
| Plonky2      | 0.6×       | Goldilocks field; cheaper arithmetic      |
| Nova/IVC     | 0.3×       | Folding-based; amortized cost             |

---

## Cost Estimation Formula

For a model with operators $O_1, ..., O_n$:

$$\text{Total Gates} \approx \sum_{i=1}^{n} \text{count}(O_i) \times \text{CostPerInvocation}(O_i) \times \text{SystemMultiplier}$$

Where `count(Oᵢ)` is the number of times operator i is invoked in a forward pass.

**Example: Transformer Block (d=768, heads=12, seq_len=128)**
- Self-Attention: 12 heads × (2×MatMul + Softmax) ≈ 12 × (10000 + 1500) = 138,000
- FFN: 2×Linear(768→3072→768) ≈ 2 × 5000 = 10,000
- 2×LayerNorm ≈ 2 × 1200 = 2,400
- 2×Add (residual) ≈ 20
- **Total per block ≈ 150,420 gates** (with lookup-based approximations)
- **12-layer transformer ≈ 1.8M gates** → proving time ~seconds on GPU
