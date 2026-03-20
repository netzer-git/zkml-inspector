#!/usr/bin/env python3
"""Tests for the zkml-inspector agent configuration.

Validates that all agent definitions, reference files, prompt files, and
the report template are present, well-structured, and internally consistent.

Run with:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".github" / "agents"
PROMPTS_DIR = ROOT / ".github" / "prompts"
SKILL_DIR = ROOT / ".github" / "skills" / "analyze-zkml-gap"
REFERENCES_DIR = SKILL_DIR / "references"
ASSETS_DIR = SKILL_DIR / "assets"


# ---------------------------------------------------------------------------
# Expected files
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = [
    "zkml-inspector.agent.md",
    "paper-analyst.agent.md",
    "code-inspector.agent.md",
    "zkp-auditor.agent.md",
    "report-writer.agent.md",
]

EXPECTED_PROMPTS = [
    "analyze-full.prompt.md",
    "analyze-quick.prompt.md",
    "audit-soundness.prompt.md",
    "inspect-code.prompt.md",
]

EXPECTED_REFERENCES = [
    "zkp_foundations.md",
    "operator_catalog.md",
    "soundness_checklist.md",
    "approximation_db.md",
    "gate_cost_table.md",
]

EXPECTED_ASSETS = [
    "report_template.md",
]


# ============================================================================
# File existence tests
# ============================================================================

class TestFileExistence:
    """Verify all required files are present."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_file_exists(self, filename: str) -> None:
        path = AGENTS_DIR / filename
        assert path.is_file(), f"Missing agent file: {path}"

    @pytest.mark.parametrize("filename", EXPECTED_PROMPTS)
    def test_prompt_file_exists(self, filename: str) -> None:
        path = PROMPTS_DIR / filename
        assert path.is_file(), f"Missing prompt file: {path}"

    @pytest.mark.parametrize("filename", EXPECTED_REFERENCES)
    def test_reference_file_exists(self, filename: str) -> None:
        path = REFERENCES_DIR / filename
        assert path.is_file(), f"Missing reference file: {path}"

    @pytest.mark.parametrize("filename", EXPECTED_ASSETS)
    def test_asset_file_exists(self, filename: str) -> None:
        path = ASSETS_DIR / filename
        assert path.is_file(), f"Missing asset file: {path}"

    def test_skill_file_exists(self) -> None:
        assert (SKILL_DIR / "SKILL.md").is_file()

    def test_no_scripts_directory(self) -> None:
        """Scripts directory should not exist (scripts removed in favor of agent analysis)."""
        scripts_dir = SKILL_DIR / "scripts"
        assert not scripts_dir.exists(), (
            f"Scripts directory should not exist: {scripts_dir}. "
            "Analysis is performed by agents directly, not by helper scripts."
        )


# ============================================================================
# YAML frontmatter tests
# ============================================================================

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _extract_frontmatter(path: Path) -> str:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match, f"No YAML frontmatter in {path.name}"
    return match.group(1)


class TestAgentFrontmatter:
    """Validate agent definition frontmatter structure."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_description(self, filename: str) -> None:
        fm = _extract_frontmatter(AGENTS_DIR / filename)
        assert "description:" in fm or "description: >" in fm

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_tools(self, filename: str) -> None:
        fm = _extract_frontmatter(AGENTS_DIR / filename)
        assert "tools:" in fm

    def test_orchestrator_has_agents_list(self) -> None:
        fm = _extract_frontmatter(AGENTS_DIR / "zkml-inspector.agent.md")
        assert "agents:" in fm

    def test_auditor_has_agents_list(self) -> None:
        fm = _extract_frontmatter(AGENTS_DIR / "zkp-auditor.agent.md")
        assert "agents:" in fm

    @pytest.mark.parametrize("filename", [
        "paper-analyst.agent.md",
        "code-inspector.agent.md",
        "zkp-auditor.agent.md",
        "report-writer.agent.md",
    ])
    def test_sub_agents_not_user_invocable(self, filename: str) -> None:
        fm = _extract_frontmatter(AGENTS_DIR / filename)
        assert "user-invocable: false" in fm

    @pytest.mark.parametrize("filename", EXPECTED_PROMPTS)
    def test_prompt_has_agent_field(self, filename: str) -> None:
        fm = _extract_frontmatter(PROMPTS_DIR / filename)
        assert "agent:" in fm


# ============================================================================
# No script references tests
# ============================================================================

SCRIPT_PATTERNS = re.compile(
    r"parse_paper\.py|inspect_codebase\.py|precision_checker\.py|gate_cost_profiler\.py"
    r"|scripts/parse_paper|scripts/inspect_codebase|scripts/precision_checker|scripts/gate_cost_profiler"
    r"|scripts/requirements\.txt"
)


class TestNoScriptReferences:
    """Ensure no file references the removed scripts."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_no_script_refs(self, filename: str) -> None:
        text = (AGENTS_DIR / filename).read_text(encoding="utf-8")
        matches = SCRIPT_PATTERNS.findall(text)
        assert not matches, f"{filename} still references scripts: {matches}"

    @pytest.mark.parametrize("filename", EXPECTED_PROMPTS)
    def test_prompt_no_script_refs(self, filename: str) -> None:
        text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
        matches = SCRIPT_PATTERNS.findall(text)
        assert not matches, f"{filename} still references scripts: {matches}"

    def test_skill_no_script_refs(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        matches = SCRIPT_PATTERNS.findall(text)
        assert not matches, f"SKILL.md still references scripts: {matches}"

    def test_copilot_instructions_no_script_refs(self) -> None:
        path = ROOT / ".github" / "copilot-instructions.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            matches = SCRIPT_PATTERNS.findall(text)
            assert not matches, f"copilot-instructions.md still references scripts: {matches}"

    def test_claude_md_no_script_refs(self) -> None:
        path = ROOT / "CLAUDE.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            matches = SCRIPT_PATTERNS.findall(text)
            assert not matches, f"CLAUDE.md still references scripts: {matches}"


# ============================================================================
# Agent no execute tool tests
# ============================================================================

class TestNoExecuteTool:
    """Sub-agents should not have the 'execute' tool since scripts are removed."""

    @pytest.mark.parametrize("filename", [
        "paper-analyst.agent.md",
        "code-inspector.agent.md",
        "zkp-auditor.agent.md",
        "report-writer.agent.md",
    ])
    def test_sub_agent_no_execute_tool(self, filename: str) -> None:
        fm = _extract_frontmatter(AGENTS_DIR / filename)
        # Parse the tools line
        tools_match = re.search(r"tools:\s*\[([^\]]*)\]", fm)
        if tools_match:
            tools = [t.strip() for t in tools_match.group(1).split(",")]
            assert "execute" not in tools, (
                f"{filename} still lists 'execute' tool — "
                "scripts have been removed, use 'read' and 'search' instead"
            )


# ============================================================================
# Content quality tests
# ============================================================================

class TestAgentContent:
    """Validate agent definitions contain required sections."""

    def test_paper_analyst_has_output_format(self) -> None:
        text = (AGENTS_DIR / "paper-analyst.agent.md").read_text(encoding="utf-8")
        assert "## Output Format" in text
        assert '"operators"' in text
        assert '"proof_system"' in text

    def test_code_inspector_has_output_format(self) -> None:
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "## Output Format" in text
        assert '"framework"' in text
        assert '"lifecycle"' in text

    def test_code_inspector_has_framework_guide(self) -> None:
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "## Framework Detection Guide" in text
        assert "halo2" in text
        assert "circom" in text
        assert "ezkl" in text

    def test_zkp_auditor_has_output_format(self) -> None:
        text = (AGENTS_DIR / "zkp-auditor.agent.md").read_text(encoding="utf-8")
        assert "## Output Format" in text
        assert '"audit_summary"' in text
        assert '"soundness_checklist"' in text

    def test_zkp_auditor_references_gate_cost_table(self) -> None:
        text = (AGENTS_DIR / "zkp-auditor.agent.md").read_text(encoding="utf-8")
        assert "gate_cost_table.md" in text

    def test_zkp_auditor_references_approximation_db(self) -> None:
        text = (AGENTS_DIR / "zkp-auditor.agent.md").read_text(encoding="utf-8")
        assert "approximation_db.md" in text

    def test_report_writer_has_dedup_rule(self) -> None:
        text = (AGENTS_DIR / "report-writer.agent.md").read_text(encoding="utf-8")
        assert "eduplicate" in text.lower(), (
            "report-writer should have a finding deduplication rule"
        )

    def test_all_agents_reference_zkp_foundations(self) -> None:
        """All analysis agents should reference the shared ZKP foundations."""
        for filename in ["paper-analyst.agent.md", "code-inspector.agent.md", "zkp-auditor.agent.md"]:
            text = (AGENTS_DIR / filename).read_text(encoding="utf-8")
            assert "zkp_foundations.md" in text, (
                f"{filename} should reference zkp_foundations.md"
            )


# ============================================================================
# Reference file quality tests
# ============================================================================

class TestReferenceContent:
    """Validate reference files are non-empty and have expected structure."""

    @pytest.mark.parametrize("filename", EXPECTED_REFERENCES)
    def test_reference_not_empty(self, filename: str) -> None:
        path = REFERENCES_DIR / filename
        text = path.read_text(encoding="utf-8")
        assert len(text.strip()) > 100, f"{filename} seems too short"

    def test_operator_catalog_has_operators(self) -> None:
        text = (REFERENCES_DIR / "operator_catalog.md").read_text(encoding="utf-8")
        for op in ["MatMul", "Softmax", "ReLU", "LayerNorm"]:
            assert op in text, f"operator_catalog.md missing {op}"

    def test_gate_cost_table_has_costs(self) -> None:
        text = (REFERENCES_DIR / "gate_cost_table.md").read_text(encoding="utf-8")
        # Should contain a markdown table with numeric cost values
        assert "|" in text, "gate_cost_table.md should contain a markdown table"

    def test_soundness_checklist_has_checks(self) -> None:
        text = (REFERENCES_DIR / "soundness_checklist.md").read_text(encoding="utf-8")
        assert "CHECK" in text, "soundness_checklist.md should contain CHECK items"


# ============================================================================
# Report template tests
# ============================================================================

class TestReportTemplate:
    """Validate the report template structure."""

    def test_template_has_required_sections(self) -> None:
        text = (ASSETS_DIR / "report_template.md").read_text(encoding="utf-8")
        required_sections = [
            "Executive Summary",
            "Operator Coverage",
            "Precision Analysis",
            "Soundness",
            "Recommendations",
        ]
        for section in required_sections:
            assert section in text, f"Report template missing section: {section}"

    def test_template_has_severity_symbols(self) -> None:
        text = (ASSETS_DIR / "report_template.md").read_text(encoding="utf-8")
        for symbol in ["✅", "⚠️", "❌"]:
            assert symbol in text, f"Report template missing status symbol: {symbol}"


# ============================================================================
# Cross-consistency tests
# ============================================================================

class TestCrossConsistency:
    """Validate consistency across agent definitions."""

    def test_orchestrator_lists_all_sub_agents(self) -> None:
        """The orchestrator should reference all sub-agents."""
        text = (AGENTS_DIR / "zkml-inspector.agent.md").read_text(encoding="utf-8")
        for agent in ["paper-analyst", "code-inspector", "zkp-auditor", "report-writer"]:
            assert agent in text, f"Orchestrator missing sub-agent: {agent}"

    def test_skill_references_match_files(self) -> None:
        """SKILL.md should only reference files that exist."""
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        # Check that referenced reference files exist
        for ref in EXPECTED_REFERENCES:
            if ref in text:
                assert (REFERENCES_DIR / ref).is_file()

    def test_prompts_reference_orchestrator(self) -> None:
        """All prompt files should use the zkml-inspector agent."""
        for filename in EXPECTED_PROMPTS:
            fm = _extract_frontmatter(PROMPTS_DIR / filename)
            assert "zkml-inspector" in fm, (
                f"{filename} should reference the zkml-inspector agent"
            )
