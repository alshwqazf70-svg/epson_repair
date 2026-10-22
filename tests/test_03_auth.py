"""اختبارات الدخول والحماية: كلمة المرور الصحيحة/الخاطئة، القفل، حماية مسارات الإدارة."""
from __future__ import annotations

from app.models import ActivityLog, User, db

from .conftest import TEST_PASSWORD, TEST_USERNAME, do_login, get_csrf

ADMIN_PATHS = [
    "/admin/", "/admin/faults", "/admin/faults/new", "/admin/models", "/admin/categories",
    "/admin/images", "/admin/references", "/admin/logs", "/admin/notes", "/admin/backups",
    "/admin/activity", "/admin/search", "/admin/export",
]


def test_login_page_available(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert 'name="csrf_token"' in resp.get_data(as_text=True)


def test_login_success(client):
    resp = do_login(client, TEST_USERNAME, TEST_PASSWORD)
    assert resp.status_code in (200, 302)
    with client.application.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        assert user.failed_attempts == 0
        assert user.last_login_at is not None


def test_login_wrong_password_rejected(client):
    resp = do_login(client, TEST_USERNAME, "wrong-password-999")
    body = resp.get_data(as_text=True)
    assert "غير صحيحة" in body or resp.status_code == 302
    # لم تُمنح جلسة
    resp2 = client.get("/admin/")
    assert resp2.status_code == 302
    assert "/auth/login" in resp2.headers["Location"]


def test_login_unknown_user_rejected(client):
    resp = do_login(client, "no-such-user", TEST_PASSWORD)
    assert resp.status_code in (200, 302)
    assert client.get("/admin/").status_code == 302


def test_account_locks_after_repeated_failures(client, app):
    with app.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        user.failed_attempts = 0
        user.locked_until = None
        db.session.commit()
    for _ in range(5):
        do_login(client, TEST_USERNAME, "bad-pass-123")
    with app.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        assert user.is_locked() is True
    # حتى كلمة المرور الصحيحة تُرفض أثناء القفل
    resp = do_login(client, TEST_USERNAME, TEST_PASSWORD)
    assert resp.status_code == 429
    assert client.get("/admin/").status_code == 302
    with app.app_context():
        assert ActivityLog.query.filter_by(action="login_locked").count() >= 1
    with app.app_context():
        User.query.filter_by(username=TEST_USERNAME).first().locked_until = None
        db.session.commit()


def test_admin_routes_require_login(client):
    for path in ADMIN_PATHS:
        resp = client.get(path)
        assert resp.status_code == 302, f"{path} غير محمي"
        assert "/auth/login" in resp.headers["Location"], path


def test_admin_routes_accessible_when_logged(logged_client):
    html_paths = [p for p in ADMIN_PATHS if p != "/admin/export"]
    for path in html_paths:
        resp = logged_client.get(path)
        assert resp.status_code == 200, f"{path}: {resp.status_code}"
        assert "<html" in resp.get_data(as_text=True)
    export = logged_client.get("/admin/export")
    assert export.status_code == 200
    assert "application/json" in export.headers["Content-Type"]


def test_logout_clears_session(logged_client):
    token = get_csrf(logged_client, "/admin/")
    resp = logged_client.post("/auth/logout", data={"csrf_token": token}, follow_redirects=False)
    assert resp.status_code == 302
    assert logged_client.get("/admin/").status_code == 302


def test_password_is_hashed(app):
    with app.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        assert user.password_hash != TEST_PASSWORD
        assert user.password_hash.startswith("pbkdf2:") or ":" in user.password_hash
        assert user.check_password(TEST_PASSWORD)
        assert not user.check_password("anything-else")


def test_change_password_flow(logged_client, app):
    token = get_csrf(logged_client, "/auth/change-password")
    resp = logged_client.post("/auth/change-password", data={
        "csrf_token": token,
        "current_password": TEST_PASSWORD,
        "new_password": "New-Secret-Pass-2025",
        "confirm_password": "New-Secret-Pass-2025",
    }, follow_redirects=False)
    assert resp.status_code in (200, 302)
    with app.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        assert user.check_password("New-Secret-Pass-2025")
        # إعادة الضبط لما بعد الاختبار
        user.set_password(TEST_PASSWORD)
        db.session.commit()


def test_change_password_rejects_weak_password(logged_client):
    token = get_csrf(logged_client, "/auth/change-password")
    resp = logged_client.post("/auth/change-password", data={
        "csrf_token": token,
        "current_password": TEST_PASSWORD,
        "new_password": "123",
        "confirm_password": "123",
    }, follow_redirects=True)
    body = resp.get_data(as_text=True)
    assert "10 أحرف" in body or "ضعيفة" in body


def test_activity_log_records_login(client, app):
    do_login(client, TEST_USERNAME, TEST_PASSWORD)
    with app.app_context():
        assert ActivityLog.query.filter_by(action="login").count() >= 1


def test_no_password_in_activity_log(client, app):
    do_login(client, TEST_USERNAME, "wrong-pass-xyz")
    with app.app_context():
        for entry in ActivityLog.query.all():
            assert "wrong-pass-xyz" not in (entry.details or "")
            assert TEST_PASSWORD not in (entry.details or "")
