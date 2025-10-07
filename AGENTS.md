# Repository Guidelines

## Project Structure & Module Organization
- `app.py` boots the Streamlit interface; `run.py` and `run.sh` wrap common launch paths.
- `components/` holds UI widgets, while domain logic lives in `modules/` and orchestration helpers in `services/`.
- `repository/` encapsulates SQLite access and should be the only layer touching persistent storage.
- Shared utilities reside in `utils/`, configuration in `config/`, and cached responses under `cache/` (avoid committing local cache artifacts).
- Tests mirror the runtime modules inside `tests/`; seed datasets and fixtures live alongside the relevant test modules.

## Build, Test, and Development Commands
- Create or refresh your environment with `pip install -r requirements.txt` (use a fresh virtualenv).
- Launch the app locally via `streamlit run app.py` or the scripted wrappers `python run.py` / `./run.sh` (the latter expects execute permission).
- Run targeted scripts such as `python add_dividend_portfolio.py` from the repo root so relative imports resolve correctly.
- Execute the regression test suite with `pytest`; add `--cov=. tests/` when verifying coverage before reviews.

## Coding Style & Naming Conventions
- Follow Black formatting (`black .`) with 4-space indentation; never mix tabs and spaces.
- Use `snake_case` for files, modules, and functions, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Prefer explicit type hints and concise docstrings describing purpose, inputs, and side effects.
- Keep Streamlit components lean: move data work into `modules/` or `services/`, and isolate database logic inside the repository layer.

## Testing Guidelines
- Place new tests in `tests/` mirroring the module tree (e.g., `tests/modules/test_position_sizing.py`).
- Name test files and functions with the `test_` prefix; group scenario-specific fixtures inside the same directory.
- Ensure business-critical paths have coverage and use `pytest -k <keyword>` for focused iterations when debugging.
- Validate edge cases involving multiple currencies or cached data to keep regressions out of the core workflows.

## Commit & Pull Request Guidelines
- Follow the existing history style: short, imperative summaries with conventional prefixes (`feat:`, `fix:`, `chore:`, `docs:`) and optional scope tags.
- Squash WIP changes locally; commits should bundle related work and mention user-facing impacts when applicable.
- Pull requests must include a clear summary, reproduction or validation steps, and screenshots/GIFs when the UI changes.
- Link GitHub issues or task IDs in the PR body, and call out schema or data updates that require reviewer migration steps.

## Configuration & Data Notes
- Centralize runtime configuration edits in `config/app_config.py`; update `old_config.py` only when deprecating legacy settings.
- Cache warmers should respect existing TTL helpers in `cache_utils.py`; never hard-code secrets or credentials in tracked files.
- When introducing new data sources, document fallbacks and timeout handling in `services/data_service.py` to stay aligned with the resilience strategy.
