#!/usr/bin/env python3
"""parse_paper.py — Extract mathematical constraints, operators, and approximations from LaTeX/PDF papers.

Usage:
    python parse_paper.py <paper_path>

Output: JSON to stdout with structure:
    {
        "source": "<file_path>",
        "format": "latex" | "pdf",
        "operators": [...],
        "constraints": [...],
        "theorems": [...],
        "approximations": [],
        "metadata": { "title": ..., "sections": [...] }
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
class MathBlock:
    """A raw mathematical expression extracted from the paper."""
    content: str
    environment: str  # equation, align, theorem, definition, etc.
    line_number: int
    section: str = ""


@dataclass
class Operator:
    """A mathematical operator found in the paper."""
    name: str
    category: str  # linear, nonlinear, normalization, activation, pooling
    math_definition: str
    location: str  # section or line reference
    is_transformer_killer: bool = False


@dataclass
class Constraint:
    """A constraint or proof obligation from the paper."""
    description: str
    math_expression: str
    constraint_type: str  # equality, inequality, range, commitment
    location: str


@dataclass
class Theorem:
    """A theorem, lemma, or proposition from the paper."""
    label: str  # Theorem 1, Lemma 2, etc.
    statement: str
    location: str
    proof_sketch: str = ""


@dataclass
class Approximation:
    """An approximation strategy described in the paper."""
    target_operation: str  # what is being approximated (e.g., Softmax)
    method: str  # piecewise-linear, polynomial, lookup, etc.
    description: str
    error_bound: str  # stated error bound if any
    location: str


@dataclass
class PaperManifest:
    """Complete parsed output from a paper."""
    source: str
    format: str
    operators: list[Operator] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    theorems: list[Theorem] = field(default_factory=list)
    approximations: list[Approximation] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Transformer-killer keywords
# ---------------------------------------------------------------------------

TRANSFORMER_KILLERS = {
    "softmax", "layernorm", "layer_norm", "layer normalization",
    "gelu", "sigmoid", "tanh", "silu", "swish", "mish",
    "batch normalization", "batchnorm", "group normalization", "groupnorm",
}

OPERATOR_PATTERNS: dict[str, str] = {
    "MatMul": r"(?:matmul|matrix\s*multiply|matrix\s*multiplication|\bgemm\b)",
    "Conv2D": r"(?:conv(?:olution)?(?:\s*2d)?|convolution\s*layer)",
    "Conv1D": r"(?:conv(?:olution)?\s*1d)",
    "ReLU": r"\brelu\b",
    "Softmax": r"\bsoftmax\b",
    "LayerNorm": r"(?:layer\s*norm(?:alization)?)",
    "BatchNorm": r"(?:batch\s*norm(?:alization)?)",
    "GroupNorm": r"(?:group\s*norm(?:alization)?)",
    "Sigmoid": r"\bsigmoid\b",
    "Tanh": r"\btanh\b",
    "GELU": r"\bgelu\b",
    "SiLU": r"(?:\bsilu\b|\bswish\b)",
    "Add": r"(?:element[\-\s]?wise\s*add(?:ition)?|residual\s*(?:add|connection))",
    "Mul": r"(?:element[\-\s]?wise\s*mult(?:iplication)?|hadamard\s*product)",
    "MaxPool": r"(?:max[\s_]?pool(?:ing)?)",
    "AvgPool": r"(?:avg[\s_]?pool(?:ing)?|average[\s_]?pool(?:ing)?)",
    "Attention": r"(?:(?:self[\-\s]?)?attention|multi[\-\s]?head[\-\s]?attention|\bmha\b)",
    "Linear": r"(?:(?:fully[\-\s]?connected|dense|linear)\s*layer)",
    "Embedding": r"\bembedding\b",
    "Dropout": r"\bdropout\b",
}

OPERATOR_CATEGORIES: dict[str, str] = {
    "MatMul": "linear", "Conv2D": "linear", "Conv1D": "linear",
    "Linear": "linear", "Embedding": "linear",
    "ReLU": "activation", "Sigmoid": "activation", "Tanh": "activation",
    "GELU": "activation", "SiLU": "activation",
    "Softmax": "activation",
    "LayerNorm": "normalization", "BatchNorm": "normalization", "GroupNorm": "normalization",
    "Add": "arithmetic", "Mul": "arithmetic",
    "MaxPool": "pooling", "AvgPool": "pooling",
    "Attention": "composite", "Dropout": "regularization",
}


# ---------------------------------------------------------------------------
# LaTeX extraction
# ---------------------------------------------------------------------------

def read_source(path: Path) -> tuple[str, str]:
    """Read file and determine format. Returns (text, format)."""
    suffix = path.suffix.lower()
    if suffix == ".tex":
        return path.read_text(encoding="utf-8", errors="replace"), "latex"
    elif suffix == ".pdf":
        return _extract_pdf_text(path), "pdf"
    else:
        # Try as plaintext (could be .txt export)
        return path.read_text(encoding="utf-8", errors="replace"), "text"


def _extract_pdf_text(path: Path) -> str:
    """Extract text from PDF using pymupdf4llm (Markdown output)."""
    try:
        import pymupdf4llm  # type: ignore[import-untyped]
        return pymupdf4llm.to_markdown(str(path))
    except ImportError:
        print(
            "WARNING: pymupdf4llm not installed. Install with: pip install pymupdf4llm",
            file=sys.stderr,
        )
        # Fallback: try pymupdf directly
        try:
            import pymupdf  # type: ignore[import-untyped]
            doc = pymupdf.open(str(path))
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)
        except ImportError:
            print("ERROR: Neither pymupdf4llm nor pymupdf installed.", file=sys.stderr)
            sys.exit(1)


def extract_math_blocks(text: str, fmt: str) -> list[MathBlock]:
    """Extract mathematical environments from LaTeX or Markdown-converted text."""
    blocks: list[MathBlock] = []

    if fmt == "latex":
        blocks.extend(_extract_latex_environments(text))
    else:
        # PDF-converted markdown or plain text: look for $...$ and $$...$$
        blocks.extend(_extract_markdown_math(text))

    # Also extract inline math patterns in both cases
    blocks.extend(_extract_inline_operators(text))

    return blocks


def _extract_latex_environments(text: str) -> list[MathBlock]:
    """Extract \\begin{env}...\\end{env} blocks from LaTeX."""
    blocks: list[MathBlock] = []
    env_pattern = re.compile(
        r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|"
        r"theorem|lemma|proposition|definition|corollary|proof|remark)\}"
        r"(.*?)"
        r"\\end\{\1\}",
        re.DOTALL,
    )
    current_section = ""
    for match in re.finditer(r"\\(?:section|subsection)\{([^}]+)\}", text):
        section_name = match.group(1)
        # Store section context
        current_section = section_name

    for match in env_pattern.finditer(text):
        env_name = match.group(1).rstrip("*")
        content = match.group(2).strip()
        line_no = text[:match.start()].count("\n") + 1

        # Determine current section from position
        section = ""
        for sec_match in re.finditer(r"\\(?:section|subsection)\{([^}]+)\}", text[:match.start()]):
            section = sec_match.group(1)

        blocks.append(MathBlock(
            content=content,
            environment=env_name,
            line_number=line_no,
            section=section,
        ))

    # Also grab display math: \[ ... \]
    for match in re.finditer(r"\\\[(.*?)\\\]", text, re.DOTALL):
        line_no = text[:match.start()].count("\n") + 1
        section = ""
        for sec_match in re.finditer(r"\\(?:section|subsection)\{([^}]+)\}", text[:match.start()]):
            section = sec_match.group(1)
        blocks.append(MathBlock(
            content=match.group(1).strip(),
            environment="displaymath",
            line_number=line_no,
            section=section,
        ))

    return blocks


def _extract_markdown_math(text: str) -> list[MathBlock]:
    """Extract math from Markdown-format text ($$...$$ and $...$)."""
    blocks: list[MathBlock] = []

    # Display math: $$...$$
    for match in re.finditer(r"\$\$(.*?)\$\$", text, re.DOTALL):
        line_no = text[:match.start()].count("\n") + 1
        blocks.append(MathBlock(
            content=match.group(1).strip(),
            environment="displaymath",
            line_number=line_no,
        ))

    return blocks


def _extract_inline_operators(text: str) -> list[MathBlock]:
    """Extract operatorname{} and known operator references."""
    blocks: list[MathBlock] = []

    # \operatorname{...} patterns
    for match in re.finditer(r"\\operatorname\{([^}]+)\}", text):
        line_no = text[:match.start()].count("\n") + 1
        blocks.append(MathBlock(
            content=match.group(0),
            environment="inline",
            line_number=line_no,
        ))

    return blocks


# ---------------------------------------------------------------------------
# Operator classification
# ---------------------------------------------------------------------------

def classify_operators(text: str, blocks: list[MathBlock]) -> list[Operator]:
    """Identify operators mentioned in the paper."""
    found: dict[str, Operator] = {}

    full_text = text.lower()
    for op_name, pattern in OPERATOR_PATTERNS.items():
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if matches:
            first_match = matches[0]
            line_no = text[:first_match.start()].count("\n") + 1

            # Find nearby math definition
            math_def = _find_math_definition(op_name, blocks)

            is_killer = op_name.lower() in TRANSFORMER_KILLERS or any(
                op_name.lower() in k for k in TRANSFORMER_KILLERS
            )

            found[op_name] = Operator(
                name=op_name,
                category=OPERATOR_CATEGORIES.get(op_name, "unknown"),
                math_definition=math_def,
                location=f"line {line_no} (first mention, {len(matches)} total references)",
                is_transformer_killer=is_killer,
            )

    return list(found.values())


def _find_math_definition(op_name: str, blocks: list[MathBlock]) -> str:
    """Try to find a mathematical definition for an operator in the extracted blocks."""
    op_lower = op_name.lower()
    for block in blocks:
        if op_lower in block.content.lower():
            # Return the first equation-like block that mentions this operator
            if block.environment in ("equation", "align", "displaymath", "definition"):
                return block.content[:500]  # truncate long definitions
    return ""


# ---------------------------------------------------------------------------
# Constraint extraction
# ---------------------------------------------------------------------------

def extract_constraints(text: str, blocks: list[MathBlock]) -> list[Constraint]:
    """Extract constraint-like statements from the paper."""
    constraints: list[Constraint] = []

    constraint_keywords = [
        (r"(?:subject\s+to|s\.t\.)\s*[:;]?\s*(.{10,200})", "equality"),
        (r"(?:constraint|enforce|ensure|require|must\s+satisfy)\s*[:;]?\s*(.{10,200})", "equality"),
        (r"(?:range\s+(?:check|proof|constraint))\s*[:;]?\s*(.{10,200})", "range"),
        (r"(?:commit(?:ment)?(?:\s+to)?)\s*[:;]?\s*(.{10,200})", "commitment"),
        (r"(\w+\s*[<>≤≥]=?\s*\w+(?:\s*[<>≤≥]=?\s*\w+)?)", "inequality"),
    ]

    for pattern, ctype in constraint_keywords:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            line_no = text[:match.start()].count("\n") + 1
            constraints.append(Constraint(
                description=match.group(0).strip()[:300],
                math_expression=match.group(1).strip()[:200] if match.lastindex else "",
                constraint_type=ctype,
                location=f"line {line_no}",
            ))

    # Also check math blocks for constraint-like patterns
    for block in blocks:
        if any(sym in block.content for sym in ["\\leq", "\\geq", "\\le", "\\ge", "=", "\\equiv"]):
            if block.environment in ("equation", "align", "displaymath"):
                constraints.append(Constraint(
                    description=f"Math constraint in {block.environment} environment",
                    math_expression=block.content[:300],
                    constraint_type="equality" if "=" in block.content else "inequality",
                    location=f"line {block.line_number}",
                ))

    return constraints


# ---------------------------------------------------------------------------
# Theorem extraction
# ---------------------------------------------------------------------------

def extract_theorems(blocks: list[MathBlock]) -> list[Theorem]:
    """Extract theorem/lemma/proposition statements."""
    theorems: list[Theorem] = []
    theorem_envs = {"theorem", "lemma", "proposition", "corollary"}

    for block in blocks:
        if block.environment in theorem_envs:
            theorems.append(Theorem(
                label=f"{block.environment.capitalize()} (line {block.line_number})",
                statement=block.content[:1000],
                location=f"line {block.line_number}, section: {block.section}",
            ))

    return theorems


# ---------------------------------------------------------------------------
# Approximation detection
# ---------------------------------------------------------------------------

def detect_approximations(text: str) -> list[Approximation]:
    """Detect approximation strategies described in the paper."""
    approximations: list[Approximation] = []

    approx_patterns = [
        (r"(?:piecewise[\-\s]?linear)\s*(?:approximat\w+)?\s*(?:of|for|to)?\s*(\w+)",
         "piecewise-linear"),
        (r"(?:taylor|polynomial)\s*(?:approximat\w+|expansion)\s*(?:of|for|to)?\s*(\w+)",
         "polynomial"),
        (r"(?:chebyshev)\s*(?:approximat\w+|polynomial)\s*(?:of|for|to)?\s*(\w+)",
         "polynomial"),
        (r"(?:lookup[\s\-]?table)\s*(?:for|of|to)?\s*(\w+)",
         "lookup-table"),
        (r"(?:approximat\w+)\s+(?:of|for|to)\s+(\w+(?:\s+\w+)?)",
         "unspecified"),
    ]

    for pattern, method in approx_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            line_no = text[:match.start()].count("\n") + 1
            target = match.group(1).strip() if match.lastindex else "unknown"

            # Look for error bound nearby (within 500 chars)
            region = text[match.start():match.start() + 500]
            error_bound = ""
            err_match = re.search(
                r"(?:error|accuracy|precision|bound)\s*(?:of|is|:|≤|<=)\s*([^\n.]{3,80})",
                region, re.IGNORECASE,
            )
            if err_match:
                error_bound = err_match.group(1).strip()

            approximations.append(Approximation(
                target_operation=target,
                method=method,
                description=match.group(0).strip()[:200],
                error_bound=error_bound,
                location=f"line {line_no}",
            ))

    return approximations


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(text: str, fmt: str) -> dict:
    """Extract paper title, authors, sections."""
    metadata: dict = {"sections": []}

    if fmt == "latex":
        title_match = re.search(r"\\title\{([^}]+)\}", text)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        author_match = re.search(r"\\author\{([^}]+)\}", text)
        if author_match:
            metadata["authors"] = author_match.group(1).strip()

        for match in re.finditer(r"\\(?:section|subsection)\{([^}]+)\}", text):
            metadata["sections"].append(match.group(1).strip())
    else:
        # Markdown: look for # headings
        for match in re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE):
            metadata["sections"].append(match.group(1).strip())
        if metadata["sections"]:
            metadata["title"] = metadata["sections"][0]

    return metadata


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def validate_path(path_str: str) -> Path:
    """Validate and resolve the input path securely."""
    path = Path(path_str).resolve()
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_file():
        print(f"ERROR: Not a file: {path}", file=sys.stderr)
        sys.exit(1)
    # Reject paths with .. components (after resolution this is implicit, but check original)
    if ".." in Path(path_str).parts:
        print("ERROR: Path traversal (..) not allowed", file=sys.stderr)
        sys.exit(1)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_paper(paper_path: str) -> PaperManifest:
    """Main entry point: parse a paper and return structured manifest."""
    path = validate_path(paper_path)
    text, fmt = read_source(path)

    blocks = extract_math_blocks(text, fmt)
    operators = classify_operators(text, blocks)
    constraints = extract_constraints(text, blocks)
    theorems = extract_theorems(blocks)
    approximations = detect_approximations(text)
    metadata = extract_metadata(text, fmt)

    return PaperManifest(
        source=str(path),
        format=fmt,
        operators=operators,
        constraints=constraints,
        theorems=theorems,
        approximations=approximations,
        metadata=metadata,
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python parse_paper.py <paper_path>", file=sys.stderr)
        sys.exit(1)

    manifest = parse_paper(sys.argv[1])
    print(json.dumps(asdict(manifest), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
