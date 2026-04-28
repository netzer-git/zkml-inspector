#!/usr/bin/env python3
"""Tests for the Claude Code command configuration.

Validates that all .claude/commands/ files and .claude/mcp.json are present,
well-structured, and consistent with the Copilot layer they mirror.

Run with:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = ROOT / ".claude"
COMMANDS_DIR = CLAUDE_DIR / "commands"
MCP_JSON = CLAUDE_DIR / "mcp.json"
VSCODE_MCP_JSON = ROOT / ".vscode" / "mcp.json"

EXPECTED_COMMANDS = [
    "analyze-full.md",
    "analyze-batch.md",
]


# ============================================================================
# File existence tests
# ============================================================================

class TestClaudeFilesExist:
    """Verify all required Claude Code files are present."""

    def test_claude_directory_exists(self) -> None:
        assert CLAUDE_DIR.is_dir(), f"Missing .claude/ directory: {CLAUDE_DIR}"

    def test_commands_directory_exists(self) -> None:
        assert COMMANDS_DIR.is_dir(), f"Missing .claude/commands/ directory: {COMMANDS_DIR}"

    def test_mcp_json_exists(self) -> None:
        assert MCP_JSON.is_file(), f"Missing .claude/mcp.json: {MCP_JSON}"

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_command_file_exists(self, filename: str) -> None:
        path = COMMANDS_DIR / filename
        assert path.is_file(), f"Missing command file: {path}"


# ============================================================================
# MCP JSON tests
# ============================================================================

class TestMcpJson:
    """Validate .claude/mcp.json structure and consistency with .vscode/mcp.json."""

    def _load(self) -> dict:
        return json.loads(MCP_JSON.read_text(encoding="utf-8"))

    def test_valid_json(self) -> None:
        self._load()  # raises if invalid

    def test_has_mcp_servers_key(self) -> None:
        data = self._load()
        assert "mcpServers" in data, (
            ".claude/mcp.json must use 'mcpServers' key (not 'servers')"
        )

    def test_has_pdf_reader_server(self) -> None:
        data = self._load()
        assert "pdf-reader" in data.get("mcpServers", {}), (
            ".claude/mcp.json must define a 'pdf-reader' server"
        )

    def test_pdf_reader_uses_npx(self) -> None:
        data = self._load()
        server = data["mcpServers"]["pdf-reader"]
        assert server.get("command") == "npx", (
            "pdf-reader server must use 'npx' command"
        )

    def test_pdf_reader_has_args(self) -> None:
        data = self._load()
        server = data["mcpServers"]["pdf-reader"]
        assert server.get("args"), "pdf-reader server must have args"

    def test_consistency_with_vscode_mcp(self) -> None:
        """pdf-reader server definition must match .vscode/mcp.json."""
        if not VSCODE_MCP_JSON.is_file():
            pytest.skip(".vscode/mcp.json not present")
        vscode = json.loads(VSCODE_MCP_JSON.read_text(encoding="utf-8"))
        vscode_server = vscode.get("servers", {}).get("pdf-reader", {})
        claude_server = json.loads(MCP_JSON.read_text(encoding="utf-8"))["mcpServers"]["pdf-reader"]
        assert claude_server.get("command") == vscode_server.get("command"), (
            "pdf-reader 'command' differs between .claude/mcp.json and .vscode/mcp.json"
        )
        assert claude_server.get("args") == vscode_server.get("args"), (
            "pdf-reader 'args' differs between .claude/mcp.json and .vscode/mcp.json"
        )


# ============================================================================
# analyze-full.md content tests
# ============================================================================

class TestAnalyzeFullContent:
    """Validate analyze-full.md contains required orchestration elements."""

    @pytest.fixture(autouse=True)
    def load(self) -> None:
        self.text = (COMMANDS_DIR / "analyze-full.md").read_text(encoding="utf-8")

    def test_has_arguments_placeholder(self) -> None:
        assert "$ARGUMENTS" in self.text, "analyze-full.md must reference $ARGUMENTS"

    def test_has_agent_tool_reference(self) -> None:
        assert "Agent" in self.text, (
            "analyze-full.md must reference the Agent tool for sub-agent dispatching"
        )

    def test_has_paper_analyst_instructions(self) -> None:
        assert "paper-analyst" in self.text.lower() or "Paper Analyst" in self.text, (
            "analyze-full.md must embed paper-analyst instructions"
        )

    def test_has_code_inspector_instructions(self) -> None:
        assert "code-inspector" in self.text.lower() or "Code Auditor" in self.text, (
            "analyze-full.md must embed code-inspector instructions"
        )

    def test_has_report_writer_instructions(self) -> None:
        assert "report-writer" in self.text.lower() or "Report Writer" in self.text, (
            "analyze-full.md must embed report-writer instructions"
        )

    def test_uses_write_not_create_file(self) -> None:
        assert "createFile" not in self.text, (
            "analyze-full.md must use 'Write' tool (not Copilot's 'createFile')"
        )

    def test_has_write_tool_reference(self) -> None:
        assert "Write" in self.text, (
            "analyze-full.md must reference the Write tool for file output"
        )

    def test_has_output_path_logic(self) -> None:
        assert "output_path" in self.text, (
            "analyze-full.md must describe output_path determination"
        )

    def test_has_pdf_mcp_tool(self) -> None:
        assert "mcp__pdf-reader__read_pdf" in self.text, (
            "analyze-full.md must reference mcp__pdf-reader__read_pdf for PDF support"
        )

    def test_has_fallback_write(self) -> None:
        assert "Fallback" in self.text or "fallback" in self.text, (
            "analyze-full.md must have a fallback to write the report if sub-agent doesn't"
        )

    def test_has_quality_gate(self) -> None:
        assert "commitment_obligations" in self.text and "proof_system" in self.text, (
            "analyze-full.md must include quality gate checks on the paper manifest"
        )


# ============================================================================
# analyze-batch.md content tests
# ============================================================================

class TestAnalyzeBatchContent:
    """Validate analyze-batch.md contains required batch orchestration elements."""

    @pytest.fixture(autouse=True)
    def load(self) -> None:
        self.text = (COMMANDS_DIR / "analyze-batch.md").read_text(encoding="utf-8")

    def test_has_arguments_placeholder(self) -> None:
        assert "$ARGUMENTS" in self.text, "analyze-batch.md must reference $ARGUMENTS"

    def test_has_agent_output_json(self) -> None:
        assert "agent_output.json" in self.text, (
            "analyze-batch.md must describe agent_output.json generation"
        )
        assert "summary.json" not in self.text, (
            "analyze-batch.md must no longer reference the legacy summary.json output"
        )

    def test_has_benchmark_schema_fields(self) -> None:
        for field in [
            "entry-id",
            "issue-name",
            "issue-explanation",
            "relevant-code",
            "paper-reference",
        ]:
            assert field in self.text, (
                f"analyze-batch.md must reference benchmark field '{field}'"
            )

    def test_has_resume_logic(self) -> None:
        assert "resume" in self.text.lower() or "skip" in self.text.lower(), (
            "analyze-batch.md must describe resume/skip behavior for existing reports"
        )

    def test_has_context_compaction(self) -> None:
        assert "context compaction" in self.text.lower() or "Context compaction" in self.text or "discard" in self.text.lower(), (
            "analyze-batch.md must describe context compaction between entries"
        )

    def test_has_isolation_constraint(self) -> None:
        assert "isolation" in self.text.lower() or "Isolation" in self.text, (
            "analyze-batch.md must enforce isolation between paper analyses"
        )

    def test_saves_outside_workspace(self) -> None:
        assert "outside" in self.text.lower() or "next to" in self.text.lower() or "NOT inside" in self.text, (
            "analyze-batch.md must save reports outside the zkml-inspector workspace"
        )

    def test_sequential_only(self) -> None:
        assert "sequential" in self.text.lower() or "NOT parallelize" in self.text or "not parallel" in self.text.lower(), (
            "analyze-batch.md must enforce sequential (non-parallel) processing"
        )

    def test_has_all_three_sub_agents(self) -> None:
        assert "paper-analyst" in self.text.lower() or "Paper Analyst" in self.text, (
            "analyze-batch.md must invoke paper-analyst"
        )
        assert "code-inspector" in self.text.lower() or "Code Auditor" in self.text, (
            "analyze-batch.md must invoke code-inspector"
        )
        assert "report-writer" in self.text.lower() or "Report Writer" in self.text, (
            "analyze-batch.md must invoke report-writer"
        )

    def test_has_pdf_mcp_tool(self) -> None:
        assert "mcp__pdf-reader__read_pdf" in self.text, (
            "analyze-batch.md must reference mcp__pdf-reader__read_pdf for PDF support"
        )

    def test_uses_write_not_create_file(self) -> None:
        assert "createFile" not in self.text, (
            "analyze-batch.md must use 'Write' tool (not Copilot's 'createFile')"
        )


# ============================================================================
# No Copilot tool names tests
# ============================================================================

class TestNoCopilotToolNames:
    """Ensure command files use Claude Code tool names, not Copilot tool names."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_no_create_file_tool(self, filename: str) -> None:
        text = (COMMANDS_DIR / filename).read_text(encoding="utf-8")
        assert "createFile" not in text, (
            f"{filename} uses Copilot's 'createFile' — use Claude Code's 'Write' tool instead"
        )
