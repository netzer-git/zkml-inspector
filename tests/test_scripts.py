#!/usr/bin/env python3
"""Tests for the zkml-inspector analysis scripts.

Run with:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the scripts directory to the path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / ".github" / "skills" / "analyze-zkml-gap" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from parse_paper import (
    PaperManifest,
    classify_operators,
    detect_approximations,
    extract_constraints,
    extract_math_blocks,
    extract_metadata,
    parse_paper,
    validate_path,
)
from inspect_codebase import (
    Framework,
    _classify_implementation,
    _detect_primary_language,
    _is_scannable,
    detect_framework,
    validate_path as validate_codebase_path,
)
from gate_cost_profiler import (
    DEFAULT_GATE_COSTS,
    estimate_operator_cost,
    load_cost_table_from_markdown,
    profile_gates,
)
from precision_checker import (
    check_precision_gaps,
    validate_json_path,
)


# ============================================================================
# Test fixtures
# ============================================================================

SAMPLE_LATEX = r"""
\documentclass{article}
\title{Test Paper on zkML}
\author{Test Author}
\begin{document}
\maketitle
\section{Introduction}
We present a zkML framework.

\section{Methods}
\subsection{Matrix Multiplication}
We use standard matrix multiplication:
\begin{equation}
Y_{ij} = \sum_k X_{ik} W_{kj}
\end{equation}

\subsection{Softmax}
We approximate the softmax function:
\begin{equation}
\operatorname{Softmax}(x_i) = \frac{e^{x_i}}{\sum_j e^{x_j}}
\end{equation}

Subject to: $\sum_i \operatorname{Softmax}(x_i) = 1$

We use a piecewise-linear approximation of softmax with K=8 segments.
The approximation error is bounded by 0.01.

\subsection{LayerNorm}
Layer normalization is defined as:
\begin{equation}
\operatorname{LayerNorm}(x) = \gamma \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta
\end{equation}

\subsection{Activation}
We use ReLU activation:
\begin{equation}
\operatorname{ReLU}(x) = \max(0, x)
\end{equation}

We also implement GELU via a lookup table for GELU.

\section{Security}
\begin{theorem}
The system is sound under the DL assumption.
\end{theorem}

Constraint: all weights must be committed using Poseidon hash.
Constraint: range checks enforce $x \in [-2^{15}, 2^{15}-1]$.

\end{document}
"""


@pytest.fixture
def sample_tex_file(tmp_path: Path) -> Path:
    """Create a temporary LaTeX file."""
    tex = tmp_path / "paper.tex"
    tex.write_text(SAMPLE_LATEX, encoding="utf-8")
    return tex


@pytest.fixture
def sample_code_dir(tmp_path: Path) -> Path:
    """Create a minimal mock codebase directory."""
    code_dir = tmp_path / "project"
    code_dir.mkdir()

    # Create a simple Rust file with operators
    src = code_dir / "src"
    src.mkdir()
    (src / "ops.rs").write_text(
        """
use halo2_proofs::*;

fn matmul(a: &Matrix, b: &Matrix) -> Matrix {
    // exact matrix multiplication
    a.dot(b)
}

fn relu(x: Field) -> Field {
    if x > Field::zero() { x } else { Field::zero() }
}

fn softmax(input: &[Field]) -> Vec<Field> {
    // piecewise-linear approximation with lookup table
    let table = lookup_table();
    input.iter().map(|x| table.lookup(*x)).collect()
}

fn sigmoid(x: Field) -> Field {
    // exact sigmoid - very expensive
    let exp_neg = exp(-x);
    Field::one() / (Field::one() + exp_neg)
}
""",
        encoding="utf-8",
    )

    # Create a Cargo.toml
    (code_dir / "Cargo.toml").write_text(
        """
[package]
name = "test-zkml"
version = "0.1.0"

[dependencies]
halo2_proofs = "0.3"
""",
        encoding="utf-8",
    )

    return code_dir


@pytest.fixture
def paper_manifest() -> dict:
    """Sample paper manifest JSON."""
    return {
        "source": "test.tex",
        "format": "latex",
        "operators": [
            {"name": "MatMul", "category": "linear", "math_definition": "", "location": "line 10", "is_transformer_killer": False},
            {"name": "Softmax", "category": "activation", "math_definition": "", "location": "line 20", "is_transformer_killer": True},
            {"name": "LayerNorm", "category": "normalization", "math_definition": "", "location": "line 30", "is_transformer_killer": True},
            {"name": "ReLU", "category": "activation", "math_definition": "", "location": "line 40", "is_transformer_killer": False},
        ],
        "constraints": [],
        "theorems": [],
        "approximations": [],
        "metadata": {},
    }


@pytest.fixture
def code_manifest() -> dict:
    """Sample code manifest JSON."""
    return {
        "codebase_path": "/test/project",
        "framework": {"name": "halo2", "language": "rust", "confidence": "high", "evidence": []},
        "operators": [
            {"name": "MatMul", "file": "src/ops.rs", "line": 4, "implementation_type": "exact"},
            {"name": "Softmax", "file": "src/ops.rs", "line": 15, "implementation_type": "approximation"},
            {"name": "ReLU", "file": "src/ops.rs", "line": 10, "implementation_type": "exact"},
            {"name": "Sigmoid", "file": "src/ops.rs", "line": 22, "implementation_type": "exact"},
        ],
        "constraints": [],
        "lookups": [],
        "precision_config": {"scale_bits": 12, "field_size": "", "quantization_method": "", "fixed_point_format": "", "evidence": ["scale=12"]},
        "files_scanned": 2,
    }


# ============================================================================
# parse_paper.py tests
# ============================================================================

class TestParsePaper:
    """Tests for paper parsing."""

    def test_parse_latex_finds_operators(self, sample_tex_file: Path) -> None:
        """Parsing a LaTeX file should find the operators mentioned in it."""
        manifest = parse_paper(str(sample_tex_file))
        op_names = {op.name for op in manifest.operators}
        assert "MatMul" in op_names or "Linear" in op_names
        assert "Softmax" in op_names
        assert "ReLU" in op_names

    def test_parse_latex_finds_theorems(self, sample_tex_file: Path) -> None:
        """Parsing should extract theorem environments."""
        manifest = parse_paper(str(sample_tex_file))
        assert len(manifest.theorems) >= 1

    def test_parse_latex_finds_constraints(self, sample_tex_file: Path) -> None:
        """Parsing should extract constraint statements."""
        manifest = parse_paper(str(sample_tex_file))
        assert len(manifest.constraints) >= 1

    def test_parse_latex_finds_approximations(self, sample_tex_file: Path) -> None:
        """Parsing should detect approximation methods."""
        manifest = parse_paper(str(sample_tex_file))
        assert len(manifest.approximations) >= 1
        approx_targets = [a.target_operation.lower() for a in manifest.approximations]
        assert any("softmax" in t for t in approx_targets)

    def test_parse_latex_metadata(self, sample_tex_file: Path) -> None:
        """Parsing should extract title and sections."""
        manifest = parse_paper(str(sample_tex_file))
        assert "title" in manifest.metadata
        assert "Test Paper" in manifest.metadata["title"]

    def test_extract_math_blocks_latex(self) -> None:
        """Math blocks should be extracted from LaTeX environments."""
        blocks = extract_math_blocks(SAMPLE_LATEX, "latex")
        assert len(blocks) > 0
        # Should find equation environments
        eq_blocks = [b for b in blocks if b.environment in ("equation", "displaymath")]
        assert len(eq_blocks) >= 3

    def test_classify_operators_transformer_killer(self) -> None:
        """Transformer killer operators should be flagged."""
        blocks = extract_math_blocks(SAMPLE_LATEX, "latex")
        operators = classify_operators(SAMPLE_LATEX, blocks)
        softmax = next((op for op in operators if op.name == "Softmax"), None)
        assert softmax is not None
        assert softmax.is_transformer_killer is True

    def test_classify_operators_not_transformer_killer(self) -> None:
        """Linear operators should NOT be flagged as transformer killers."""
        blocks = extract_math_blocks(SAMPLE_LATEX, "latex")
        operators = classify_operators(SAMPLE_LATEX, blocks)
        relu = next((op for op in operators if op.name == "ReLU"), None)
        assert relu is not None
        assert relu.is_transformer_killer is False

    def test_validate_path_rejects_traversal(self, tmp_path: Path) -> None:
        """Path with .. components should be rejected."""
        with pytest.raises(SystemExit):
            validate_path(str(tmp_path / ".." / "etc" / "passwd"))

    def test_validate_path_rejects_nonexistent(self) -> None:
        """Nonexistent path should cause exit."""
        with pytest.raises(SystemExit):
            validate_path("/nonexistent/file.tex")

    def test_detect_approximations(self) -> None:
        """Approximation detection should find piecewise-linear."""
        approxs = detect_approximations(SAMPLE_LATEX)
        assert len(approxs) >= 1
        methods = [a.method for a in approxs]
        assert "piecewise-linear" in methods

    def test_detect_lookup_approximation(self) -> None:
        """Should detect lookup table approximations."""
        text = "We use a lookup table for GELU activation."
        approxs = detect_approximations(text)
        assert len(approxs) >= 1
        assert any(a.method == "lookup-table" for a in approxs)

    def test_inequality_regex_no_false_positives(self) -> None:
        """The tightened inequality regex should not match casual prose."""
        text = "Our results are > baseline by 5%."
        blocks: list = []
        constraints = extract_constraints(text, blocks)
        inequality_constraints = [c for c in constraints if c.constraint_type == "inequality"]
        assert len(inequality_constraints) == 0

    def test_format_detection(self, sample_tex_file: Path) -> None:
        """Should detect LaTeX format correctly."""
        from parse_paper import read_source
        _, fmt = read_source(sample_tex_file)
        assert fmt == "latex"


# ============================================================================
# inspect_codebase.py tests
# ============================================================================

class TestInspectCodebase:
    """Tests for codebase inspection."""

    def test_detect_halo2_framework(self, sample_code_dir: Path) -> None:
        """Should detect halo2 framework from Cargo.toml."""
        fw = detect_framework(sample_code_dir)
        assert fw.name == "halo2"
        assert fw.language == "rust"

    def test_detect_primary_language(self, sample_code_dir: Path) -> None:
        """Should detect Rust as primary language."""
        lang = _detect_primary_language(sample_code_dir)
        assert lang == "rust"

    def test_is_scannable_skips_git(self, tmp_path: Path) -> None:
        """Should skip .git directory files."""
        git_file = tmp_path / ".git" / "config"
        git_file.parent.mkdir()
        git_file.write_text("test")
        assert _is_scannable(git_file) is False

    def test_is_scannable_skips_large_files(self, tmp_path: Path) -> None:
        """Should skip files larger than 2MB."""
        large_file = tmp_path / "big.rs"
        large_file.write_bytes(b"x" * (3 * 1024 * 1024))
        assert _is_scannable(large_file) is False

    def test_classify_implementation_lookup(self) -> None:
        """Code with 'lookup' nearby should classify as lookup."""
        content = "fn softmax(x: &[Field]) -> Vec<Field> { let table = lookup_table(); }"
        result = _classify_implementation("Softmax", content, 3)
        assert result == "lookup"

    def test_classify_implementation_approximation(self) -> None:
        """Code with 'approx' nearby should classify as approximation."""
        content = "fn sigmoid(x: Field) -> Field { // piecewise approximation }"
        result = _classify_implementation("Sigmoid", content, 3)
        assert result == "approximation"

    def test_classify_implementation_exact(self) -> None:
        """Code without lookup/approx keywords should classify as exact."""
        content = "fn relu(x: Field) -> Field { if x > 0 { x } else { 0 } }"
        result = _classify_implementation("ReLU", content, 3)
        assert result == "exact"

    def test_validate_path_rejects_traversal(self, tmp_path: Path) -> None:
        """Path with .. should be rejected."""
        with pytest.raises(SystemExit):
            validate_codebase_path(str(tmp_path / ".." / "etc"))

    def test_validate_path_rejects_file(self, sample_code_dir: Path) -> None:
        """Should reject a file path (expects directory)."""
        file_path = sample_code_dir / "Cargo.toml"
        with pytest.raises(SystemExit):
            validate_codebase_path(str(file_path))

    def test_circom_language_label(self) -> None:
        """Circom files should be labeled 'circom', not 'javascript'."""
        from inspect_codebase import FILE_EXTENSIONS
        assert FILE_EXTENSIONS[".circom"] == "circom"


# ============================================================================
# gate_cost_profiler.py tests
# ============================================================================

class TestGateCostProfiler:
    """Tests for gate cost profiling."""

    def test_estimate_known_operator_exact(self) -> None:
        """Known operator with exact impl should return correct cost."""
        cost = estimate_operator_cost("Softmax", "exact")
        assert cost == 100_000

    def test_estimate_known_operator_lookup(self) -> None:
        """Known operator with lookup should return lookup cost."""
        cost = estimate_operator_cost("Softmax", "lookup")
        assert cost == 1_500

    def test_estimate_unknown_operator(self) -> None:
        """Unknown operator should return default costs."""
        cost = estimate_operator_cost("CustomOp", "exact")
        assert cost == 1_000  # default for unknown

    def test_estimate_with_custom_table(self) -> None:
        """Custom cost table should override defaults."""
        custom = {"Softmax": (999, 888, 777)}
        cost = estimate_operator_cost("Softmax", "exact", custom)
        assert cost == 999

    def test_profile_gates_counts_total(self, code_manifest: dict) -> None:
        """Total gates should be the sum of individual operator costs."""
        profile = profile_gates(code_manifest)
        expected = sum(op.estimated_gates for op in profile.operators)
        assert profile.total_estimated_gates == expected

    def test_profile_gates_finds_transformer_killers(self, code_manifest: dict) -> None:
        """Should identify transformer killer operators."""
        profile = profile_gates(code_manifest)
        killer_names = {op.name for op in profile.transformer_killers}
        assert "Softmax" in killer_names
        assert "Sigmoid" in killer_names

    def test_profile_gates_custom_table_no_global_mutation(self) -> None:
        """Passing a custom cost table should NOT mutate DEFAULT_GATE_COSTS."""
        original_softmax = DEFAULT_GATE_COSTS["Softmax"]
        custom = {"Softmax": (1, 1, 1)}
        manifest = {"operators": [{"name": "Softmax", "implementation_type": "exact"}]}
        profile = profile_gates(manifest, custom)
        # The global dict should be unchanged
        assert DEFAULT_GATE_COSTS["Softmax"] == original_softmax
        # But the profile should use the custom cost
        assert profile.operators[0].estimated_gates == 1

    def test_profile_gates_bottlenecks_sorted(self, code_manifest: dict) -> None:
        """Top bottlenecks should be sorted by cost descending."""
        profile = profile_gates(code_manifest)
        if len(profile.top_bottlenecks) > 1:
            costs = [b.estimated_gates for b in profile.top_bottlenecks]
            assert costs == sorted(costs, reverse=True)

    def test_load_cost_table_from_markdown(self, tmp_path: Path) -> None:
        """Should parse a markdown table correctly."""
        md_content = """# Test Table
| Operator | Exact | Approx | Lookup | Notes |
|----------|-------|--------|--------|-------|
| TestOp   | 999   | 888    | 777    | test  |
"""
        md_file = tmp_path / "costs.md"
        md_file.write_text(md_content)
        table = load_cost_table_from_markdown(str(md_file))
        assert "TestOp" in table
        assert table["TestOp"] == (999, 888, 777)


# ============================================================================
# precision_checker.py tests
# ============================================================================

class TestPrecisionChecker:
    """Tests for precision checking."""

    def test_missing_operator_is_critical(self, paper_manifest: dict, code_manifest: dict) -> None:
        """Operator in paper but not in code should be CRITICAL."""
        report = check_precision_gaps(paper_manifest, code_manifest)
        critical_gaps = [g for g in report.gaps if g.severity == "CRITICAL"]
        missing_ops = [g for g in critical_gaps if "LayerNorm" in g.operator]
        assert len(missing_ops) >= 1

    def test_insufficient_precision_flagged(self, paper_manifest: dict, code_manifest: dict) -> None:
        """Operators needing more bits than code provides should be flagged."""
        report = check_precision_gaps(paper_manifest, code_manifest)
        precision_gaps = [
            g for g in report.gaps
            if g.operator == "Softmax" and "precision" in g.description.lower()
        ]
        assert len(precision_gaps) >= 1

    def test_approximation_operator_flagged(self, paper_manifest: dict, code_manifest: dict) -> None:
        """Approximation implementations should generate a WARNING."""
        report = check_precision_gaps(paper_manifest, code_manifest)
        approx_gaps = [
            g for g in report.gaps
            if g.severity == "WARNING" and "approximation" in g.description.lower()
        ]
        assert len(approx_gaps) >= 1

    def test_no_precision_config_warning(self, paper_manifest: dict) -> None:
        """Missing precision config should generate a WARNING."""
        code_no_precision = {
            "operators": [],
            "precision_config": {},
        }
        report = check_precision_gaps(paper_manifest, code_no_precision)
        global_gaps = [g for g in report.gaps if g.operator == "GLOBAL"]
        assert any("precision" in g.description.lower() for g in global_gaps)

    def test_total_checks_count_accurate(self, paper_manifest: dict, code_manifest: dict) -> None:
        """The total_checks count should reflect actual checks performed."""
        report = check_precision_gaps(paper_manifest, code_manifest)
        # Should not just be len(paper_operators) + 2
        # Should be: operators with known precision reqs + approximation ops + 2
        from precision_checker import OPERATOR_PRECISION_REQUIREMENTS
        expected_op_checks = sum(
            1 for op in paper_manifest["operators"]
            if op["name"] in OPERATOR_PRECISION_REQUIREMENTS
        )
        expected_approx = sum(
            1 for op in code_manifest["operators"]
            if op.get("implementation_type") == "approximation"
        )
        expected_total = expected_op_checks + expected_approx + 2
        assert report.summary["total_checks"] == expected_total

    def test_validate_json_path_rejects_traversal(self, tmp_path: Path) -> None:
        """Path with .. should be rejected."""
        with pytest.raises(SystemExit):
            validate_json_path(str(tmp_path / ".." / "secret.json"))

    def test_validate_json_path_valid(self, tmp_path: Path) -> None:
        """Valid JSON file should be parsed correctly."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        result = validate_json_path(str(json_file))
        assert result == {"key": "value"}

    def test_summary_counts(self, paper_manifest: dict, code_manifest: dict) -> None:
        """Summary should accurately count gaps by severity."""
        report = check_precision_gaps(paper_manifest, code_manifest)
        assert report.summary["gaps_found"] == len(report.gaps)
        assert report.summary["critical"] == sum(1 for g in report.gaps if g.severity == "CRITICAL")
        assert report.summary["warning"] == sum(1 for g in report.gaps if g.severity == "WARNING")
        assert report.summary["info"] == sum(1 for g in report.gaps if g.severity == "INFO")


# ============================================================================
# Cross-cutting / integration tests
# ============================================================================

class TestEndToEnd:
    """Integration tests across scripts."""

    def test_paper_output_is_valid_json(self, sample_tex_file: Path) -> None:
        """parse_paper output should be serializable as valid JSON."""
        from dataclasses import asdict
        manifest = parse_paper(str(sample_tex_file))
        json_str = json.dumps(asdict(manifest), ensure_ascii=False)
        parsed = json.loads(json_str)
        assert "operators" in parsed
        assert "constraints" in parsed

    def test_precision_checker_with_parsed_data(self, sample_tex_file: Path, code_manifest: dict) -> None:
        """Precision checker should work with data from parse_paper."""
        from dataclasses import asdict
        manifest = parse_paper(str(sample_tex_file))
        paper_dict = asdict(manifest)
        report = check_precision_gaps(paper_dict, code_manifest)
        assert report.summary["total_checks"] > 0

    def test_gate_profiler_with_empty_manifest(self) -> None:
        """Gate profiler should handle empty operator list gracefully."""
        manifest = {"operators": []}
        profile = profile_gates(manifest)
        assert profile.total_estimated_gates == 0
        assert len(profile.operators) == 0
        assert len(profile.top_bottlenecks) == 0
