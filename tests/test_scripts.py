#!/usr/bin/env python3
"""Tests for the zkml-inspector agent configuration.

Validates that all agent definitions, reference files, prompt files, and
the skill definition are present, well-structured, and internally consistent.

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


# ---------------------------------------------------------------------------
# Expected files
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = [
    "zkml-inspector.agent.md",
    "paper-analyst.agent.md",
    "code-inspector.agent.md",
    "report-writer.agent.md",
]

EXPECTED_PROMPTS = [
    "analyze-full.prompt.md",
    "analyze-batch.prompt.md",
]


# ============================================================================
# File existence tests
# ============================================================================

class TestFileExistence:
    """Verify all required files are present and removed files are gone."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_file_exists(self, filename: str) -> None:
        path = AGENTS_DIR / filename
        assert path.is_file(), f"Missing agent file: {path}"

    @pytest.mark.parametrize("filename", EXPECTED_PROMPTS)
    def test_prompt_file_exists(self, filename: str) -> None:
        path = PROMPTS_DIR / filename
        assert path.is_file(), f"Missing prompt file: {path}"

    def test_references_directory_removed(self) -> None:
        """Knowledgeless variant: the references/ knowledge base is intentionally absent."""
        assert not (ROOT / "references").exists(), (
            "references/ should not exist on the knowledgeless branch"
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

    def test_orchestrator_lists_three_agents(self) -> None:
        """Orchestrator should list exactly 3 sub-agents."""
        fm = _extract_frontmatter(AGENTS_DIR / "zkml-inspector.agent.md")
        # Handle both inline [a, b, c] and block sequence (- a\n  - b\n  - c)
        inline_match = re.search(r"agents:\s*\[([^\]]*)\]", fm)
        if inline_match:
            agents = [a.strip() for a in inline_match.group(1).split(",")]
        else:
            # Block sequence: find all "- <name>" lines after "agents:"
            block_match = re.search(r"agents:\s*\n((?:\s+-\s+\S+\n?)+)", fm)
            assert block_match, "Could not parse agents list"
            agents = re.findall(r"-\s+(\S+)", block_match.group(1))
        assert len(agents) == 3, f"Expected 3 agents, got {len(agents)}: {agents}"
        assert "paper-analyst" in agents
        assert "code-inspector" in agents
        assert "report-writer" in agents

    @pytest.mark.parametrize("filename", [
        "paper-analyst.agent.md",
        "code-inspector.agent.md",
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
# No removed component references tests
# ============================================================================

class TestNoRemovedComponentReferences:
    """Ensure no file references removed components (zkp-auditor, gate_cost_table, etc.)."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_no_auditor_refs(self, filename: str) -> None:
        text = (AGENTS_DIR / filename).read_text(encoding="utf-8")
        assert "zkp-auditor" not in text, f"{filename} still references zkp-auditor"
        assert "gate_cost_table" not in text, f"{filename} still references gate_cost_table"

    @pytest.mark.parametrize("filename", EXPECTED_PROMPTS)
    def test_prompt_no_auditor_refs(self, filename: str) -> None:
        text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
        assert "zkp-auditor" not in text, f"{filename} still references zkp-auditor"
        assert "gate_cost_table" not in text, f"{filename} still references gate_cost_table"

    def test_copilot_instructions_no_auditor_refs(self) -> None:
        path = ROOT / ".github" / "copilot-instructions.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            assert "zkp-auditor" not in text
            assert "gate_cost_table" not in text


# ============================================================================
# Agent no execute tool tests
# ============================================================================

class TestNoExecuteTool:
    """Sub-agents should not have the 'execute' tool since scripts are removed."""

    @pytest.mark.parametrize("filename", [
        "paper-analyst.agent.md",
        "code-inspector.agent.md",
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
        assert '"claims"' in text
        assert '"paper_reference"' in text

    def test_code_inspector_has_output_format(self) -> None:
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "## Output Format" in text
        assert '"findings"' in text or '"summary"' in text

    def test_code_inspector_receives_paper_manifest(self) -> None:
        """code-inspector must receive paper manifest as input."""
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "paper manifest" in text.lower() or "Paper manifest" in text, (
            "code-inspector must reference paper manifest as input"
        )

    def test_code_inspector_produces_findings(self) -> None:
        """code-inspector output is audit findings, not a code manifest."""
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert '"findings"' in text, (
            "code-inspector output should include a findings array"
        )

    def test_code_inspector_no_framework_detection_table(self) -> None:
        """code-inspector should not have a framework detection table."""
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "## Framework Detection Guide" not in text, (
            "code-inspector should not have a framework detection guide table"
        )

    def test_report_writer_has_dedup_rule(self) -> None:
        text = (AGENTS_DIR / "report-writer.agent.md").read_text(encoding="utf-8")
        assert "eduplicate" in text.lower(), (
            "report-writer should have a finding deduplication rule"
        )

    def test_report_writer_has_benchmark_findings_section(self) -> None:
        """report-writer must produce a trailing Benchmark Findings JSON block."""
        text = (AGENTS_DIR / "report-writer.agent.md").read_text(encoding="utf-8")
        assert "Benchmark Findings" in text, (
            "report-writer should describe a Benchmark Findings (machine-readable) section"
        )
        for field in [
            "issue-name",
            "issue-explanation",
            "relevant-code",
            "paper-reference",
        ]:
            assert field in text, (
                f"report-writer Benchmark Findings schema must mention '{field}'"
            )

    def test_report_writer_has_file_output_instructions(self) -> None:
        """report-writer must document how the report file is saved."""
        text = (AGENTS_DIR / "report-writer.agent.md").read_text(encoding="utf-8")
        assert "output_path" in text, (
            "report-writer should reference output_path for file saving"
        )

    def test_orchestrator_has_report_file_output(self) -> None:
        """Orchestrator must instruct saving the report to disk."""
        text = (AGENTS_DIR / "zkml-inspector.agent.md").read_text(encoding="utf-8")
        assert "write the file to disk" in text, (
            "Orchestrator should instruct writing the report to a file"
        )

    def test_orchestrator_has_sequential_pipeline(self) -> None:
        """Orchestrator must describe the sequential pipeline."""
        text = (AGENTS_DIR / "zkml-inspector.agent.md").read_text(encoding="utf-8")
        assert "sequential" in text.lower(), (
            "Orchestrator should describe the sequential pipeline"
        )

    def test_orchestrator_no_follow_up_rounds(self) -> None:
        """Orchestrator should NOT have follow-up round logic."""
        text = (AGENTS_DIR / "zkml-inspector.agent.md").read_text(encoding="utf-8")
        assert "Follow-Up Round" not in text, (
            "Orchestrator should not have follow-up round logic"
        )
        assert "follow_up_questions" not in text, (
            "Orchestrator should not reference follow_up_questions"
        )


# ============================================================================
# Knowledgeless variant tests
# ============================================================================

class TestKnowledgelessVariant:
    """Ensure no agent or prompt references the deleted references/ knowledge base."""

    REF_PATTERNS = re.compile(
        r"references/|zkp_foundations|soundness_checklist|operator_catalog|approximation_db|benchmark_taxonomy"
    )

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_no_reference_files(self, filename: str) -> None:
        text = (AGENTS_DIR / filename).read_text(encoding="utf-8")
        matches = self.REF_PATTERNS.findall(text)
        assert not matches, (
            f"{filename} still references the deleted knowledge base: {matches}"
        )

    @pytest.mark.parametrize("filename", EXPECTED_PROMPTS)
    def test_prompt_no_reference_files(self, filename: str) -> None:
        text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
        matches = self.REF_PATTERNS.findall(text)
        assert not matches, (
            f"{filename} still references the deleted knowledge base: {matches}"
        )


# ============================================================================
# Cross-consistency tests
# ============================================================================

class TestCrossConsistency:
    """Validate consistency across agent definitions."""

    def test_orchestrator_lists_all_sub_agents(self) -> None:
        """The orchestrator should reference all sub-agents."""
        text = (AGENTS_DIR / "zkml-inspector.agent.md").read_text(encoding="utf-8")
        for agent in ["paper-analyst", "code-inspector", "report-writer"]:
            assert agent in text, f"Orchestrator missing sub-agent: {agent}"

    def test_prompts_reference_orchestrator(self) -> None:
        """All prompt files should reference the zkml-inspector agent."""
        for filename in EXPECTED_PROMPTS:
            fm = _extract_frontmatter(PROMPTS_DIR / filename)
            assert "zkml-inspector" in fm, (
                f"{filename} should reference the zkml-inspector agent"
            )


# ============================================================================
# Batch prompt tests
# ============================================================================

class TestBatchPrompt:
    """Validate batch analysis prompt configuration."""

    def test_batch_prompt_references_analyze_full(self) -> None:
        """Batch prompt should delegate to analyze-full, not duplicate pipeline."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        assert "analyze-full" in text, (
            "analyze-batch should reference analyze-full for the per-entry pipeline"
        )

    def test_batch_prompt_has_resume_logic(self) -> None:
        """Batch prompt must describe resume behavior."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        assert "resume" in text.lower() or "skip" in text.lower(), (
            "analyze-batch should describe resume/skip behavior"
        )

    def test_batch_prompt_has_agent_output_json(self) -> None:
        """Batch prompt must describe agent_output.json (benchmark-schema) generation."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        assert "agent_output.json" in text, (
            "analyze-batch should describe agent_output.json output"
        )
        # Old summary.json schema must be gone
        assert "summary.json" not in text, (
            "analyze-batch should no longer reference the legacy summary.json output"
        )

    def test_batch_prompt_has_benchmark_schema_fields(self) -> None:
        """Batch prompt must mention the 5 required benchmark fields."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        for field in [
            "entry-id",
            "issue-name",
            "issue-explanation",
            "relevant-code",
            "paper-reference",
        ]:
            assert field in text, (
                f"analyze-batch must reference benchmark field '{field}'"
            )

    def test_batch_prompt_has_context_compaction(self) -> None:
        """Batch prompt must describe context compaction between entries."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        assert "context compaction" in text.lower() or "Context compaction" in text, (
            "analyze-batch should describe context compaction between entries"
        )

    def test_batch_prompt_saves_outside_workspace(self) -> None:
        """Batch prompt must save reports outside the zkml-inspector workspace."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        assert "NOT inside the zkml-inspector" in text or "next to manifest" in text.lower(), (
            "analyze-batch should save reports outside the zkml-inspector workspace"
        )

    def test_batch_prompt_has_isolation_constraint(self) -> None:
        """Batch prompt must enforce isolation between entries."""
        text = (PROMPTS_DIR / "analyze-batch.prompt.md").read_text(encoding="utf-8")
        assert "isolation" in text.lower(), (
            "analyze-batch should enforce isolation between paper analyses"
        )


class TestBatchManifest:
    """Validate the example batch manifest template."""

    def test_manifest_exists(self) -> None:
        path = ROOT / "examples" / "batch_manifest.json"
        assert path.is_file(), f"Missing manifest template: {path}"

    def test_manifest_is_valid_json(self) -> None:
        import json
        path = ROOT / "examples" / "batch_manifest.json"
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        assert "analyses" in data, "Manifest must have 'analyses' key"
        assert isinstance(data["analyses"], list), "'analyses' must be an array"
        assert len(data["analyses"]) > 0, "'analyses' must be non-empty"

    def test_manifest_entries_have_required_fields(self) -> None:
        import json
        path = ROOT / "examples" / "batch_manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["analyses"]:
            assert "entry-id" in entry, "Each entry must have 'entry-id'"
            assert "paper" in entry, "Each entry must have 'paper'"
            assert "codebase" in entry, "Each entry must have 'codebase'"
