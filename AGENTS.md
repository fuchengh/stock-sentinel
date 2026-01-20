# AGENTS.md

This document is guidance for agentic coding agents operating in this repository.
Follow it strictly unless a human explicitly instructs otherwise.

Repository: stock-sentinel (Python)

---
Build, Run, Lint, Test

Environment
- Python: 3.10+ (tested up to 3.14)
- Platform: macOS/Linux/Windows
- Virtualenv recommended: `.venv`

Install dependencies
- `pip install -r requirements.txt`

Primary entry points
- Weekly scan: `python src/main.py --mode WEEKLY`
- Daily scan: `python src/main.py --mode DAILY`
- Backtest runner: `python run_backtest.py`

Build
- No compilation step; pure Python project
- Ensure imports resolve by running: `python -m compileall src`

Lint / Static checks
- No enforced linter in repo
- Preferred tools if adding checks:
  - Formatting: `black src`
  - Linting: `ruff src` or `flake8 src`
  - Types (optional): `mypy src`

Tests
- No formal test suite currently present
- If tests are added, use `pytest`
- Run all tests: `pytest`
- Run a single test file: `pytest path/to/test_file.py`
- Run a single test function: `pytest path/to/test_file.py -k test_name`

CI
- GitHub Actions workflow: `.github/workflows/weekly_scan.yml`
- Runs scheduled weekly scan; no tests enforced in CI

---
Project Structure and Ownership

- `src/main.py`
  - Application entry point
  - Orchestrates WEEKLY vs DAILY modes
- `src/data_loader.py`
  - External I/O: Alpaca API, price data, news
- `src/strategies/`
  - Strategy implementations
  - `base.py` defines shared interfaces and helpers
- `src/notifier.py`
  - Discord webhook formatting and delivery
- `src/chart_generator.py`
  - Chart rendering (mplfinance)
- `src/ai_analyst.py`
  - LLM / OpenRouter integration

Keep I/O, strategy logic, and presentation concerns separated.

---
Code Style Guidelines

General
- Language: Python
- Encoding: ASCII preferred
- Follow PEP 8 unless project conventions differ
- Favor clarity over cleverness

Imports
- Standard library imports first
- Third-party imports second
- Local imports last (`src.` or relative modules)
- One import per line; avoid wildcard imports
- Group imports with a single blank line between groups

Formatting
- Indentation: 4 spaces
- Max line length: ~88 characters (Black-compatible)
- Use trailing commas in multiline literals
- Use parentheses instead of backslashes for line continuation

Types
- Type hints encouraged for public functions and complex logic
- Use built-in generics (`list[str]`, `dict[str, float]`) when possible
- Avoid overly generic `Any` unless unavoidable

Naming Conventions
- Modules: `snake_case.py`
- Functions: `snake_case`
- Variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Strategy names should be descriptive and domain-specific

Functions and Classes
- Keep functions small and single-purpose
- Prefer pure functions for strategy calculations
- Side effects (API calls, file writes, notifications) should be explicit

Error Handling
- Do not silently swallow exceptions
- Catch exceptions only when you can add context or recover
- Log or propagate errors upward rather than printing
- Validate external data (API responses, env vars) defensively

Configuration
- Configuration is driven by environment variables (`.env`)
- Do not hardcode secrets, tokens, or IDs
- Access env vars close to application boundaries

Logging and Output
- Prefer structured, informative messages
- Avoid noisy prints inside tight loops
- User-facing output should be actionable and concise

Dependencies
- Add new dependencies sparingly
- Update `requirements.txt` when adding or upgrading packages
- Prefer well-maintained, widely used libraries

AI / LLM Code
- Keep prompts deterministic and concise
- Do not embed secrets in prompts
- Isolate LLM calls from strategy decision logic

Charts and Visualization
- Chart generation should be deterministic
- Avoid coupling chart code with trading logic

---
Agent-Specific Rules

- Do not introduce new architectural patterns without justification
- Do not reformat unrelated files
- Do not remove existing behavior unless explicitly instructed
- Preserve existing public interfaces where possible
- When unsure, ask a clarifying question before making large changes

---
Notes

- No Cursor rules (`.cursor/rules/`, `.cursorrules`) present
- No Copilot instructions (`.github/copilot-instructions.md`) present
- This file is the source of truth for automated agents
