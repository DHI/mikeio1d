# Contributing to MIKEIO1D

This guide will help you set up your development environment.

## Prerequisites

This project uses [`uv`](https://docs.astral.sh/uv/) as the package manager. If you don't have it installed, please refer to the [installation guide](https://dhigroup.sharepoint.com/sites/TechnologyandInnovation/SitePages/Installing-Python.aspx).

## Setup

1. **Clone the repository**
2. **Install dependencies**
   ```bash
   uv sync --extra dev --extra test --extra notebooks --python 3.XX
   ```
   Replace `XX` with your Python version (3.9 through 3.13 are supported).

3. **Activate the virtual environment**
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. **Verify installation**
   Run the test suite to ensure everything is working correctly:
   ```bash
   pytest .
   ```

## Making Contributions

1. **Prepare your contribution**
   - For bugs: Create a failing test that demonstrates the issue
   - For new features: Consider opening an issue to discuss your idea first

2. **Implement your changes**
   - Write or update tests as needed
   - Make your code changes
   - Ensure all tests pass with `pytest`

3. **Submit a pull request**
   - Provide a clear description of your changes
   - Reference any related issues

### Code Quality

Before submitting your changes:

1. **Run tests**: `pytest`
2. **Format code**: We use `ruff` for formatting and linting:
   ```bash
   ruff format .
   ruff check .
   ```
3. **Check coverage**: Ensure your changes include appropriate tests

### Pull Request Guidelines

When submitting a pull request:
- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass
- Include documentation updates if necessary