"""代码整洁度检查：找出**真正**未使用的 import、过长的行、遗留标记。

按作用域统计：只有当一个 import 在它所在的作用域及其所有子作用域里都没被引用时，
才会被报告。不修改任何文件，只输出报告。
"""

from __future__ import annotations

import ast
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
PKG = CODE_DIR / "gwp"
MAX_LINE = 140      # themes.py 里是成段的 CSS 字符串，放宽一些


class Scope:
    def __init__(self, parent: "Scope | None", node: ast.AST) -> None:
        self.parent = parent
        self.node = node
        self.children: list[Scope] = []
        self.imports: dict[str, int] = {}      # 名字 -> 行号
        self.used: set[str] = set()
        if parent is not None:
            parent.children.append(self)


def _collect_names(node: ast.AST) -> set[str]:
    """收集一个节点里出现的所有标识符（考虑属性链的根）。"""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            root = child
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                names.add(root.id)
        elif isinstance(child, ast.arg):
            if child.annotation is not None:
                names |= _collect_annotation_names(child.annotation)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in child.decorator_list:
                names |= _collect_annotation_names(decorator)
        elif isinstance(child, ast.AnnAssign) and child.annotation is not None:
            names |= _collect_annotation_names(child.annotation)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            # 字符串注解，例如 "Config" / "list[Book]"
            for token in _split_identifiers(child.value):
                names.add(token)
    return names


def _collect_annotation_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            root = child
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                names.add(root.id)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            names |= _split_identifiers(child.value)
    return names


def _split_identifiers(text: str) -> set[str]:
    tokens: set[str] = set()
    current = ""
    for char in text:
        if char.isalnum() or char == "_":
            current += char
        else:
            if current:
                tokens.add(current)
            current = ""
    if current:
        tokens.add(current)
    return tokens


def build_scopes(tree: ast.AST) -> Scope:
    root = Scope(None, tree)

    def visit(node: ast.AST, scope: Scope) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                child_scope = Scope(scope, child)
                # 装饰器与默认参数在**外层**作用域求值
                for decorator in child.decorator_list:
                    scope.used |= _collect_annotation_names(decorator)
                for default in list(child.args.defaults if hasattr(child, "args") else []):
                    scope.used |= _collect_names(default)
                if isinstance(child, ast.ClassDef):
                    for base in child.bases:
                        scope.used |= _collect_names(base)
                visit(child, child_scope)
                continue
            if isinstance(child, ast.Import):
                for alias in child.names:
                    if alias.name == "__future__":
                        continue          # 编译器指令，不是真正的导入
                    name = alias.asname or alias.name.split(".")[0]
                    scope.imports.setdefault(name, child.lineno)
            elif isinstance(child, ast.ImportFrom):
                if child.module == "__future__":
                    continue
                for alias in child.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    scope.imports.setdefault(name, child.lineno)
            elif isinstance(child, (ast.Name, ast.Attribute)):
                scope.used |= _collect_names(child)
            else:
                if isinstance(child, ast.Constant) and isinstance(child.value, str):
                    scope.used |= _split_identifiers(child.value)
                visit(child, scope)

    visit(tree, root)
    return root


def unused_imports(path: Path, source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"语法错误: {exc}"]

    # 显式标记 # noqa 的行（例如"为副作用而导入"）视为有意为之
    noqa_lines = {
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if "# noqa" in line
    }

    root = build_scopes(tree)
    report: list[tuple[int, str]] = []

    def used_in_subtree(scope: Scope, name: str, text: str) -> bool:
        if name in scope.used:
            return True
        # 名字出现在字符串里（例如 __all__ 或文档）也算被引用
        if f'"{name}"' in text or f"'{name}'" in text:
            return True
        if name in getattr(scope.node, "name", ""):
            return True
        for child in scope.children:
            if used_in_subtree(child, name, text):
                return True
        return False

    def walk(scope: Scope) -> None:
        for name, line in scope.imports.items():
            if line in noqa_lines:
                continue
            # 在导入点之后（含子作用域）是否被使用
            if not used_in_subtree(scope, name, source):
                report.append((line, name))
        for child in scope.children:
            walk(child)

    walk(root)
    return [f"第 {line} 行：{name}" for line, name in sorted(set(report))]


def long_lines(source: str) -> list[str]:
    return [
        f"第 {number} 行（{len(line)} 字符）"
        for number, line in enumerate(source.splitlines(), start=1)
        if len(line) > MAX_LINE
    ]


def markers(source: str) -> list[str]:
    issues = []
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "#" in stripped:
            comment = stripped.split("#", 1)[1]
            for token in ("TODO", "FIXME", "XXX", "HACK"):
                if token in comment:
                    issues.append(f"第 {number} 行：{stripped[:90]}")
                    break
    return issues


def main() -> int:
    files = sorted(PKG.rglob("*.py"))
    total = 0
    for path in files:
        source = path.read_text(encoding="utf-8")
        problems = []
        for label, items in (
            ("未使用的 import", unused_imports(path, source)),
            (f"超过 {MAX_LINE} 字符的行", long_lines(source)),
            ("遗留标记", markers(source)),
        ):
            if items:
                problems.append((label, items))
        if problems:
            print(f"\n{path.relative_to(CODE_DIR)}")
            for label, items in problems:
                print(f"  [{label}] {len(items)} 处")
                for item in items[:15]:
                    print(f"    - {item}")
                total += len(items)

    print()
    print(f"检查了 {len(files)} 个文件，共 {total} 处提示。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
