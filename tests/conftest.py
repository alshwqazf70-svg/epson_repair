"""تهيئة مشتركة للاختبارات: قاعدة بيانات منفصلة داخل مجلد مؤقت، ومستخدم مالك للاختبار."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.models import User, db  # noqa: E402
from app.seed import seed_all  # noqa: E402

TEST_USERNAME = "owner-test"
TEST_PASSWORD = "S3cure-Passphrase-2024"


@pytest.fixture()
def app(tmp_path_factory):
    """تطبيق اختبار مع قاعدة بيانات ومجلدات مؤقتة منفصلة تماماً عن بيانات المشروع."""
    root = tmp_path_factory.mktemp("epsonrm")
    db_path = root / "data" / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    uploads = root / "private_uploads"
    backups = root / "backups"
    uploads.mkdir(parents=True, exist_ok=True)
    backups.mkdir(parents=True, exist_ok=True)

    application = create_app("testing", database_uri=f"sqlite:///{db_path}")
    application.config.update(
        DATABASE_PATH=str(db_path),
        UPLOAD_FOLDER=str(uploads),
        BACKUP_FOLDER=str(backups),
        WTF_CSRF_ENABLED=True,
        SERVER_NAME=None,
    )
    application.config["TEST_ROOT"] = str(root)

    with application.app_context():
        db.create_all()
        seed_all(force=True)
        if User.query.filter_by(username=TEST_USERNAME).first() is None:
            user = User(username=TEST_USERNAME, display_name="مالك الاختبار")
            user.set_password(TEST_PASSWORD)
            db.session.add(user)
            db.session.commit()

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_client(app):
    """عميل مسجل الدخول (جلسة مستقلة تماماً عن عميل الزائر المجهول)."""
    session_client = app.test_client()
    do_login(session_client, TEST_USERNAME, TEST_PASSWORD)
    return session_client


# ------------------------------------------------------------------ مساعدات


def get_csrf(client, path: str = "/auth/login") -> str:
    """يقرأ توكن CSRF الصالح من صفحة نموذج حقيقية."""
    resp = client.get(path)
    assert resp.status_code == 200, f"تعذّر فتح {path} لاستخراج توكن CSRF"
    html = resp.get_data(as_text=True)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if not match:
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, "لم يُعثر على توكن CSRF في الصفحة"
    return match.group(1)


def do_login(client, username: str, password: str):
    token = get_csrf(client, "/auth/login")
    return client.post("/auth/login", data={
        "csrf_token": token,
        "username": username,
        "password": password,
    }, follow_redirects=False)
