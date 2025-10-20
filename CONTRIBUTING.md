# Guidelines for contribution

1. Clone repo
2. Install package in editable mode via *uv* `uv sync --dev`
3. If you are fixiing a bug, first add a failing test
4. Make changes
5. Verify that all tests passes by running `uv run pytest` from the package root directory
6. Lint the code by running *ruff* from root directory e.g. `uv run ruff check`
7. Format the code by running *ruff* from root directory e.g. `uv run ruff format`
8. Make a pull request with a summary of the changes
