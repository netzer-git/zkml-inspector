# zkml-inspector — Project Conventions

## Language & Runtime
- Python 3.10+ for all scripts
- Type hints on all function signatures
- UTF-8 encoding everywhere

## Security Boundaries
- Scripts MUST only read files within the user-provided paper path and codebase path
- Never execute code from the analyzed codebase — only read and parse
- Never write outside the current working directory
- Sanitize all file paths before use (resolve symlinks, reject `..` traversals)

## Report Formatting
- All output reports use Markdown
- Severity levels: `CRITICAL`, `WARNING`, `INFO`
- Every finding must include: severity, location (file + line), description, recommendation
- Tables use GitHub-Flavored Markdown syntax

## Code Style
- Scripts are standalone CLI tools invokable via `python script.py <args>`
- All scripts output JSON to stdout (parseable by the agent)
- Errors go to stderr
- Exit code 0 = success, 1 = error

## zkML Domain Conventions
- "Operator" = a mathematical operation defined in the paper (MatMul, Conv2D, ReLU, Softmax, etc.)
- "Constraint" = a polynomial equality/inequality enforced in the circuit
- "Gate" = a single constraint in the arithmetic circuit
- "Approximation" = a simplified version of a non-polynomial operation used in the ZK circuit
- "Transformer Killer" = non-polynomial operations (Softmax, LayerNorm, GELU, Sigmoid, Tanh) that are expensive to prove in ZK
