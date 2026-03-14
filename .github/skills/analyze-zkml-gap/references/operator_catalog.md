# zkML Operator Catalog

Reference catalog of operators commonly specified in zkML research papers.
Each entry includes the mathematical definition, known ZK implementation patterns,
and common gap patterns between paper and code.

---

## Linear Operators

### MatMul (Matrix Multiplication)

**Mathematical Definition:**
$$C_{ij} = \sum_{k} A_{ik} \cdot B_{kj}$$

**ZK Implementation Patterns:**
- Direct arithmetic circuit: one multiplication gate + one addition gate per MAC operation
- Constraint count: O(n·m·k) for (n×m) × (m×k) matrices
- Typically the dominant cost in transformer FFN layers

**Common Gap Patterns:**
- Paper assumes arbitrary-precision real multiplication; code uses fixed-point with truncation after each multiply-accumulate
- Accumulation overflow: for large inner dimensions (k > 512), fixed-point accumulator may overflow without range checks
- Strassen/Karatsuba optimizations mentioned in paper but not implemented in circuit

---

### Conv2D (2D Convolution)

**Mathematical Definition:**
$$Y_{c_{out}, h, w} = \sum_{c_{in}} \sum_{k_h} \sum_{k_w} X_{c_{in}, h+k_h, w+k_w} \cdot W_{c_{out}, c_{in}, k_h, k_w} + b_{c_{out}}$$

**ZK Implementation Patterns:**
- Unrolled as MatMul via im2col transformation
- Direct convolution loop: O(c_out · c_in · k² · H · W) constraints
- Some implementations use NTT-based convolution for large kernels

**Common Gap Patterns:**
- Padding mode (zero-pad, reflect, circular) may differ between paper and code
- Stride/dilation parameters may not be constrained — prover can change them
- Bias term omitted or not committed separately

---

### Linear (Fully Connected)

**Mathematical Definition:**
$$y = Wx + b$$

**ZK Implementation Patterns:**
- Same as MatMul + vector addition
- Weight matrix W and bias b should be committed as public/instance values

**Common Gap Patterns:**
- Bias not committed — allows prover to choose arbitrary bias
- Weight matrix not committed in some implementations (critical soundness issue)

---

## Activation Functions

### ReLU (Rectified Linear Unit)

**Mathematical Definition:**
$$\text{ReLU}(x) = \max(0, x)$$

**ZK Implementation Patterns:**
- Decompose x into sign bit + magnitude
- Constraint: `x = x_pos - x_neg`, `x_pos ≥ 0`, `x_neg ≥ 0`, `x_pos · x_neg = 0`
- Range check on both components
- ~100 gates (cheap)

**Common Gap Patterns:**
- Missing range check allows prover to set both x_pos and x_neg to non-zero
- Fixed-point truncation before ReLU can shift the threshold from 0

---

### Sigmoid

**Mathematical Definition:**
$$\sigma(x) = \frac{1}{1 + e^{-x}}$$

**ZK Implementation Patterns:**
- **Exact**: Requires exp() in-circuit — extremely expensive (50k+ gates)
- **Piecewise-linear**: 3-5 segments, ~2000 gates, error bound ~0.01
- **Lookup table**: Pre-computed table for discretized input range, ~500 gates
- **Polynomial approx**: Degree-3 Chebyshev, ~1000 gates, error ~0.005 in [-5,5]

**Common Gap Patterns:**
- Paper defines exact sigmoid; code uses piecewise-linear with only 3 segments
- Input range assumption: approximation valid only in [-8, 8] but model produces inputs outside this range
- Error not bounded or proven in the paper's security analysis

---

### Tanh

**Mathematical Definition:**
$$\tanh(x) = \frac{e^x - e^{-x}}{e^x + e^{-x}} = 2\sigma(2x) - 1$$

**ZK Implementation Patterns:**
- Usually derived from Sigmoid: `tanh(x) = 2·sigmoid(2x) - 1`
- Same cost profile as Sigmoid
- Alternatively: odd-degree polynomial approximation (exploits symmetry)

**Common Gap Patterns:**
- Same as Sigmoid — approximation range mismatch
- Symmetry not exploited (code doesn't use `tanh(-x) = -tanh(x)`)

---

### GELU (Gaussian Error Linear Unit)

**Mathematical Definition:**
$$\text{GELU}(x) = x \cdot \Phi(x) = x \cdot \frac{1}{2}\left[1 + \text{erf}\left(\frac{x}{\sqrt{2}}\right)\right]$$

Approximate form:
$$\text{GELU}(x) \approx 0.5x\left(1 + \tanh\left[\sqrt{2/\pi}(x + 0.044715x^3)\right]\right)$$

**ZK Implementation Patterns:**
- **Exact**: Requires erf() — impractical (80k+ gates)
- **Tanh approximation**: Uses the approximate form above, still requires tanh()
- **Lookup table**: Most practical, ~800 gates

**Common Gap Patterns:**
- Paper uses exact GELU; code uses tanh-approximation or lookup
- The 0.044715 coefficient precision matters — fixed-point truncation affects it
- Some implementations use ReLU as a drop-in replacement (changes model behavior)

---

### SiLU / Swish

**Mathematical Definition:**
$$\text{SiLU}(x) = x \cdot \sigma(x)$$

**ZK Implementation Patterns:**
- Requires sigmoid computation + one multiplication
- Cost is sigmoid cost + ~20 gates

**Common Gap Patterns:**
- Same as Sigmoid — the sigmoid component dominates cost and error

---

## Normalization Operators (Transformer Killers)

### Softmax

**Mathematical Definition:**
$$\text{Softmax}(x_i) = \frac{e^{x_i}}{\sum_j e^{x_j}}$$

**ZK Implementation Patterns:**
- **Exact**: exp() for each element + sum + division — catastrophically expensive (100k+ gates per head)
- **Lookup table**: Discretize input range, pre-compute exp values, ~1500 gates
- **Piecewise approximation**: 5-8 segments for exp(), ~5000 gates
- **Base-2 trick**: Use 2^x instead of e^x (shift by ln2), cheaper in binary circuits
- **Softmax-free attention**: Replace with linear attention (architecture change)

**Common Gap Patterns:**
- **The #1 Transformer Killer**: Dominates circuit cost in transformer models
- Numerical stability trick (subtract max) adds comparison gates — sometimes omitted in ZK, causing overflow
- Paper assumes exact softmax; code uses 3-segment piecewise linear → large error for extreme values
- Division is expensive in arithmetic circuits — some implementations approximate 1/x with Newton's method

---

### LayerNorm (Layer Normalization)

**Mathematical Definition:**
$$\text{LayerNorm}(x) = \gamma \cdot \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta$$
where $\mu = \frac{1}{n}\sum x_i$, $\sigma^2 = \frac{1}{n}\sum(x_i - \mu)^2$

**ZK Implementation Patterns:**
- Requires: mean (addition + division), variance (squaring + addition + division), inverse square root, scaling
- **Division**: ~5000 gates via Newton's method or lookup
- **Inverse sqrt**: ~10000 gates exact, ~2000 via lookup
- Total: ~80000 gates exact, ~4000 with lookups

**Common Gap Patterns:**
- Epsilon (ε) value differs between paper and code — affects numerical stability
- Division implemented as multiplication by approximate inverse — error not bounded
- γ and β parameters not committed — prover can choose arbitrary normalization
- Some implementations skip variance computation (use RMSNorm instead) without documenting the change

---

### BatchNorm (Batch Normalization)

**Mathematical Definition:**
$$\hat{x}_i = \frac{x_i - \mu_B}{\sqrt{\sigma_B^2 + \epsilon}}$$
where $\mu_B$ and $\sigma_B^2$ are batch statistics

**ZK Implementation Patterns:**
- In inference mode: running mean/variance are constants → cheaper than LayerNorm
- Pre-fold into preceding linear layer: `W' = W·γ/√(σ²+ε)`, `b' = (b-μ)·γ/√(σ²+ε) + β`
- Folded version: zero additional gates

**Common Gap Patterns:**
- Paper describes training-time BatchNorm with batch statistics; code uses inference-mode with stored statistics
- Folding optimization not applied — BatchNorm computed separately instead of folded into Linear/Conv

---

## Pooling & Other

### MaxPool

**Mathematical Definition:**
$$y_{c,h,w} = \max_{k_h,k_w} x_{c, h \cdot s + k_h, w \cdot s + k_w}$$

**ZK Implementation Patterns:**
- Requires comparison gates: O(k²) comparisons per output element
- ~200 gates per pooling window

**Common Gap Patterns:**
- Argmax information leaked — in ZK, revealing which element was max may leak information
- Comparison chain not constrained — prover could choose a different max

---

### Attention (Multi-Head Attention)

**Mathematical Definition:**
$$\text{Attention}(Q, K, V) = \text{Softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right) V$$

**ZK Implementation Patterns:**
- Composed of: Linear projection (Q,K,V) → MatMul(Q,K^T) → Scale → Softmax → MatMul(·,V)
- Total cost dominated by Softmax (per-head)
- Multi-head: cost scales linearly with number of heads

**Common Gap Patterns:**
- The √d_k scaling factor: integer division in fixed-point loses precision
- Softmax computation is the dominant cost — see Softmax section
- KV-cache optimizations from paper not reflected in circuit
- Causal masking (setting future positions to -∞) interacts with fixed-point range limits

---

### Dropout

**Mathematical Definition:**
$$y_i = \begin{cases} x_i / (1-p) & \text{with probability } 1-p \\ 0 & \text{with probability } p \end{cases}$$

**ZK Implementation Patterns:**
- **Must be removed in ZK inference** — randomness breaks determinism and proof validity
- Zero gates if properly removed

**Common Gap Patterns:**
- Paper describes model with dropout; code fails to remove it for inference
- Training-time description confused with inference-time behavior
