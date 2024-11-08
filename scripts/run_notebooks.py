from __future__ import annotations

from typing import List

from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


def find_notebooks() -> List[Path]:
    """
    Find all jupyter notebooks in the repository.
    """
    notebooks = []
    for file in Path(".").rglob("*.ipynb"):
        notebooks.append(file)
    return notebooks


def run_notebook(notebook_path: Path):
    """
    Run a jupyter notebook.

    Returns:
        The executed notebook object
    """
    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(
            timeout=600, kernel_name="python3", allow_errors=True, log_level=50
        )
        try:
            ep.preprocess(nb, {"metadata": {"path": notebook_path.parent}})
        except Exception as e:
            print(f"Error executing the notebook {notebook_path}")
            print(e)

    return nb


def strip_metadata(nb):
    """
    Strip the metadata from the notebook.

    Args:
        nb: The notebook object from nbformat.
    """
    for cell in nb.cells:
        if "metadata" in cell:
            cell.metadata = {}
    return nb


def count_errors_and_warnings(nb):
    """
    Count the number of errors and warnings in the notebook.

    Args:
        nb: The notebook object from nbformat.

    Returns:
        The number of errors and warnings as a tuple (errors, warnings).
    """
    errors = 0
    warnings = 0
    for cell in nb.cells:
        if cell.cell_type == "code":
            for output in cell.outputs:
                if output.output_type == "error":
                    errors += 1
                elif output.output_type == "stream" and "warning" in output.text.lower():
                    warnings += 1
    return errors, warnings


def save_notebook(nb, notebook_path: Path):
    """
    Save a jupyter notebook.

    Args:
        nb: The notebook object from nbformat.
        notebook_path: The path to the notebook.
    """
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)


def main():
    summary = "\n\nSUMMARY OF ERRORS AND WARNINGS\n\n"

    total_errors = 0
    total_warnings = 0

    for notebook_path in find_notebooks():
        nb = run_notebook(notebook_path)
        nb = strip_metadata(nb)
        save_notebook(nb, notebook_path)

        errors, warnings = count_errors_and_warnings(nb)
        total_errors += errors
        total_warnings += warnings

        if errors > 0:
            summary += f"Notebook {notebook_path} has {errors} errors.\n"
        if warnings > 0:
            summary += f"Notebook {notebook_path} has {warnings} warnings.\n"

    summary += f"Total errors = {total_errors}\n"
    summary += f"Total warnings = {total_warnings}\n"

    print(summary)


if __name__ == "__main__":
    main()
