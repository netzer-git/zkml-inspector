#!/usr/bin/env python3
"""precision_checker.py — Compare fixed-point precision between paper and code.

Usage:
    python precision_checker.py <paper_json> <code_json>

    Where paper_json and code_json are the JSON outputs from
    parse_paper.py and inspect_codebase.py respectively.

Output: JSON to stdout with structure:
    {
        "gaps": [...],
        "summary": { "total_checks": N, "gaps_found": M, "critical": C, "warning": W }
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
class PrecisionGap:
    operator: str
    severity: str  # CRITICAL, WARNING, INFO
    description: str
    paper_precision: str
    code_precision: str
    recommendation: str
    location: str = ""


@dataclass
class PrecisionReport:
    gaps: list[PrecisionGap] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Known precision requirements for common operators
# ---------------------------------------------------------------------------

# Minimum bits of precision typically required for accurate operator execution
OPERATOR_PRECISION_REQUIREMENTS: dict[str, int] = {
    "Softmax": 16,      # Requires exp() — needs high precision to avoid overflow
    "LayerNorm": 14,     # Involves mean, variance, division — accumulates error
    "BatchNorm": 14,     # Similar to LayerNorm
    "GELU": 14,          # Non-polynomial — approximation error compounds
    "Sigmoid": 12,       # Range [-∞, +∞] → [0, 1] — sensitive to precision
    "Tanh": 12,          # Range [-∞, +∞] → [-1, 1] — sensitive to precision
    "SiLU": 14,          # x * sigmoid(x) — compounds errors
    "Attention": 16,     # Softmax + MatMul chain — error accumulates
    "MatMul": 10,        # Accumulation error scales with dimension
    "Conv2D": 10,        # Similar accumulation pattern to MatMul
    "ReLU": 8,           # Simple threshold — forgiving
    "Add": 8,            # Direct — minimal precision needs
    "Mul": 10,           # Product — needs moderate precision
    "MaxPool": 8,        # Comparison only
    "AvgPool": 10,       # Division — moderate needs
}


# ---------------------------------------------------------------------------
# Precision analysis
# ---------------------------------------------------------------------------

def check_precision_gaps(
    paper_manifest: dict,
    code_manifest: dict,
) -> PrecisionReport:
    """Compare precision requirements between paper and implementation."""
    gaps: list[PrecisionGap] = []

    paper_operators = {op["name"]: op for op in paper_manifest.get("operators", [])}
    code_operators = {op["name"]: op for op in code_manifest.get("operators", [])}
    precision_config = code_manifest.get("precision_config", {})

    code_bits = precision_config.get("scale_bits")

    # Check 1: Each paper operator against code precision
    for op_name, paper_op in paper_operators.items():
        required_bits = OPERATOR_PRECISION_REQUIREMENTS.get(op_name)
        if required_bits is None:
            continue

        code_op = code_operators.get(op_name)

        # Check if operator exists in code
        if not code_op:
            gaps.append(PrecisionGap(
                operator=op_name,
                severity="CRITICAL",
                description=f"Operator '{op_name}' is defined in paper but not found in code",
                paper_precision=f"Requires ≥{required_bits} bits",
                code_precision="NOT IMPLEMENTED",
                recommendation=f"Implement {op_name} with at least {required_bits}-bit fixed-point precision",
                location=paper_op.get("location", ""),
            ))
            continue

        # Check if code has sufficient precision
        if code_bits is not None and code_bits < required_bits:
            severity = "CRITICAL" if (required_bits - code_bits) >= 4 else "WARNING"
            gaps.append(PrecisionGap(
                operator=op_name,
                severity=severity,
                description=(
                    f"Operator '{op_name}' requires ≥{required_bits}-bit precision "
                    f"but code uses {code_bits}-bit fixed-point"
                ),
                paper_precision=f"≥{required_bits} bits (standard requirement for {op_name})",
                code_precision=f"{code_bits} bits (from config: {precision_config.get('evidence', ['unknown'])})",
                recommendation=(
                    f"Increase precision to at least {required_bits} bits for {op_name}, "
                    f"or use a lookup table / piecewise approximation with bounded error"
                ),
                location=code_op.get("file", ""),
            ))

    # Check 2: Approximation operators — do they have sufficient precision?
    for op_name, code_op in code_operators.items():
        if code_op.get("implementation_type") == "approximation":
            required_bits = OPERATOR_PRECISION_REQUIREMENTS.get(op_name, 12)
            gaps.append(PrecisionGap(
                operator=op_name,
                severity="WARNING",
                description=(
                    f"Operator '{op_name}' uses an approximation — verify error bound "
                    f"is within acceptable range for {code_bits or 'unknown'}-bit precision"
                ),
                paper_precision=f"Exact or ≥{required_bits}-bit approximation",
                code_precision=f"Approximation in {code_op.get('file', 'unknown')}",
                recommendation=(
                    f"Verify that the approximation error for {op_name} is bounded by "
                    f"2^(-{required_bits}) across the expected input range"
                ),
                location=code_op.get("file", ""),
            ))

    # Check 3: If no precision config found at all, flag it
    if code_bits is None and not precision_config.get("evidence"):
        gaps.append(PrecisionGap(
            operator="GLOBAL",
            severity="WARNING",
            description="No fixed-point precision configuration detected in codebase",
            paper_precision="Paper may assume floating-point arithmetic",
            code_precision="No precision config found",
            recommendation=(
                "Define explicit precision parameters (scale bits, quantization method) "
                "in a configuration file. This is essential for reproducible ZK proofs."
            ),
        ))

    # Check 4: Floating-point keywords in paper vs fixed-point code
    paper_mentions_float = _check_paper_float_assumption(paper_manifest)
    if paper_mentions_float and code_bits is not None:
        gaps.append(PrecisionGap(
            operator="GLOBAL",
            severity="INFO",
            description="Paper appears to assume floating-point arithmetic but code uses fixed-point",
            paper_precision="Floating-point (IEEE 754 implied)",
            code_precision=f"Fixed-point with {code_bits} bits",
            recommendation=(
                "Verify that the quantization from float to fixed-point preserves "
                "the paper's accuracy guarantees. Document the quantization error bound."
            ),
        ))

    # Summary
    report = PrecisionReport(
        gaps=gaps,
        summary={
            "total_checks": len(paper_operators) + 2,  # +2 for global checks
            "gaps_found": len(gaps),
            "critical": sum(1 for g in gaps if g.severity == "CRITICAL"),
            "warning": sum(1 for g in gaps if g.severity == "WARNING"),
            "info": sum(1 for g in gaps if g.severity == "INFO"),
        },
    )

    return report


def _check_paper_float_assumption(paper_manifest: dict) -> bool:
    """Check if the paper assumes floating-point arithmetic."""
    # Look through constraints and theorems for float indicators
    for constraint in paper_manifest.get("constraints", []):
        desc = constraint.get("description", "").lower()
        if any(kw in desc for kw in ["float", "real-valued", "continuous", "ℝ", "\\mathbb{r}"]):
            return True

    for theorem in paper_manifest.get("theorems", []):
        stmt = theorem.get("statement", "").lower()
        if any(kw in stmt for kw in ["float", "real", "continuous"]):
            return True

    return False


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
    if len(sys.argv) != 3:
        print("Usage: python precision_checker.py <paper_json> <code_json>", file=sys.stderr)
        sys.exit(1)

    paper_manifest = validate_json_path(sys.argv[1])
    code_manifest = validate_json_path(sys.argv[2])

    report = check_precision_gaps(paper_manifest, code_manifest)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
