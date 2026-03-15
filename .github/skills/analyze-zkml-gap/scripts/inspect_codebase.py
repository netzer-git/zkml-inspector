#!/usr/bin/env python3
"""inspect_codebase.py — Framework-agnostic zkML codebase inspector.

Usage:
    python inspect_codebase.py <codebase_path>

Output: JSON to stdout with structure:
    {
        "codebase_path": "...",
        "framework": { "name": "...", "language": "...", "confidence": "..." },
        "operators": [...],
        "constraints": [...],
        "lookups": [...],
        "precision_config": { ... },
        "files_scanned": 123
    }
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Framework:
    name: str         # ezkl, halo2, circom, python-generic, rust-generic, cpp, unknown
    language: str     # rust, python, javascript, c++, mixed
    confidence: str   # high, medium, low
    evidence: list[str] = field(default_factory=list)


@dataclass
class CodeOperator:
    name: str
    file: str
    line: int
    implementation_type: str  # exact, approximation, lookup, missing
    code_snippet: str = ""
    notes: str = ""


@dataclass
class CodeConstraint:
    description: str
    file: str
    line: int
    constraint_type: str  # arithmetic, range_check, lookup, commitment, custom_gate
    expression: str = ""


@dataclass
class LookupTable:
    name: str
    file: str
    line: int
    size: str = ""
    purpose: str = ""


@dataclass
class PrecisionConfig:
    scale_bits: int | None = None
    field_size: str = ""
    quantization_method: str = ""
    fixed_point_format: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class CodebaseManifest:
    codebase_path: str
    framework: Framework = field(default_factory=lambda: Framework("unknown", "unknown", "low"))
    operators: list[CodeOperator] = field(default_factory=list)
    constraints: list[CodeConstraint] = field(default_factory=list)
    lookups: list[LookupTable] = field(default_factory=list)
    precision_config: PrecisionConfig = field(default_factory=PrecisionConfig)
    files_scanned: int = 0


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

FRAMEWORK_SIGNALS: dict[str, list[tuple[str, str, str]]] = {
    # (file_pattern, content_pattern, evidence_label)
    "ezkl": [
        ("**/Cargo.toml", r"ezkl", "Cargo.toml references ezkl"),
        ("**/*.py", r"(?:import\s+ezkl|from\s+ezkl)", "Python imports ezkl"),
        ("**/input.json", r"input_data", "EZKL input.json found"),
        ("**/*.json", r'"scale":\s*\d+', "EZKL scale config found"),
        ("**/calibration.json", r".", "EZKL calibration.json found"),
    ],
    "halo2": [
        ("**/Cargo.toml", r"halo2", "Cargo.toml references halo2"),
        ("**/*.rs", r"use\s+halo2", "Rust imports halo2"),
        ("**/*.rs", r"impl\s+Circuit", "Circuit trait implementation"),
    ],
    "circom": [
        ("**/*.circom", r"template", "Circom template file found"),
        ("**/*.circom", r"signal\s+(?:input|output)", "Circom signal declarations"),
        ("**/circuit.json", r"constraints", "Circom circuit.json found"),
    ],
    "plonky2": [
        ("**/Cargo.toml", r"plonky2", "Cargo.toml references plonky2"),
        ("**/*.rs", r"use\s+plonky2", "Rust imports plonky2"),
    ],
}

FILE_EXTENSIONS = {
    ".rs": "rust",
    ".py": "python",
    ".circom": "circom",
    ".cpp": "c++",
    ".c": "c++",
    ".hpp": "c++",
    ".h": "c++",
    ".sol": "solidity",
}


def detect_framework(root: Path) -> Framework:
    """Auto-detect the zkML framework used in the codebase."""
    scores: dict[str, int] = {}
    evidence: dict[str, list[str]] = {}

    for fw_name, signals in FRAMEWORK_SIGNALS.items():
        scores[fw_name] = 0
        evidence[fw_name] = []
        for file_glob, content_pattern, label in signals:
            # rglob() already recurses, so strip the **/ prefix from glob patterns
            for fpath in root.rglob(file_glob.replace("**/", "")):
                if fpath.is_file() and _is_scannable(fpath):
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                        if re.search(content_pattern, content):
                            scores[fw_name] += 1
                            evidence[fw_name].append(f"{label} ({fpath.relative_to(root)})")
                    except (OSError, UnicodeDecodeError):
                        continue

    # Pick the framework with highest score
    if scores:
        best = max(scores, key=lambda k: scores[k])
        if scores[best] > 0:
            confidence = "high" if scores[best] >= 3 else "medium" if scores[best] >= 2 else "low"
            lang = _detect_primary_language(root)
            return Framework(
                name=best,
                language=lang,
                confidence=confidence,
                evidence=evidence[best],
            )

    # Fallback: detect by language
    lang = _detect_primary_language(root)
    return Framework(name="unknown", language=lang, confidence="low",
                     evidence=["No known zkML framework detected"])


def _detect_primary_language(root: Path) -> str:
    """Detect the primary language by file extension frequency."""
    lang_count: dict[str, int] = {}
    for fpath in root.rglob("*"):
        if fpath.is_file():
            lang = FILE_EXTENSIONS.get(fpath.suffix.lower())
            if lang:
                lang_count[lang] = lang_count.get(lang, 0) + 1
    if lang_count:
        return max(lang_count, key=lambda k: lang_count[k])
    return "unknown"


def _is_scannable(path: Path) -> bool:
    """Check if a file should be scanned (skip binaries, large files, vendor dirs)."""
    skip_dirs = {
        "node_modules", ".git", "target", "__pycache__", ".venv", "venv",
        "build", "dist", ".eggs", ".tox",
    }
    if any(part in skip_dirs for part in path.parts):
        return False
    if path.stat().st_size > 2 * 1024 * 1024:  # Skip files > 2MB
        return False
    return path.suffix.lower() in FILE_EXTENSIONS or path.suffix.lower() in {
        ".toml", ".json", ".yaml", ".yml", ".txt", ".md", ".cfg",
    }


# ---------------------------------------------------------------------------
# Operator extraction
# ---------------------------------------------------------------------------

# Patterns for each language to detect operator implementations
RUST_OPERATOR_PATTERNS: dict[str, str] = {
    "MatMul": r"(?:matmul|matrix_mul|dot_product|gemm)",
    "Conv2D": r"(?:conv2d|convolution|conv_layer)",
    "ReLU": r"(?:relu|rectified_linear|max\(.*?,\s*0\))",
    "Softmax": r"(?:softmax|soft_max)",
    "LayerNorm": r"(?:layer_norm|layernorm|layer_normalization)",
    "BatchNorm": r"(?:batch_norm|batchnorm|batch_normalization)",
    "Sigmoid": r"(?:sigmoid|logistic)",
    "Tanh": r"(?:tanh|hyperbolic_tangent)",
    "GELU": r"(?:gelu|gaussian_error_linear)",
    "Attention": r"(?:attention|self_attention|multi_head)",
    "Add": r"(?:add_gate|element_add|residual_add)",
    "Mul": r"(?:mul_gate|element_mul|hadamard)",
    "MaxPool": r"(?:max_pool|maxpool)",
    "AvgPool": r"(?:avg_pool|avgpool|average_pool)",
    "Lookup": r"(?:lookup_table|lookup|table_lookup)",
    "RangeCheck": r"(?:range_check|range_proof|bound_check)",
}

PYTHON_OPERATOR_PATTERNS: dict[str, str] = {
    "MatMul": r"(?:matmul|mm\(|torch\.mm|np\.dot|linear\(|nn\.Linear)",
    "Conv2D": r"(?:conv2d|nn\.Conv2d|F\.conv2d)",
    "ReLU": r"(?:relu|nn\.ReLU|F\.relu)",
    "Softmax": r"(?:softmax|nn\.Softmax|F\.softmax)",
    "LayerNorm": r"(?:layer_norm|nn\.LayerNorm|F\.layer_norm)",
    "BatchNorm": r"(?:batch_norm|nn\.BatchNorm|F\.batch_norm)",
    "Sigmoid": r"(?:sigmoid|nn\.Sigmoid|F\.sigmoid|torch\.sigmoid)",
    "Tanh": r"(?:tanh|nn\.Tanh|torch\.tanh)",
    "GELU": r"(?:gelu|nn\.GELU|F\.gelu)",
    "Attention": r"(?:attention|MultiheadAttention|self_attn)",
    "Dropout": r"(?:dropout|nn\.Dropout)",
}

CIRCOM_OPERATOR_PATTERNS: dict[str, str] = {
    "MatMul": r"(?:MatMul|matMul|MatrixMultiply)",
    "Conv2D": r"(?:Conv2D|Conv2d|Convolution)",
    "ReLU": r"(?:ReLU|Relu|IsPositive)",
    "Softmax": r"(?:Softmax|SoftMax)",
    "Sigmoid": r"(?:Sigmoid)",
    "Tanh": r"(?:Tanh)",
    "Add": r"(?:Add\(|Adder)",
    "Mul": r"(?:Mul\(|Multiplier)",
}


def extract_operators(root: Path, framework: Framework) -> list[CodeOperator]:
    """Extract operator implementations from the codebase."""
    operators: list[CodeOperator] = []
    seen: set[str] = set()

    patterns = _get_operator_patterns(framework)
    extensions = _get_extensions(framework)

    for fpath in root.rglob("*"):
        if not fpath.is_file() or not _is_scannable(fpath):
            continue
        if fpath.suffix.lower() not in extensions:
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        for op_name, pattern in patterns.items():
            for match in re.finditer(pattern, content, re.IGNORECASE):
                key = f"{op_name}:{fpath}"
                if key in seen:
                    continue
                seen.add(key)

                line_no = content[:match.start()].count("\n") + 1
                # Get a snippet of surrounding code
                lines = content.splitlines()
                start = max(0, line_no - 2)
                end = min(len(lines), line_no + 3)
                snippet = "\n".join(lines[start:end])

                impl_type = _classify_implementation(op_name, content, match.start())

                operators.append(CodeOperator(
                    name=op_name,
                    file=str(fpath.relative_to(root)),
                    line=line_no,
                    implementation_type=impl_type,
                    code_snippet=snippet[:500],
                ))

    return operators


def _get_operator_patterns(framework: Framework) -> dict[str, str]:
    """Get language-appropriate operator patterns."""
    if framework.language == "rust":
        return RUST_OPERATOR_PATTERNS
    elif framework.language == "python":
        return PYTHON_OPERATOR_PATTERNS
    elif framework.name == "circom":
        return CIRCOM_OPERATOR_PATTERNS
    else:
        # Merge all patterns for unknown frameworks, combining overlapping keys
        merged = dict(RUST_OPERATOR_PATTERNS)
        for key, pattern in PYTHON_OPERATOR_PATTERNS.items():
            if key in merged:
                merged[key] = f"(?:{merged[key]}|{pattern})"
            else:
                merged[key] = pattern
        return merged


def _get_extensions(framework: Framework) -> set[str]:
    """Get relevant file extensions for the framework."""
    if framework.language == "rust":
        return {".rs", ".toml"}
    elif framework.language == "python":
        return {".py"}
    elif framework.name == "circom":
        return {".circom", ".js"}
    elif framework.language == "c++":
        return {".cpp", ".hpp", ".c", ".h"}
    else:
        return set(FILE_EXTENSIONS.keys())


def _classify_implementation(op_name: str, content: str, pos: int) -> str:
    """Classify whether an operator is exact, approximation, or lookup-based."""
    region = content[max(0, pos - 200):pos + 500].lower()

    if any(kw in region for kw in ["lookup", "table", "lut"]):
        return "lookup"
    if any(kw in region for kw in ["approx", "piecewise", "taylor", "chebyshev", "polynomial"]):
        return "approximation"
    return "exact"


# ---------------------------------------------------------------------------
# Constraint extraction
# ---------------------------------------------------------------------------

def extract_constraints(root: Path, framework: Framework) -> list[CodeConstraint]:
    """Extract constraint definitions from the codebase."""
    constraints: list[CodeConstraint] = []
    extensions = _get_extensions(framework)

    constraint_patterns: list[tuple[str, str]] = []

    if framework.language == "rust":
        constraint_patterns = [
            (r"(?:region\.assign_advice|assign_fixed|constrain_equal|enforce_equal)", "arithmetic"),
            (r"(?:range_check|check_range|bound_check)", "range_check"),
            (r"(?:lookup\.input_expressions|lookup_table)", "lookup"),
            (r"(?:create_gate|gate\(|custom_gate)", "custom_gate"),
            (r"(?:instance_column|commit|commitment)", "commitment"),
        ]
    elif framework.language == "python":
        constraint_patterns = [
            (r"(?:assert_equal|constrain|check_constraint)", "arithmetic"),
            (r"(?:range_check|check_range|clip|clamp)", "range_check"),
            (r"(?:lookup|table|quantize)", "lookup"),
        ]
    elif framework.name == "circom":
        constraint_patterns = [
            (r"===", "arithmetic"),
            (r"(?:assert|Num2Bits|range_proof)", "range_check"),
            (r"<==", "assignment"),
        ]

    for fpath in root.rglob("*"):
        if not fpath.is_file() or not _is_scannable(fpath):
            continue
        if fpath.suffix.lower() not in extensions:
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        for pattern, ctype in constraint_patterns:
            for match in re.finditer(pattern, content):
                line_no = content[:match.start()].count("\n") + 1
                lines = content.splitlines()
                expr_line = lines[line_no - 1] if line_no <= len(lines) else ""

                constraints.append(CodeConstraint(
                    description=f"{ctype} constraint",
                    file=str(fpath.relative_to(root)),
                    line=line_no,
                    constraint_type=ctype,
                    expression=expr_line.strip()[:200],
                ))

    return constraints


# ---------------------------------------------------------------------------
# Lookup table extraction
# ---------------------------------------------------------------------------

def extract_lookups(root: Path, framework: Framework) -> list[LookupTable]:
    """Extract lookup table definitions."""
    lookups: list[LookupTable] = []
    extensions = _get_extensions(framework)

    lookup_patterns = [
        r"(?:lookup_table|LookupTable|lookup_config)",
        r"(?:TableColumn|table_column|fixed_table)",
        r"(?:create_lookup|lookup_any|lookup_advice)",
    ]

    for fpath in root.rglob("*"):
        if not fpath.is_file() or not _is_scannable(fpath):
            continue
        if fpath.suffix.lower() not in extensions:
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        for pattern in lookup_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_no = content[:match.start()].count("\n") + 1
                lookups.append(LookupTable(
                    name=match.group(0),
                    file=str(fpath.relative_to(root)),
                    line=line_no,
                ))

    return lookups


# ---------------------------------------------------------------------------
# Precision configuration extraction
# ---------------------------------------------------------------------------

def extract_precision_config(root: Path, framework: Framework) -> PrecisionConfig:
    """Extract fixed-point precision configuration."""
    config = PrecisionConfig()

    if framework.name == "ezkl":
        config = _extract_ezkl_precision(root)
    elif framework.name == "halo2":
        config = _extract_halo2_precision(root)
    else:
        config = _extract_generic_precision(root)

    return config


def _extract_ezkl_precision(root: Path) -> PrecisionConfig:
    """Extract EZKL-specific precision config."""
    config = PrecisionConfig(quantization_method="ezkl-quantization")

    # Look for scale parameters in JSON config files
    for fpath in root.rglob("*.json"):
        if not _is_scannable(fpath):
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            data = json.loads(content)
        except (OSError, json.JSONDecodeError):
            continue

        if "scale" in data:
            if config.scale_bits is not None and config.scale_bits != data["scale"]:
                print(
                    f"WARNING: Conflicting scale config: was {config.scale_bits}, "
                    f"now {data['scale']} (in {fpath.relative_to(root)})",
                    file=sys.stderr,
                )
            config.scale_bits = data["scale"]
            config.evidence.append(f"scale={data['scale']} in {fpath.relative_to(root)}")
        if "bits" in data:
            if config.scale_bits is not None and config.scale_bits != data["bits"]:
                print(
                    f"WARNING: Conflicting bits config: was {config.scale_bits}, "
                    f"now {data['bits']} (in {fpath.relative_to(root)})",
                    file=sys.stderr,
                )
            config.scale_bits = data["bits"]
            config.evidence.append(f"bits={data['bits']} in {fpath.relative_to(root)}")
        if "input_scale" in data:
            config.evidence.append(f"input_scale={data['input_scale']} in {fpath.relative_to(root)}")

    return config


def _extract_halo2_precision(root: Path) -> PrecisionConfig:
    """Extract Halo2-specific precision config."""
    config = PrecisionConfig(quantization_method="halo2-field")

    for fpath in root.rglob("*.rs"):
        if not _is_scannable(fpath):
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        # Look for field size and K value
        k_match = re.search(r"(?:let\s+k|const\s+K)\s*[:=]\s*(\d+)", content)
        if k_match:
            config.field_size = f"2^{k_match.group(1)}"
            config.evidence.append(f"K={k_match.group(1)} in {fpath.relative_to(root)}")

        # Look for fixed-point scale
        scale_match = re.search(r"(?:SCALE|scale|precision)\s*[:=]\s*(\d+)", content)
        if scale_match:
            config.scale_bits = int(scale_match.group(1))
            config.evidence.append(f"scale={scale_match.group(1)} in {fpath.relative_to(root)}")

    return config


def _extract_generic_precision(root: Path) -> PrecisionConfig:
    """Extract precision config from unknown frameworks."""
    config = PrecisionConfig()

    for fpath in root.rglob("*"):
        if not fpath.is_file() or not _is_scannable(fpath):
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        # Look for quantization keywords
        quant_match = re.search(
            r"(?:quantiz\w+|fixed[\s_]point|scale[\s_]?bits|precision)\s*[:=]\s*(\d+)",
            content, re.IGNORECASE,
        )
        if quant_match:
            config.scale_bits = int(quant_match.group(1))
            config.evidence.append(f"precision={quant_match.group(1)} in {fpath.name}")

        bits_match = re.search(r"(?:num_bits|bit_width|n_bits)\s*[:=]\s*(\d+)", content)
        if bits_match:
            config.scale_bits = int(bits_match.group(1))
            config.evidence.append(f"bits={bits_match.group(1)} in {fpath.name}")

    return config


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def validate_path(path_str: str) -> Path:
    """Validate and resolve the input path securely."""
    # Reject path traversal BEFORE resolving to prevent bypass
    if ".." in Path(path_str).parts:
        print("ERROR: Path traversal (..) not allowed", file=sys.stderr)
        sys.exit(1)
    path = Path(path_str).resolve()
    if not path.exists():
        print(f"ERROR: Path not found: {path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_dir():
        print(f"ERROR: Not a directory: {path}", file=sys.stderr)
        sys.exit(1)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def inspect_codebase(codebase_path: str) -> CodebaseManifest:
    """Main entry point: inspect a codebase and return structured manifest."""
    root = validate_path(codebase_path)
    framework = detect_framework(root)

    operators = extract_operators(root, framework)
    constraints = extract_constraints(root, framework)
    lookups = extract_lookups(root, framework)
    precision = extract_precision_config(root, framework)

    file_count = sum(1 for f in root.rglob("*") if f.is_file() and _is_scannable(f))

    return CodebaseManifest(
        codebase_path=str(root),
        framework=framework,
        operators=operators,
        constraints=constraints,
        lookups=lookups,
        precision_config=precision,
        files_scanned=file_count,
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python inspect_codebase.py <codebase_path>", file=sys.stderr)
        sys.exit(1)

    manifest = inspect_codebase(sys.argv[1])
    print(json.dumps(asdict(manifest), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
