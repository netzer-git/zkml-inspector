#!/usr/bin/env python3
"""gate_cost_profiler.py — Estimate circuit gate costs for operators in a zkML codebase.

Usage:
    python gate_cost_profiler.py <code_json> [--cost-table <gate_cost_table.md>]

    Where code_json is the JSON output from inspect_codebase.py.

Output: JSON to stdout with structure:
    {
        "operators": [...],
        "total_estimated_gates": N,
        "transformer_killers": [...],
        "top_bottlenecks": [...],
        "recommendations": [...]
    }
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class OperatorCost:
    name: str
    implementation_type: str  # exact, approximation, lookup
    estimated_gates: int
    gate_breakdown: str
    is_transformer_killer: bool
    file: str = ""
    line: int = 0
    notes: str = ""


@dataclass
class Bottleneck:
    operator: str
    estimated_gates: int
    percentage_of_total: float
    severity: str  # CRITICAL, WARNING, INFO
    recommendation: str


@dataclass
class CostProfile:
    operators: list[OperatorCost] = field(default_factory=list)
    total_estimated_gates: int = 0
    transformer_killers: list[OperatorCost] = field(default_factory=list)
    top_bottlenecks: list[Bottleneck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default gate cost model
# ---------------------------------------------------------------------------

# Estimated constraint counts for common operations across proof systems.
# Values are rough order-of-magnitude estimates based on published benchmarks.
# Format: (exact_gates, approx_gates, lookup_gates)
DEFAULT_GATE_COSTS: dict[str, tuple[int, int, int]] = {
    # Linear operations — moderate cost, scales with dimension
    "MatMul":      (5000,  5000,  5000),   # O(n²) multiplications + additions
    "Conv2D":      (8000,  8000,  8000),   # O(k²·c_in·c_out·h·w)
    "Conv1D":      (4000,  4000,  4000),
    "Linear":      (3000,  3000,  3000),

    # Activations — cheap if polynomial, expensive if not
    "ReLU":        (100,   80,    50),      # Comparison + conditional = cheap
    "Sigmoid":     (50000, 2000,  500),     # Exact is very expensive
    "Tanh":        (50000, 2000,  500),     # Same as sigmoid
    "GELU":        (80000, 3000,  800),     # Even worse — involves erf()
    "SiLU":        (55000, 2500,  600),     # x * sigmoid(x)

    # Normalization — "Transformer Killers"
    "Softmax":     (100000, 5000, 1500),    # exp() + division = circuit killer
    "LayerNorm":   (80000,  4000, 1200),    # mean + variance + division
    "BatchNorm":   (60000,  3000, 1000),    # Similar but with stored params
    "GroupNorm":   (70000,  3500, 1100),

    # Arithmetic — cheapest
    "Add":         (10,    10,    10),
    "Mul":         (20,    20,    20),

    # Pooling
    "MaxPool":     (200,   200,   100),     # Comparisons
    "AvgPool":     (300,   300,   200),     # Addition + division

    # Composite
    "Attention":   (200000, 15000, 5000),   # MatMul + Softmax + MatMul

    # Tables & checks (infrastructure)
    "Lookup":      (50,    50,    50),      # Per lookup entry
    "RangeCheck":  (100,   100,   50),

    # Misc
    "Embedding":   (500,   500,   200),
    "Dropout":     (0,     0,     0),       # Should be removed in inference
}

TRANSFORMER_KILLERS = {
    "Softmax", "LayerNorm", "BatchNorm", "GroupNorm",
    "Sigmoid", "Tanh", "GELU", "SiLU",
}


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_operator_cost(
    op_name: str,
    impl_type: str,
    cost_table: dict[str, tuple[int, int, int]] | None = None,
) -> int:
    """Estimate gate count for a single operator."""
    table = cost_table or DEFAULT_GATE_COSTS
    costs = table.get(op_name, (1000, 500, 200))  # default for unknown ops

    if impl_type == "approximation":
        return costs[1]
    elif impl_type == "lookup":
        return costs[2]
    else:
        return costs[0]


def profile_gates(code_manifest: dict) -> CostProfile:
    """Profile gate costs for all operators in the codebase."""
    profile = CostProfile()

    code_operators = code_manifest.get("operators", [])

    for op_data in code_operators:
        op_name = op_data["name"]
        impl_type = op_data.get("implementation_type", "exact")
        gates = estimate_operator_cost(op_name, impl_type)

        is_killer = op_name in TRANSFORMER_KILLERS

        op_cost = OperatorCost(
            name=op_name,
            implementation_type=impl_type,
            estimated_gates=gates,
            gate_breakdown=_gate_breakdown(op_name, impl_type, gates),
            is_transformer_killer=is_killer,
            file=op_data.get("file", ""),
            line=op_data.get("line", 0),
        )

        profile.operators.append(op_cost)
        profile.total_estimated_gates += gates

        if is_killer:
            profile.transformer_killers.append(op_cost)

    # Calculate top bottlenecks
    if profile.total_estimated_gates > 0:
        sorted_ops = sorted(profile.operators, key=lambda x: x.estimated_gates, reverse=True)
        for op in sorted_ops[:5]:
            pct = (op.estimated_gates / profile.total_estimated_gates) * 100
            severity = "CRITICAL" if pct > 30 else "WARNING" if pct > 10 else "INFO"
            profile.top_bottlenecks.append(Bottleneck(
                operator=op.name,
                estimated_gates=op.estimated_gates,
                percentage_of_total=round(pct, 1),
                severity=severity,
                recommendation=_bottleneck_recommendation(op),
            ))

    # Generate recommendations
    profile.recommendations = _generate_recommendations(profile)

    return profile


def _gate_breakdown(op_name: str, impl_type: str, gates: int) -> str:
    """Generate a human-readable cost breakdown."""
    if op_name in TRANSFORMER_KILLERS:
        if impl_type == "exact":
            return f"{gates:,} gates (EXACT — extremely expensive, consider approximation or lookup)"
        elif impl_type == "approximation":
            return f"{gates:,} gates (approximation — verify error bounds are acceptable)"
        else:
            return f"{gates:,} gates (lookup table — efficient but verify table size)"
    else:
        return f"{gates:,} gates ({impl_type})"


def _bottleneck_recommendation(op: OperatorCost) -> str:
    """Generate a recommendation for a bottleneck operator."""
    if op.is_transformer_killer:
        if op.implementation_type == "exact":
            return (
                f"Replace exact {op.name} with a lookup-table or piecewise-linear "
                f"approximation. Expected savings: ~{op.estimated_gates - estimate_operator_cost(op.name, 'lookup'):,} gates"
            )
        elif op.implementation_type == "approximation":
            return (
                f"Consider using a smaller lookup table for {op.name} if error bound permits. "
                f"Current approximation uses {op.estimated_gates:,} gates."
            )
        else:
            return f"Lookup-based {op.name} is already optimized. Verify table size is minimal."
    else:
        return f"Consider batching or optimizing {op.name} if it appears in a hot loop."


def _generate_recommendations(profile: CostProfile) -> list[str]:
    """Generate overall optimization recommendations."""
    recs: list[str] = []

    # Transformer killer warnings
    exact_killers = [
        op for op in profile.transformer_killers
        if op.implementation_type == "exact"
    ]
    if exact_killers:
        names = ", ".join(op.name for op in exact_killers)
        total_savings = sum(
            op.estimated_gates - estimate_operator_cost(op.name, "lookup")
            for op in exact_killers
        )
        recs.append(
            f"CRITICAL: {len(exact_killers)} Transformer Killer operations ({names}) "
            f"use exact implementations. Switching to lookup tables could save "
            f"~{total_savings:,} gates."
        )

    # Total gate count assessment
    total = profile.total_estimated_gates
    if total > 1_000_000:
        recs.append(
            f"WARNING: Total estimated gate count ({total:,}) is very high. "
            f"Proving time will be significant. Consider reducing model size "
            f"or using more aggressive approximations."
        )
    elif total > 100_000:
        recs.append(
            f"INFO: Total estimated gate count ({total:,}) is moderate. "
            f"Optimization of top-3 bottlenecks could reduce this significantly."
        )

    # Check operator balance
    if profile.operators:
        killer_pct = sum(
            op.estimated_gates for op in profile.transformer_killers
        ) / max(total, 1) * 100
        if killer_pct > 60:
            recs.append(
                f"CRITICAL: Transformer Killer operations account for {killer_pct:.0f}% "
                f"of total gates. This circuit is dominated by non-polynomial operations."
            )

    return recs


# ---------------------------------------------------------------------------
# Optional: load custom cost table from markdown
# ---------------------------------------------------------------------------

def load_cost_table_from_markdown(md_path: str) -> dict[str, tuple[int, int, int]]:
    """Parse a gate cost table from a markdown file.

    Expected format:
    | Operator | Exact | Approx | Lookup |
    |----------|-------|--------|--------|
    | Softmax  | 100000| 5000   | 1500   |
    """
    table = dict(DEFAULT_GATE_COSTS)  # start with defaults
    path = Path(md_path).resolve()

    if not path.exists():
        return table

    content = path.read_text(encoding="utf-8", errors="replace")
    for match in re.finditer(
        r"\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        content,
    ):
        op_name = match.group(1)
        if op_name.lower() not in ("operator", "---", ""):
            table[op_name] = (
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
            )

    return table


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def validate_json_path(path_str: str) -> dict:
    """Read and validate a JSON file."""
    path = Path(path_str).resolve()
    if ".." in Path(path_str).parts:
        print("ERROR: Path traversal (..) not allowed", file=sys.stderr)
        sys.exit(1)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python gate_cost_profiler.py <code_json> [--cost-table <gate_cost_table.md>]",
              file=sys.stderr)
        sys.exit(1)

    code_manifest = validate_json_path(sys.argv[1])

    # Optional: load custom cost table
    if "--cost-table" in sys.argv:
        idx = sys.argv.index("--cost-table")
        if idx + 1 < len(sys.argv):
            custom_table = load_cost_table_from_markdown(sys.argv[idx + 1])
            # Override default costs with custom ones (not used directly in profile_gates yet)
            DEFAULT_GATE_COSTS.update(custom_table)

    profile = profile_gates(code_manifest)
    print(json.dumps(asdict(profile), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
