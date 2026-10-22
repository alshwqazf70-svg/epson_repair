"""اختبارات CRUD الفعلية على الأعطال والتصنيفات وسجلات الصيانة والملاحظات."""
from __future__ import annotations

from datetime import date

from app.models import Category, Fault, MaintenanceLog, Note, PrinterModel, db

from .conftest import get_csrf


def _fault_payload(csrf: str, model_id: int, category_id: int, title: str) -> dict:
    return {
        "csrf_token": csrf,
        "title_ar": title,
        "title_en": "Test Fault Entry",
        "category_id": str(category_id),
        "model_ids": str(model_id),
        "code": "لا يوجد رمز موثق",
        "severity": "medium",
        "symptoms_text": "عرض اختباري للتحقق من الحفظ.",
        "causes": "سبب أول\nسبب ثانٍ",
        "suspect_part": "منطقة اختبارية",
        "part_number": "",
        "part_number_confidence": "unverified",
        "tools": "مفك",
        "initial_checks": "فحص أولي آمن.",
        "diagnosis_tree": "1) خطوة أولى\n2) خطوة ثانية",
        "repair_steps": "خطوات الإصلاح التجريبية.",
        "verification": "التحقق بالطباعة التجريبية.",
        "final_test": "طباعة صفحة اختبار.",
        "common_mistakes": "خطأ شائع.",
        "stop_when": "عند ظهور دخان توقف فوراً.",
        "safety_note": "افصل الطاقة قبل الفتح.",
        "source_name": "ملاحظة داخلية",
        "source_url": "",
        "source_needed": "مصدر فني مطلوب للتحقق.",
        "reviewed_at": date.today().isoformat(),
        "confidence": "unverified",
        "status": "draft",
    }


def test_create_fault(logged_client, app):
    with app.app_context():
        model = PrinterModel.query.filter_by(slug="epson-lx-350").first()
        cat = Category.query.first()
        before = Fault.query.count()
    csrf = get_csrf(logged_client, "/admin/faults/new")
    resp = logged_client.post("/admin/faults/new", data=_fault_payload(
        csrf, model.id, cat.id, "عطل اختباري للتحقق من الحفظ"), follow_redirects=False)
    assert resp.status_code == 302, resp.get_data(as_text=True)[:400]
    with app.app_context():
        assert Fault.query.count() == before + 1
        fault = Fault.query.filter_by(title_ar="عطل اختباري للتحقق من الحفظ").first()
        assert fault is not None
        assert fault.slug
        assert fault.status == "draft"
        assert "epson-lx-350" in [m.slug for m in fault.models]
        assert (fault.search_blob or "").strip()


def test_create_fault_requires_title(logged_client, app):
    with app.app_context():
        model = PrinterModel.query.first()
        cat = Category.query.first()
        before = Fault.query.count()
    csrf = get_csrf(logged_client, "/admin/faults/new")
    payload = _fault_payload(csrf, model.id, cat.id, "   ")
    resp = logged_client.post("/admin/faults/new", data=payload)
    assert resp.status_code == 200  # لم يتم الحفظ، وأُعيد عرض النموذج
    with app.app_context():
        assert Fault.query.count() == before


def test_edit_fault(logged_client, app):
    with app.app_context():
        fault = Fault.query.first()
        fid = fault.id
    csrf = get_csrf(logged_client, f"/admin/faults/{fid}/edit")
    payload = _fault_payload(csrf, 1, 1, "عنوان بعد التعديل")
    payload["title_ar"] = "عنوان معدّل بالكامل"
    payload["status"] = "published"
    resp = logged_client.post(f"/admin/faults/{fid}/edit", data=payload, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        fault = db.session.get(Fault, fid)
        assert fault.title_ar == "عنوان معدّل بالكامل"
        assert fault.status == "published"


def test_delete_fault(logged_client, app):
    with app.app_context():
        fault = Fault.query.first()
        fid = fault.id
        before = Fault.query.count()
    csrf = get_csrf(logged_client, "/admin/")
    resp = logged_client.post(f"/admin/faults/{fid}/delete", data={"csrf_token": csrf})
    assert resp.status_code == 302
    with app.app_context():
        assert Fault.query.count() == before - 1


def test_category_crud(logged_client, app):
    csrf = get_csrf(logged_client, "/admin/categories/new")
    resp = logged_client.post("/admin/categories/new", data={
        "csrf_token": csrf, "name_ar": "تصنيف اختباري", "name_en": "Test Category",
        "description": "وصف", "icon": "", "sort_order": "99"}, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        cat = Category.query.filter_by(name_ar="تصنيف اختباري").first()
        assert cat is not None
        cid = cat.id
    csrf = get_csrf(logged_client, f"/admin/categories/{cid}/edit")
    resp = logged_client.post(f"/admin/categories/{cid}/edit", data={
        "csrf_token": csrf, "name_ar": "تصنيف اختباري معدل", "name_en": "Test Category",
        "description": "وصف", "icon": "", "sort_order": "99"}, follow_redirects=False)
    assert resp.status_code == 302
    csrf = get_csrf(logged_client, "/admin/")
    resp = logged_client.post(f"/admin/categories/{cid}/delete", data={"csrf_token": csrf})
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Category, cid) is None


def test_maintenance_log_crud(logged_client, app):
    with app.app_context():
        model = PrinterModel.query.filter_by(slug="epson-fx-890").first()
    csrf = get_csrf(logged_client, "/admin/logs/new")
    resp = logged_client.post("/admin/logs/new", data={
        "csrf_token": csrf,
        "model_id": str(model.id),
        "fault_id": "0",
        "log_date": date.today().isoformat(),
        "title": "صيانة اختبارية",
        "symptoms": "انحشار ورق",
        "initial_diagnosis": "مسار الورق",
        "tests_done": "تغذية يدوية",
        "parts_cleaned": "بكرات التغذية",
        "parts_replaced": "لا شيء",
        "repair_done": "تنظيف البكرات",
        "result": "success",
        "notes": "ملاحظة",
    }, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        entry = MaintenanceLog.query.filter_by(title="صيانة اختبارية").first()
        assert entry is not None
        assert entry.model.slug == "epson-fx-890"
        assert entry.result_label == "نجح الإصلاح"
        log_id = entry.id
    resp = logged_client.get(f"/admin/logs/{log_id}")
    assert resp.status_code == 200
    resp = logged_client.get(f"/admin/logs/{log_id}/print")
    assert resp.status_code == 200
    csrf = get_csrf(logged_client, "/admin/")
    resp = logged_client.post(f"/admin/logs/{log_id}/delete", data={"csrf_token": csrf})
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(MaintenanceLog, log_id) is None


def test_note_crud(logged_client, app):
    csrf = get_csrf(logged_client, "/admin/notes/new")
    resp = logged_client.post("/admin/notes/new", data={
        "csrf_token": csrf, "title": "ملاحظة اختبارية", "body": "نص", "model_id": "0"},
        follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        note = Note.query.filter_by(title="ملاحظة اختبارية").first()
        assert note is not None
        nid = note.id
    csrf = get_csrf(logged_client, "/admin/")
    resp = logged_client.post(f"/admin/notes/{nid}/delete", data={"csrf_token": csrf})
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Note, nid) is None


def test_model_form_renders_and_saves(logged_client, app):
    csrf = get_csrf(logged_client, "/admin/models/new")
    resp = logged_client.post("/admin/models/new", data={
        "csrf_token": csrf, "name_ar": "موديل اختباري", "name_en": "Epson TEST-100",
        "printer_class": "نقطية", "pins": "9", "columns": "80", "interfaces": "USB",
        "ribbon_part": "", "ribbon_part_confidence": "unverified", "mtbf": "",
        "print_head_life": "", "memory": "", "paper_paths": "خلفي", "summary": "نبذة",
        "specs_note": "غير متحقق منه", "sort_order": "50", "is_active": "y"},
        follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        assert PrinterModel.query.filter_by(name_en="Epson TEST-100").first() is not None
        extra = PrinterModel.query.filter_by(name_en="Epson TEST-100").first()
        db.session.delete(extra)
        db.session.commit()
