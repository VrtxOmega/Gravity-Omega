"""
Omega Claw — Repository Map
==============================
AST-based codebase index. Pattern from Aider's repomap.py.

Scans a workspace and builds a structural map of all Python files:
  - Classes and their methods
  - Top-level functions with signatures
  - Import graph (what depends on what)

This map is injected into the agent's LLM context so Omega understands
the codebase structure without reading every file in full.
Zero external dependencies — uses Python's built-in ast module.
"""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════

@dataclass
class FunctionInfo:
    name: str
    args: List[str]
    returns: str
    line: int
    docstring: str = ""
    is_method: bool = False

    def signature(self) -> str:
        args_str = ", ".join(self.args)
        ret = f" -> {self.returns}" if self.returns else ""
        return f"{self.name}({args_str}){ret}"


@dataclass
class ClassInfo:
    name: str
    line: int
    bases: List[str]
    methods: List[FunctionInfo] = field(default_factory=list)
    docstring: str = ""

    def summary(self) -> str:
        base_str = f"({', '.join(self.bases)})" if self.bases else ""
        methods = [f"    .{m.signature()}" for m in self.methods]
        return f"class {self.name}{base_str}\n" + "\n".join(methods)


@dataclass
class FileMap:
    path: str
    relative_path: str
    imports: List[str]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    line_count: int

    def summary(self, max_funcs: int = 10, max_methods: int = 5) -> str:
        """Compact summary for LLM context injection."""
        parts = [f"# {self.relative_path} ({self.line_count} lines)"]

        if self.imports:
            parts.append(f"  imports: {', '.join(self.imports[:8])}")

        for cls in self.classes:
            base_str = f"({', '.join(cls.bases)})" if cls.bases else ""
            parts.append(f"  class {cls.name}{base_str}:")
            if cls.docstring:
                parts.append(f"    \"{cls.docstring[:80]}\"")
            for m in cls.methods[:max_methods]:
                parts.append(f"    .{m.signature()}")
            if len(cls.methods) > max_methods:
                parts.append(f"    ... +{len(cls.methods) - max_methods} more methods")

        for fn in self.functions[:max_funcs]:
            parts.append(f"  def {fn.signature()}")
            if fn.docstring:
                parts.append(f"    \"{fn.docstring[:60]}\"")
        if len(self.functions) > max_funcs:
            parts.append(f"  ... +{len(self.functions) - max_funcs} more functions")

        return "\n".join(parts)


# ══════════════════════════════════════════════════════════════
# AST EXTRACTORS
# ══════════════════════════════════════════════════════════════

def _get_docstring(node: ast.AST) -> str:
    """Extract docstring from a function or class node."""
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)):
        val = node.body[0].value
        if isinstance(val.value, str):
            return val.value.strip().split("\n")[0][:100]
    return ""


def _get_return_annotation(node: ast.FunctionDef) -> str:
    """Extract return type annotation."""
    if node.returns:
        return ast.dump(node.returns) if not isinstance(node.returns, ast.Constant) else str(node.returns.value)
    return ""


def _get_arg_names(node: ast.FunctionDef) -> List[str]:
    """Extract argument names with type annotations."""
    args = []
    for arg in node.args.args:
        name = arg.arg
        if arg.annotation:
            try:
                ann = ast.unparse(arg.annotation)
                name = f"{name}: {ann}"
            except Exception:
                pass
        args.append(name)
    return args


def _extract_imports(tree: ast.Module) -> List[str]:
    """Extract imported module names."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return sorted(set(imports))


def _extract_functions(tree: ast.Module) -> List[FunctionInfo]:
    """Extract top-level functions (not methods)."""
    funcs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(FunctionInfo(
                name=node.name,
                args=_get_arg_names(node),
                returns=_get_return_annotation(node),
                line=node.lineno,
                docstring=_get_docstring(node),
                is_method=False,
            ))
    return funcs


def _extract_classes(tree: ast.Module) -> List[ClassInfo]:
    """Extract class definitions with methods."""
    classes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    bases.append("?")

            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(FunctionInfo(
                        name=item.name,
                        args=_get_arg_names(item),
                        returns=_get_return_annotation(item),
                        line=item.lineno,
                        docstring=_get_docstring(item),
                        is_method=True,
                    ))

            classes.append(ClassInfo(
                name=node.name,
                line=node.lineno,
                bases=bases,
                methods=methods,
                docstring=_get_docstring(node),
            ))
    return classes


# ══════════════════════════════════════════════════════════════
# REPO MAP BUILDER
# ══════════════════════════════════════════════════════════════

class RepoMap:
    """AST-based workspace index.

    Usage:
        repo = RepoMap("/path/to/workspace")
        repo.scan()
        context = repo.get_context()         # Full map for LLM
        context = repo.get_relevant("foo")   # Only files mentioning "foo"
    """

    def __init__(self, root: str, exclude_dirs: Optional[Set[str]] = None):
        self._root = Path(root).resolve()
        self._exclude = exclude_dirs or {
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".pytest_cache", ".mypy_cache", "dist", "build", ".eggs",
        }
        self._files: Dict[str, FileMap] = {}

    def scan(self) -> int:
        """Scan the workspace and build the map. Returns file count."""
        self._files.clear()
        count = 0
        for root, dirs, files in os.walk(self._root):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in self._exclude]
            for fname in sorted(files):
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                fmap = self._parse_file(fpath)
                if fmap:
                    self._files[fpath] = fmap
                    count += 1
        return count

    def _parse_file(self, filepath: str) -> Optional[FileMap]:
        """Parse a single Python file into a FileMap."""
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=filepath)
        except (SyntaxError, OSError):
            return None

        rel = os.path.relpath(filepath, self._root)
        return FileMap(
            path=filepath,
            relative_path=rel,
            imports=_extract_imports(tree),
            classes=_extract_classes(tree),
            functions=_extract_functions(tree),
            line_count=content.count("\n") + 1,
        )

    def get_context(self, max_files: int = 30, max_chars: int = 8000) -> str:
        """Get full repo map as LLM context. Respects token budget."""
        parts = [f"[REPO MAP: {self._root.name}/ — {len(self._files)} files]\n"]
        total = 0
        for fmap in sorted(self._files.values(), key=lambda f: f.relative_path):
            summary = fmap.summary()
            if total + len(summary) > max_chars:
                parts.append(f"\n... +{len(self._files) - len(parts) + 1} more files (truncated)")
                break
            parts.append(summary)
            total += len(summary)
        return "\n".join(parts)

    def get_relevant(self, query: str, max_files: int = 10) -> str:
        """Get map entries relevant to a query (by name matching)."""
        query_lower = query.lower()
        scored = []
        for fmap in self._files.values():
            score = 0
            # Check filename
            if query_lower in fmap.relative_path.lower():
                score += 3
            # Check class names
            for cls in fmap.classes:
                if query_lower in cls.name.lower():
                    score += 2
                for m in cls.methods:
                    if query_lower in m.name.lower():
                        score += 1
            # Check function names
            for fn in fmap.functions:
                if query_lower in fn.name.lower():
                    score += 2
            # Check imports
            for imp in fmap.imports:
                if query_lower in imp.lower():
                    score += 1
            if score > 0:
                scored.append((score, fmap))

        scored.sort(key=lambda x: -x[0])
        parts = [f"[RELEVANT FILES for '{query}']"]
        for _, fmap in scored[:max_files]:
            parts.append(fmap.summary())
        if not scored:
            parts.append("(no matches)")
        return "\n".join(parts)

    def get_file_map(self, filepath: str) -> Optional[FileMap]:
        """Get the map for a specific file."""
        resolved = str(Path(filepath).resolve())
        return self._files.get(resolved)

    @property
    def file_count(self) -> int:
        return len(self._files)

    @property
    def total_lines(self) -> int:
        return sum(f.line_count for f in self._files.values())
