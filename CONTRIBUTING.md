# Contributing to MIKE IO 1D

This guide will help you set up your development environment.

## Prerequisites

This project uses [`uv`](https://docs.astral.sh/uv/) as the package manager. If you don't have it installed, please refer to the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

## Setup

1. **Clone the repo**
2. **Install dependencies**
   ```bash
   uv sync --extra dev --extra test --extra notebooks --python 3.XX
   ```
   Replace `XX` with your Python version (3.12 through 3.14 are supported).
3. **Verify installation** with `uv run pytest`

## Supported Python versions

MIKE IO 1D follows the [Scientific Python SPEC 0](https://scientific-python.org/specs/spec-0000/)
recommendation for dropping support of older Python versions. In short, support for a Python
minor version is dropped 3 years after its initial release. When bumping the minimum supported
Python version, remember to update it in `pyproject.toml` (`requires-python` and the
`Programming Language :: Python` classifiers), the CI matrix in `.github/workflows/full_test.yml`,
and the requirements listed in `README.md` and `docs/index.qmd`.

## Making Contributions

1. **Prepare your contribution**
   - For bugs: Create a failing test that demonstrates the issue
   - For new features: Consider opening an issue to discuss your idea first

2. **Implement your changes**
   - Write or update tests as needed
   - Make your code changes
   - Ensure all tests pass with `uv run pytest`

3. **Format code** with `uv run ruff format .`

4. **Submit a pull request**
   - Provide a clear description of your changes
   - Reference any related issues