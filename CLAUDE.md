# CLAUDE.md — zkml-inspector

See `.github/copilot-instructions.md` for full project guidelines, architecture,
agent capabilities, build commands, and conventions.

## Quick Reference

```bash
python -m pytest tests/ -v    # Run tests
```

No runtime dependencies. Agent pipeline uses built-in LLM capabilities.
Reference data: `.github/skills/analyze-zkml-gap/references/`

## Architecture

Sequential 3-agent pipeline: `paper-analyst → code-inspector → report-writer`

- paper-analyst: extracts verification checklist from paper (commitment obligations, operator specs)
- code-inspector: audits codebase against paper manifest, produces findings
- report-writer: assembles findings into Markdown report
