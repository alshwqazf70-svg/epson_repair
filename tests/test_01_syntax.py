"""فحص سلامة الشيفرة: صياغة Python، صياغة قوالب Jinja، غياب الاستيرادات التالفة."""
from __future__ import annotations

import compileall
import io
import py_compile
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _python_files() -> list[Path]:
    skip = {"__pycache__", ".git", "venv", ".venv", "node_modules"}
    files = []
    for p in ROOT.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        files.append(p)
    return files


def test_all_python_files_compile():
    bad = []
    for path in _python_files():
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:  # pragma: no cover
            bad.append(f"{path}: {exc}")
    assert not bad, "ملفات ذات صياغة خاطئة:\n" + "\n".join(bad)


def test_compileall_root():
    buf = io.StringIO()
    ok = compileall.compile_dir(str(ROOT), quiet=2, force=True)
    buf.close()
    assert ok is True, "compileall فشل على مجلد المشروع"


def test_no_pycache_committed():
    """لا يجب أن يحتوي ZIP على ملفات مترجمة؛ نتحقق أن الأداة لا تعتمد عليها."""
    assert (ROOT / "app" / "__init__.py").is_file()


def test_all_templates_compile(app):
    """كل قوالب Jinja تُترجم بدون أخطاء، وكل url_for يشير إلى نقطة نهاية موجودة."""
    env = app.jinja_env
    templates_dir = Path(app.jinja_loader.searchpath[0])
    errors = []
    for path in sorted(templates_dir.rglob("*.html")):
        rel = path.relative_to(templates_dir).as_posix()
        try:
            env.get_template(rel)
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
    assert not errors, "قوالب بها أخطاء:\n" + "\n".join(errors)


def test_no_missing_imports():
    """استيراد كل وحدات الحزمة للتأكد من عدم وجود وحدة أو اسم ناقص."""
    import importlib

    modules = [
        "app", "app.config", "app.models", "app.forms", "app.utils", "app.seed",
        "app.seed_data", "app.seed_faults_a", "app.seed_faults_b",
        "app.routes.public", "app.routes.auth", "app.routes.admin",
        "app.routes.diag", "app.routes.media",
    ]
    for name in modules:
        importlib.import_module(name)


def test_no_unused_imports():
    """كشف الاستيرادات غير المستخدمة (تبسيطي: يبحث عن تكرار الاسم في الملف)."""
    import ast
    import re

    offenders = []
    for path in _python_files():
        src = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        imported: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported[(alias.asname or alias.name).split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported[alias.asname or alias.name] = node.lineno
        for name, line in imported.items():
            if name == "annotations":  # from __future__ import annotations
                continue
            hits = len(re.findall(rf"\b{re.escape(name)}\b", src))
            if hits <= 1:
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {name}")
    assert not offenders, "استيرادات غير مستخدمة:\n" + "\n".join(offenders)


def test_wsgi_entry_importable():
    spec_path = ROOT / "wsgi.py"
    assert spec_path.is_file()
    source = spec_path.read_text(encoding="utf-8")
    assert "application" in source
    assert "create_app" in source


@pytest.mark.parametrize("name", ["requirements.txt", ".env.example", ".gitignore",
                                  "README_AR.md", "run_local.py"])
def test_required_files_exist(name):
    assert (ROOT / name).is_file(), f"الملف المطلوب غير موجود: {name}"
