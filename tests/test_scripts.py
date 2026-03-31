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
SKILL_DIR = ROOT / ".github" / "skills" / "analyze-zkml-gap"
REFERENCES_DIR = SKILL_DIR / "references"


# ---------------------------------------------------------------------------
# Expected files
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = [
    "zkml-inspector.agent.md",
    "paper-analyst.agent.md",
    "code-inspector.agent.md",
    "report-writer.agent.md",
    "batch-runner.agent.md",
]

EXPECTED_PROMPTS = [
    "analyze-full.prompt.md",
    "analyze-quick.prompt.md",
    "analyze-batch.prompt.md",
]

EXPECTED_REFERENCES = [
    "zkp_foundations.md",
    "operator_catalog.md",
    "soundness_checklist.md",
    "approximation_db.md",
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

    @pytest.mark.parametrize("filename", EXPECTED_REFERENCES)
    def test_reference_file_exists(self, filename: str) -> None:
        path = REFERENCES_DIR / filename
        assert path.is_file(), f"Missing reference file: {path}"

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

    def test_skill_no_auditor_refs(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        assert "zkp-auditor" not in text, "SKILL.md still references zkp-auditor"
        assert "gate_cost_table" not in text, "SKILL.md still references gate_cost_table"

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
        assert '"operators"' in text
        assert '"proof_system"' in text

    def test_paper_analyst_has_commitment_obligations(self) -> None:
        """paper-analyst must include commitment_obligations in its output."""
        text = (AGENTS_DIR / "paper-analyst.agent.md").read_text(encoding="utf-8")
        assert '"commitment_obligations"' in text, (
            "paper-analyst output should include commitment_obligations field"
        )

    def test_paper_analyst_emphasizes_commitments(self) -> None:
        """paper-analyst must have exhaustive commitment extraction."""
        text = (AGENTS_DIR / "paper-analyst.agent.md").read_text(encoding="utf-8")
        assert "EXHAUSTIVE" in text.upper() or "exhaustive" in text.lower(), (
            "paper-analyst should emphasize exhaustive commitment extraction"
        )

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
        assert '"commitment_audit"' in text or '"operator_coverage"' in text or '"soundness_findings"' in text, (
            "code-inspector output should include audit finding arrays"
        )

    def test_code_inspector_no_framework_detection_table(self) -> None:
        """code-inspector should not have a framework detection table."""
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "## Framework Detection Guide" not in text, (
            "code-inspector should not have a framework detection guide table"
        )

    def test_code_inspector_references_soundness_checklist(self) -> None:
        """code-inspector must reference soundness_checklist.md."""
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "soundness_checklist.md" in text, (
            "code-inspector should reference soundness_checklist.md"
        )

    def test_report_writer_has_dedup_rule(self) -> None:
        text = (AGENTS_DIR / "report-writer.agent.md").read_text(encoding="utf-8")
        assert "eduplicate" in text.lower(), (
            "report-writer should have a finding deduplication rule"
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

    def test_analysis_agents_reference_zkp_foundations(self) -> None:
        """Analysis agents should reference the shared ZKP foundations."""
        for filename in ["paper-analyst.agent.md", "code-inspector.agent.md"]:
            text = (AGENTS_DIR / filename).read_text(encoding="utf-8")
            assert "zkp_foundations.md" in text, (
                f"{filename} should reference zkp_foundations.md"
            )

    def test_mock_phantom_detection_in_code_inspector(self) -> None:
        """code-inspector must have the mock/phantom implementation detection."""
        text = (AGENTS_DIR / "code-inspector.agent.md").read_text(encoding="utf-8")
        assert "mock" in text.lower() or "phantom" in text.lower(), (
            "code-inspector should detect mock/phantom implementations"
        )

    def test_mock_phantom_detection_in_soundness_checklist(self) -> None:
        """Soundness checklist must include a CHECK for mock implementations."""
        text = (REFERENCES_DIR / "soundness_checklist.md").read_text(encoding="utf-8")
        assert "CHECK-2.5" in text, (
            "soundness_checklist.md should include CHECK-2.5 for mock/phantom detection"
        )
        assert "phantom" in text.lower() or "mock" in text.lower()


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

    def test_soundness_checklist_has_checks(self) -> None:
        text = (REFERENCES_DIR / "soundness_checklist.md").read_text(encoding="utf-8")
        assert "CHECK" in text, "soundness_checklist.md should contain CHECK items"

    def test_no_framework_specific_mentions_in_references(self) -> None:
        """Reference files should not contain framework-specific mentions."""
        for filename in EXPECTED_REFERENCES:
            text = (REFERENCES_DIR / filename).read_text(encoding="utf-8")
            assert "EZKL" not in text and "ezkl" not in text, (
                f"{filename} contains EZKL-specific mention — should be framework-agnostic"
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

    def test_skill_references_match_files(self) -> None:
        """SKILL.md should only reference files that exist."""
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        # Check that referenced reference files exist
        for ref in EXPECTED_REFERENCES:
            if ref in text:
                assert (REFERENCES_DIR / ref).is_file()

    def test_prompts_reference_orchestrator(self) -> None:
        """Prompt files should use their respective agent."""
        agent_map = {
            "analyze-full.prompt.md": "zkml-inspector",
            "analyze-quick.prompt.md": "zkml-inspector",
            "analyze-batch.prompt.md": "batch-runner",
        }
        for filename in EXPECTED_PROMPTS:
            fm = _extract_frontmatter(PROMPTS_DIR / filename)
            expected_agent = agent_map[filename]
            assert expected_agent in fm, (
                f"{filename} should reference the {expected_agent} agent"
            )


# ============================================================================
# Batch runner tests
# ============================================================================

class TestBatchRunner:
    """Validate batch-runner agent configuration."""

    def test_batch_runner_has_zkml_inspector_agent(self) -> None:
        """batch-runner must list zkml-inspector as its sub-agent."""
        fm = _extract_frontmatter(AGENTS_DIR / "batch-runner.agent.md")
        assert "zkml-inspector" in fm, (
            "batch-runner should list zkml-inspector in its agents"
        )

    def test_batch_runner_is_user_invocable(self) -> None:
        """batch-runner should be user-invocable (no user-invocable: false)."""
        fm = _extract_frontmatter(AGENTS_DIR / "batch-runner.agent.md")
        assert "user-invocable: false" not in fm, (
            "batch-runner should be user-invocable"
        )

    def test_batch_runner_has_resume_logic(self) -> None:
        """batch-runner must describe resume behavior."""
        text = (AGENTS_DIR / "batch-runner.agent.md").read_text(encoding="utf-8")
        assert "resume" in text.lower() or "Resume" in text, (
            "batch-runner should describe resume behavior"
        )

    def test_batch_runner_has_timestamped_folder(self) -> None:
        """batch-runner must create timestamped output folders."""
        text = (AGENTS_DIR / "batch-runner.agent.md").read_text(encoding="utf-8")
        assert "YYYYMMDD" in text or "timestamp" in text.lower(), (
            "batch-runner should create timestamped output folders"
        )

    def test_batch_runner_saves_outside_workspace(self) -> None:
        """batch-runner must save reports outside the zkml-inspector workspace."""
        text = (AGENTS_DIR / "batch-runner.agent.md").read_text(encoding="utf-8")
        assert "next to the manifest" in text.lower() or "NOT inside the zkml-inspector" in text, (
            "batch-runner should save reports outside the zkml-inspector workspace"
        )

    def test_batch_runner_delegates_to_zkml_inspector(self) -> None:
        """batch-runner must delegate analysis to zkml-inspector, not do it itself."""
        text = (AGENTS_DIR / "batch-runner.agent.md").read_text(encoding="utf-8")
        assert "DO NOT" in text and "analysis yourself" in text.lower(), (
            "batch-runner should explicitly delegate to zkml-inspector"
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
            assert "name" in entry, "Each entry must have 'name'"
            assert "paper" in entry, "Each entry must have 'paper'"
            assert "codebase" in entry, "Each entry must have 'codebase'"
