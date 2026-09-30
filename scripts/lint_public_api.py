"""Check that the public API, as declared by ``__all__``, agrees with the docs.

The public API is the names listed in ``__all__`` of public modules, plus every
non-underscore member of an exported class. A module or package whose name starts
with a single underscore (``_graph.py``, ``_internal/``) is private, and so is
everything inside it; dunder names such as ``__init__`` are not.

This script reads the source and the docs with the standard library only --
nothing is imported, so .NET is never loaded and the whole run takes well under
a second. Checks that ruff already covers are left to ruff: F822 (undefined
export), PLE0604/PLE0605 (malformed ``__all__``), RUF022 (unsorted) and RUF068
(duplicates).

Checks
------
missing-all          a public package under src/mikeio1d has no ``__all__``
misspelled-all       a module assigns something like ``__all___`` or ``__ALL__``
docs-import          docs or notebooks import a name the module does not export,
                     or import from a private module
undocumented-export  an exported name is never mentioned in the docs
leaked-type          a public signature mentions a .NET type or a private name

A signature that exposes a .NET or private type on purpose -- an escape hatch to the
underlying .NET object, or a constructor only the package itself calls -- is exempted by the
comment ``# api: allow-leaked-type`` on a line of the signature: the ``def`` line, or the
line that closes it once the formatter has wrapped it.

Usage
-----
    python scripts/lint_public_api.py          # run from the repository root

Exits 1 when there are findings. Output is ``path:line: check message``.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PACKAGE = "mikeio1d"

# Directories under the package that hold no Python API.
NON_PYTHON_DIRS = {"bin"}

# .NET namespaces loaded through pythonnet; they must not appear in public signatures.
DOTNET_ROOTS = ("DHI", "System")

DOC_SUFFIXES = {".qmd", ".md", ".ipynb", ".yml", ".yaml"}

# Marks a signature that exposes a .NET or private type on purpose.
ALLOW_LEAK = re.compile(r"#\s*api:\s*allow-leaked-type\b")


@dataclass(frozen=True)
class Finding:
    """A problem found by one of the checks."""

    path: Path
    line: int
    check: str
    message: str

    def __str__(self) -> str:
        """Format as ``path:line: check message``."""
        return f"{self.path.relative_to(ROOT)}:{self.line}: {self.check} {self.message}"


@dataclass
class Module:
    """A parsed source module and the names it declares public."""

    name: str
    path: Path
    tree: ast.Module
    lines: list[str]
    declares_all: bool
    exports: list[str] | None
    exports_line: int

    @property
    def is_package(self) -> bool:
        """Whether the module is a package ``__init__``."""
        return self.path.name == "__init__.py"

    @property
    def is_private(self) -> bool:
        """Whether this module, or a package containing it, has a private name."""
        return any(is_private_name(part) for part in self.name.split("."))


def is_private_name(name: str) -> bool:
    """Whether a module name is private: a single leading underscore, not a dunder."""
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


# --- Loading source -----------------------------------------------------------------


def module_name(path: Path) -> str:
    """Return the dotted module name for a source file."""
    parts = path.relative_to(SRC).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def load_modules() -> dict[str, Module]:
    """Parse every module in the package."""
    modules = {}
    for path in sorted((SRC / PACKAGE).rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        name = module_name(path)
        declares_all, exports, line = False, None, 0
        for node in tree.body:
            target = assigned_name(node)
            if target == "__all__" and node.value is not None:
                # A non-literal __all__ gives None here; ruff's PLE0604/PLE0605 report it.
                declares_all = True
                exports, line = literal_strings(node.value), node.lineno
        modules[name] = Module(name, path, tree, source.splitlines(), declares_all, exports, line)
    return modules


def assigned_name(node: ast.stmt) -> str | None:
    """Return the name a simple top-level assignment binds, if any."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
    elif isinstance(node, ast.AnnAssign):
        target = node.target
    else:
        return None
    return target.id if isinstance(target, ast.Name) else None


def literal_strings(value: ast.expr) -> list[str] | None:
    """Return the strings of a literal list/tuple, or None if it is anything else."""
    if not isinstance(value, (ast.List, ast.Tuple)):
        return None
    items = []
    for element in value.elts:
        if not (isinstance(element, ast.Constant) and isinstance(element.value, str)):
            return None
        items.append(element.value)
    return items


def resolve_relative(module: Module, node: ast.ImportFrom) -> str:
    """Return the absolute module name an import-from refers to."""
    if not node.level:
        return node.module or ""
    base = module.name.split(".")
    if not module.is_package:
        base = base[:-1]
    if node.level > 1:
        base = base[: -(node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def bindings(module: Module) -> dict[str, ast.stmt]:
    """Names bound anywhere at the top level of a module, including inside if/try blocks."""
    bound: dict[str, ast.stmt] = {}

    def visit(body: list[ast.stmt]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound[node.name] = node
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bound[(alias.asname or alias.name).split(".")[0]] = node
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for leaf in ast.walk(target):
                        if isinstance(leaf, ast.Name):
                            bound[leaf.id] = node
            elif isinstance(node, (ast.If, ast.Try)):
                visit(node.body)
                visit(node.orelse)
                for handler in getattr(node, "handlers", []):
                    visit(handler.body)
                visit(getattr(node, "finalbody", []))

    visit(module.tree.body)
    return bound


# --- Resolving exported classes and functions -----------------------------------------


def resolve(
    modules: dict[str, Module], module_name: str, name: str, depth: int = 0
) -> tuple[Module, ast.stmt] | None:
    """Follow re-exports until the class or function definition is found."""
    module = modules.get(module_name)
    if module is None or depth > 10:
        return None
    node = bindings(module).get(name)
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return module, node
    if isinstance(node, ast.ImportFrom):
        source = resolve_relative(module, node)
        for alias in node.names:
            if (alias.asname or alias.name) == name:
                return resolve(modules, source, alias.name, depth + 1)
    return None


def public_members(
    modules: dict[str, Module], module: Module, cls: ast.ClassDef, seen: set[int] | None = None
):
    """Yield (module, class name, function) for public methods, including inherited ones."""
    seen = seen if seen is not None else set()
    if id(cls) in seen:
        return
    seen.add(id(cls))
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            not node.name.startswith("_") or node.name == "__init__"
        ):
            yield module, cls.name, node
    for base in cls.bases:
        if isinstance(base, ast.Name):
            found = resolve(modules, module.name, base.id)
            if found and isinstance(found[1], ast.ClassDef):
                yield from public_members(modules, found[0], found[1], seen)


# --- Checks on the source -------------------------------------------------------------


def check_declarations(modules: dict[str, Module]) -> list[Finding]:
    """Check that ``__all__`` is spelled right and that every public package has one."""
    findings = []
    for module in modules.values():
        top_dir = module.path.relative_to(SRC / PACKAGE).parts[0]
        for node in module.tree.body:
            name = assigned_name(node)
            if name and name != "__all__" and name.strip("_").lower() == "all":
                findings.append(
                    Finding(
                        module.path, node.lineno, "misspelled-all", f"'{name}' is not '__all__'"
                    )
                )
        if (
            module.is_package
            and not module.is_private
            and not module.declares_all
            and top_dir not in NON_PYTHON_DIRS
        ):
            findings.append(
                Finding(
                    module.path,
                    1,
                    "missing-all",
                    f"package {module.name} has no __all__ "
                    "(use __all__ = [] if nothing in it is public, or rename it with a "
                    "leading underscore)",
                )
            )
    return findings


def dotnet_names(module: Module) -> set[str]:
    """Return the names a module imports from the .NET namespaces."""
    names = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in DOTNET_ROOTS:
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in DOTNET_ROOTS:
                    names.add((alias.asname or alias.name).split(".")[0])
    return names


def annotation_leaks(annotation: ast.expr, dotnet: set[str]) -> list[str]:
    """Return the names in an annotation that a caller cannot use from the public API."""
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return []
    names = [node.id for node in ast.walk(annotation) if isinstance(node, ast.Name)]
    return [
        name
        for name in names
        if name in dotnet
        or name in DOTNET_ROOTS
        or (name.startswith("_") and not name.startswith("__"))
    ]


def signature_annotations(function: ast.FunctionDef | ast.AsyncFunctionDef):
    """Yield every annotation in a function signature."""
    arguments = function.args
    for arg in [
        *arguments.posonlyargs,
        *arguments.args,
        *arguments.kwonlyargs,
        arguments.vararg,
        arguments.kwarg,
    ]:
        if arg is not None and arg.annotation is not None:
            yield arg.annotation
    if function.returns is not None:
        yield function.returns


def allows_leak(module: Module, function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the function's signature carries the ``# api: allow-leaked-type`` marker."""
    signature = module.lines[function.lineno - 1 : function.body[0].lineno - 1]
    return any(ALLOW_LEAK.search(line) for line in signature)


def public_modules(modules: dict[str, Module]) -> list[Module]:
    """Return the modules whose ``__all__`` is part of the public API."""
    return [module for module in modules.values() if not module.is_private]


def check_signatures(modules: dict[str, Module]) -> list[Finding]:
    """Check that public signatures only mention types a caller can use."""
    findings = []
    seen = set()
    for module in public_modules(modules):
        for name in module.exports or []:
            found = resolve(modules, module.name, name)
            if found is None:
                continue
            owner, node = found
            if isinstance(node, ast.ClassDef):
                functions = list(public_members(modules, owner, node))
            else:
                functions = [(owner, None, node)]
            for defining_module, class_name, function in functions:
                label = f"{class_name}." if class_name else ""
                key = (defining_module.path, function.lineno)
                if key in seen:
                    continue
                seen.add(key)
                dotnet = dotnet_names(defining_module)
                leaks = sorted(
                    {
                        leak
                        for annotation in signature_annotations(function)
                        for leak in annotation_leaks(annotation, dotnet)
                    }
                )
                if leaks and not allows_leak(defining_module, function):
                    findings.append(
                        Finding(
                            defining_module.path,
                            function.lineno,
                            "leaked-type",
                            f"{label}{function.name} exposes {', '.join(leaks)} in its signature",
                        )
                    )
    return findings


# --- Checks against the docs ----------------------------------------------------------


def doc_files() -> list[Path]:
    """Return the tracked docs, notebooks and README."""
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "docs", "notebooks", "README.md"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        paths = [ROOT / p for p in tracked]
    except (OSError, subprocess.CalledProcessError):
        paths = [*ROOT.glob("docs/**/*"), *ROOT.glob("notebooks/*"), ROOT / "README.md"]
    return sorted(p for p in paths if p.suffix in DOC_SUFFIXES and p.is_file())


FENCE = re.compile(r"^```\s*\{?python[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)


def code_blocks(path: Path, text: str):
    """Yield (first line, source) for each Python code block in a doc file."""
    if path.suffix == ".ipynb":
        for cell in json.loads(text).get("cells", []):
            if cell.get("cell_type") == "code":
                yield 1, "".join(cell.get("source", []))
    elif path.suffix in {".qmd", ".md"}:
        for match in FENCE.finditer(text):
            yield text.count("\n", 0, match.start(1)) + 1, match.group(1)


def notebook_text(path: Path, text: str) -> str:
    """Return the searchable text of a doc file, unwrapping notebook JSON."""
    if path.suffix != ".ipynb":
        return text
    return "\n".join("".join(cell.get("source", [])) for cell in json.loads(text).get("cells", []))


def check_doc_imports(modules: dict[str, Module], docs: dict[Path, str]) -> list[Finding]:
    """Check that docs only import names the package exports."""
    findings = []

    def check_module(path: Path, line: int, module_name: str) -> bool:
        """Report a missing or private module; return whether it is usable."""
        module = modules.get(module_name)
        if module is None:
            message = f"'{module_name}' is not a module of the package"
        elif module.is_private:
            message = f"imports from {module_name}, which is private"
        else:
            return True
        findings.append(Finding(path, line, "docs-import", message))
        return False

    def check(path: Path, line: int, module_name: str, name: str) -> None:
        if f"{module_name}.{name}" in modules:
            # Importing a submodule; its own exports are checked where it is used.
            check_module(path, line, f"{module_name}.{name}")
            return
        if not check_module(path, line, module_name):
            return
        module = modules[module_name]
        if module.exports is None:
            message = f"imports '{name}' from {module_name}, which declares no __all__"
        elif name in module.exports:
            return
        else:
            message = f"imports '{name}' from {module_name}, which does not export it"
        findings.append(Finding(path, line, "docs-import", message))

    for path, text in docs.items():
        for first_line, source in code_blocks(path, text):
            lines = [
                "" if line.lstrip().startswith(("%", "!", "#|")) else line
                for line in source.splitlines()
            ]
            try:
                tree = ast.parse("\n".join(lines))
            except SyntaxError:
                continue
            aliases = {}
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and (node.module or "").split(".")[0] == PACKAGE
                ):
                    for alias in node.names:
                        check(path, first_line + node.lineno - 1, node.module, alias.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] == PACKAGE:
                            check_module(path, first_line + node.lineno - 1, alias.name)
                            if alias.asname:
                                aliases[alias.asname] = alias.name
                            elif alias.name == PACKAGE:
                                aliases[PACKAGE] = PACKAGE
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in aliases
                ):
                    check(path, first_line + node.lineno - 1, aliases[node.value.id], node.attr)
    return findings


def check_documented(modules: dict[str, Module], docs: dict[Path, str]) -> list[Finding]:
    """Check that every exported name is mentioned in the docs."""
    corpus = "\n".join(notebook_text(path, text) for path, text in docs.items())
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", corpus))
    findings = []
    reported = set()
    for module in public_modules(modules):
        for name in module.exports or []:
            if name not in words and name not in reported:
                reported.add(name)
                findings.append(
                    Finding(
                        module.path,
                        module.exports_line,
                        "undocumented-export",
                        f"'{name}' is exported but never mentioned in docs/, notebooks/ "
                        "or README.md",
                    )
                )
    return findings


def main() -> int:
    """Run all checks and print the findings."""
    modules = load_modules()
    docs = {path: path.read_text(encoding="utf-8") for path in doc_files()}
    findings = [
        *check_declarations(modules),
        *check_signatures(modules),
        *check_doc_imports(modules, docs),
        *check_documented(modules, docs),
    ]
    for finding in sorted(findings, key=lambda f: (f.check, str(f.path), f.line)):
        print(finding)
    if findings:
        counts: dict[str, int] = {}
        for finding in findings:
            counts[finding.check] = counts.get(finding.check, 0) + 1
        summary = ", ".join(f"{count} {check}" for check, count in sorted(counts.items()))
        print(f"\n{len(findings)} findings: {summary}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
