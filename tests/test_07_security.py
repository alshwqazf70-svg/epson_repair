"""اختبارات الحماية: CSRF، ترويسات الأمان، صفحات الخطأ، غياب الأسرار، سلامة الجلسة."""
from __future__ import annotations

import re
from pathlib import Path

from app.models import Fault, db

ROOT = Path(__file__).resolve().parent.parent


def test_csrf_token_present_in_forms(logged_client):
    for path in ("/admin/faults/new", "/admin/images/new", "/admin/logs/new",
                 "/admin/notes/new", "/admin/references/new", "/admin/models/new"):
        body = logged_client.get(path).get_data(as_text=True)
        assert 'name="csrf_token"' in body, f"نموذج بلا حماية CSRF: {path}"


def test_post_without_csrf_rejected(logged_client, app):
    with app.app_context():
        before = Fault.query.count()
    resp = logged_client.post("/admin/faults/new", data={"title_ar": "بدون توكن"},
                              follow_redirects=False)
    assert resp.status_code == 400, "طلب POST بلا توكن CSRF لم يُرفض"
    with app.app_context():
        assert Fault.query.count() == before


def test_post_with_invalid_csrf_rejected(logged_client, app):
    with app.app_context():
        before = Fault.query.count()
    resp = logged_client.post("/admin/faults/new",
                              data={"csrf_token": "invalid-token-value", "title_ar": "x"})
    assert resp.status_code == 400
    with app.app_context():
        assert Fault.query.count() == before


def test_login_post_without_csrf_rejected(client):
    resp = client.post("/auth/login", data={"username": "a", "password": "b"})
    assert resp.status_code == 400


def test_security_headers(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")


def test_no_external_resources(client):
    """لا اعتماد على Google Fonts أو أي CDN خارجي."""
    body = client.get("/").get_data(as_text=True)
    for bad in ("fonts.googleapis", "cdn.jsdelivr", "unpkg.com", "cdnjs.cloudflare"):
        assert bad not in body, f"اعتماد خارجي ممنوع: {bad}"


def test_404_page(client):
    resp = client.get("/this-page-does-not-exist-xyz")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    assert "404" in body


def test_403_page(client):
    resp = client.get("/media/private.png")
    assert resp.status_code == 403
    assert "403" in resp.get_data(as_text=True)


def test_500_page(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    client = app.test_client()
    resp = client.get("/_test/500")
    assert resp.status_code == 500
    body = resp.get_data(as_text=True)
    assert "500" in body
    assert "RuntimeError" not in body, "تفاصيل الخطأ ظهرت للمستخدم (تسريب معلومات)"


def test_xss_is_escaped(client, app):
    with app.app_context():
        fault = Fault.query.first()
        fault.title_ar = "<script>alert('xss')</script> عنوان"
        db.session.commit()
        slug = fault.slug
    resp = client.get(f"/search?q=" + "%3Cscript%3E")
    body = resp.get_data(as_text=True)
    assert "<script>alert" not in body


def test_no_hardcoded_secrets_in_source():
    patterns = [
        r"SECRET_KEY\s*=\s*['\"][^'\"]{16,}['\"]",
        r"PASSWORD\s*=\s*['\"][^'\"]{8,}['\"]",
    ]
    offenders = []
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            for m in re.finditer(pat, text):
                value = m.group(0)
                if "change-me" in value or "example" in value.lower() or "getenv" in value:
                    continue
                offenders.append(f"{path}: {value}")
    assert not offenders, "أسرار ثابتة داخل الشيفرة:\n" + "\n".join(offenders)


def test_env_example_has_no_real_secret():
    env = (ROOT / ".env.example")
    assert env.is_file()
    text = env.read_text(encoding="utf-8")
    lowered = text.lower()
    for bad in ("change-me", "your-", "example", "put-", "××", "xxx"):
        pass
    assert "SECRET_KEY" in text
    # لا قيمة حقيقية: يجب أن تكون القيم نائبة
    assert re.search(r"SECRET_KEY\s*=\s*(change-me|your-|.*example.*)", text, re.I)


def test_gitignore_excludes_secrets_and_db():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needed in (".env", "__pycache__", "*.db", "private_uploads", "*.pyc"):
        assert needed in text, f".gitignore لا يستثني: {needed}"


def test_debug_disabled_by_default(app):
    assert app.config.get("DEBUG") is False


def test_session_cookie_flags(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] in {"Lax", "Strict"}
