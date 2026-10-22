"""اختبارات الرفع الآمن: نوع الملف، الحجم، منع التنفيذ، وحماية الملفات الخاصة."""
from __future__ import annotations

import io

from app.models import Image

from .conftest import get_csrf

PNG_BYTES = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
JPEG_BYTES = (b"\xff\xd8\xff\xe0" + b"\x00" * 40)


def _upload(client, filename: str, content: bytes, csrf_path: str = "/admin/images/new"):
    token = get_csrf(client, csrf_path)
    return client.post("/admin/images/new", data={
        "csrf_token": token,
        "title": f"صورة اختبار {filename}",
        "description": "وصف",
        "model_id": "0",
        "fault_id": "0",
        "image_type": "photo",
        "source": "رفع اختباري",
        "license_note": "",
        "step_hint": "",
        "file": (io.BytesIO(content), filename),
    }, content_type="multipart/form-data", follow_redirects=False)


def test_allowed_png_upload_accepted(logged_client, app):
    with app.app_context():
        before = Image.query.count()
    resp = _upload(logged_client, "test-image.png", PNG_BYTES)
    assert resp.status_code == 302, resp.get_data(as_text=True)[:500]
    with app.app_context():
        assert Image.query.count() == before + 1
        img = Image.query.order_by(Image.id.desc()).first()
        assert img.storage == "uploaded"
        assert img.filename.startswith("images/")


def test_allowed_jpeg_upload_accepted(logged_client, app):
    with app.app_context():
        before = Image.query.count()
    resp = _upload(logged_client, "photo.jpg", JPEG_BYTES)
    assert resp.status_code == 302
    with app.app_context():
        assert Image.query.count() == before + 1


def test_executable_extension_rejected(logged_client, app):
    with app.app_context():
        before = Image.query.count()
    resp = _upload(logged_client, "payload.exe", b"MZ\x00\x00" + b"\x00" * 40)
    assert resp.status_code == 200  # أُعيد عرض النموذج مع رسالة خطأ
    assert "نوع صورة غير مسموح" in resp.get_data(as_text=True)
    with app.app_context():
        assert Image.query.count() == before


def test_php_script_rejected(logged_client, app):
    with app.app_context():
        before = Image.query.count()
    resp = _upload(logged_client, "shell.php.png", b"<?php system($_GET[0]); ?>")
    assert resp.status_code in (200, 400)
    with app.app_context():
        assert Image.query.count() == before


def test_fake_png_content_rejected(logged_client, app):
    """امتداد صورة لكن المحتوى ليس صورة: يُرفض بالتحقق الفعلي من توقيع البايتات."""
    with app.app_context():
        before = Image.query.count()
    resp = _upload(logged_client, "notreally.png", b"just plain text content")
    assert resp.status_code == 400
    with app.app_context():
        assert Image.query.count() == before


def test_uploaded_file_stored_outside_static(logged_client, app):
    _upload(logged_client, "outside-static.png", PNG_BYTES)
    with app.app_context():
        img = Image.query.order_by(Image.id.desc()).first()
        rel = img.filename
    root = app.config["UPLOAD_FOLDER"]
    assert str(app.config["TEST_ROOT"]) in str(root)
    assert "static" not in str(root)
    assert rel.startswith("images/")


def test_private_file_blocked_for_anonymous(client, app, logged_client):
    resp = _upload(logged_client, "private-one.png", PNG_BYTES)
    assert resp.status_code == 302
    with app.app_context():
        img = Image.query.order_by(Image.id.desc()).first()
        rel = img.filename
    anon = client.get(f"/media/{rel}")
    assert anon.status_code == 403, "الملف الخاص متاح للزوار المجهولين!"
    ok = logged_client.get(f"/media/{rel}")
    assert ok.status_code == 200


def test_path_traversal_blocked(logged_client):
    for attempt in ("../../etc/passwd", "..%2f..%2fetc%2fpasswd",
                    "images/../../../etc/passwd", "....//....//etc/passwd"):
        resp = logged_client.get(f"/media/{attempt}")
        assert resp.status_code in (403, 404), f"مسار خطير مسموح: {attempt}"


def test_unique_filenames(logged_client, app):
    _upload(logged_client, "dup.png", PNG_BYTES)
    _upload(logged_client, "dup.png", PNG_BYTES)
    with app.app_context():
        rows = Image.query.filter(Image.storage == "uploaded").all()
        names = [r.filename for r in rows]
        assert len(names) == len(set(names)), "أسماء الملفات ليست فريدة"


def test_upload_page_requires_login(client):
    resp = client.get("/admin/images/new")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
