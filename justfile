# Task runner for mikeio1d. Run `just` to list recipes.
#
# The recipes are the stable interface for contributors, agents and CI: call
# `just <recipe>` rather than the tools behind it, so a tool can be swapped here
# without touching the docs, skills or workflows.

default:
    @just --list

# --- Fast tier: well under a second, safe to run on every edit ----------------------

# Lint and check formatting
lint:
    uv run ruff check .
    uv run ruff format --check .

# Check the public API (__all__) against the source and the docs
api:
    python scripts/lint_public_api.py

# Stricter rules (annotations, Returns/Raises sections) on files changed since `base`
lint-changed base="main":
    #!/usr/bin/env bash
    set -euo pipefail
    files=$(git diff --name-only --diff-filter=d "$(git merge-base "{{ base }}" HEAD)" -- 'src/mikeio1d/*.py')
    if [ -z "$files" ]; then echo "No changed source files."; exit 0; fi
    # DOC rules are preview-only in ruff 0.16, so select them by exact code.
    uv run ruff check --preview --select ANN001,ANN201,DOC201,DOC501 $files

# Apply formatting and safe lint fixes
fix:
    uv run ruff format .
    uv run ruff check --fix .

# --- Slow tier ----------------------------------------------------------------------

# Run tests; extra arguments go to pytest, e.g. `just test tests/test_xns11.py -v`
test *args:
    uv run pytest {{ args }}

# Run tests the way CI does
test-ci:
    uv run pytest -c .pytest-ci.ini

# Build the documentation site into docs/_site
docs:
    #!/usr/bin/env bash
    set -euo pipefail
    cd docs
    uv run quartodoc build
    uv run quartodoc interlinks
    uv run quarto render
    if [ ! -f _site/index.html ]; then
        echo "Error: index.html not found. Quarto render failed."
        exit 1
    fi

# What to run before opening a PR
check: lint test
