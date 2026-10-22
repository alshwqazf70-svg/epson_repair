"""اختبارات النسخ الاحتياطي والاستعادة والتصدير."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import Fault, db
from app.utils import create_backup, restore_backup

from .conftest import get_csrf


def test_backup_created_via_route(logged_client, app):
    token = get_csrf(logged_client, "/admin/backups")
    resp = logged_client.post("/admin/backup/create", data={"csrf_token": token},
                              follow_redirects=False)
    assert resp.status_code == 302
    files = sorted(Path(app.config["BACKUP_FOLDER"]).glob("backup-*.zip"))
    assert files, "لم تُنشأ أي نسخة احتياطية"


def test_backup_contains_db_and_uploads(logged_client, app):
    token = get_csrf(logged_client, "/admin/backups")
    logged_client.post("/admin/backup/create", data={"csrf_token": token})
    files = sorted(Path(app.config["BACKUP_FOLDER"]).glob("backup-*.zip"))
    import zipfile
    with zipfile.ZipFile(files[-1]) as zf:
        names = zf.namelist()
    assert any(n.startswith("data/") for n in names), "قاعدة البيانات غير موجودة في النسخة"
    assert any(n == "backup_meta.json" for n in names)


def test_backup_download_requires_login(client, app, logged_client):
    token = get_csrf(logged_client, "/admin/backups")
    logged_client.post("/admin/backup/create", data={"csrf_token": token})
    files = sorted(Path(app.config["BACKUP_FOLDER"]).glob("backup-*.zip"))
    name = files[-1].name
    resp_anon = client.get(f"/admin/backups/{name}/download")
    assert resp_anon.status_code == 302
    resp_ok = logged_client.get(f"/admin/backups/{name}/download")
    assert resp_ok.status_code == 200


def test_backup_download_blocks_traversal(logged_client):
    for bad in ("..%2f..%2fetc%2fpasswd", "backup-../../../etc/passwd.zip", "evil.zip",
                "../../data/test.db"):
        resp = logged_client.get(f"/admin/backups/{bad}/download")
        assert resp.status_code == 404, f"اسم ملف خطير مقبول: {bad}"


def test_restore_roundtrip(app):
    with app.app_context():
        before = Fault.query.count()
        archive = create_backup(app)
    assert archive.is_file()
    # حذف مقالة ثم الاستعادة من النسخة
    with app.app_context():
        victim = Fault.query.first()
        title = victim.title_ar
        db.session.delete(victim)
        db.session.commit()
        assert Fault.query.count() == before - 1
    with app.app_context():
        info = restore_backup(app, archive)
    assert info["db"] is True
    # إعادة فتح الاتصال حتى تُقرأ قاعدة البيانات المستعادة فعلياً
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
        assert Fault.query.count() == before
        assert Fault.query.filter_by(title_ar=title).first() is not None


def test_restore_rejects_non_zip(app, tmp_path):
    bad = tmp_path / "not-a-zip.bin"
    bad.write_bytes(b"definitely not a zip")
    with app.app_context():
        with pytest.raises(ValueError):
            restore_backup(app, bad)


def test_export_json(logged_client, app):
    resp = logged_client.get("/admin/export")
    assert resp.status_code == 200
    payload = resp.get_data(as_text=True)
    data = json.loads(payload)
    assert "faults" in data and "models" in data and "categories" in data
    with app.app_context():
        assert len(data["faults"]) == Fault.query.count()
    assert len(data["models"]) == 2


def test_backups_page_lists_files(logged_client, app):
    token = get_csrf(logged_client, "/admin/backups")
    logged_client.post("/admin/backup/create", data={"csrf_token": token})
    resp = logged_client.get("/admin/backups")
    body = resp.get_data(as_text=True)
    assert "backup-" in body
