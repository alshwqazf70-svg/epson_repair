"""اختبارات قاعدة البيانات والمحتوى التأسيسي وعدد الأعطال لكل موديل."""
from __future__ import annotations

from app.models import Category, Fault, Image, PrinterModel, Question, Reference, Symptom, db


def test_tables_created(app):
    with app.app_context():
        names = set(db.metadata.tables.keys())
        for expected in ("users", "printer_models", "categories", "faults", "symptoms",
                         "questions", "question_options", "images", "references",
                         "maintenance_logs", "log_attachments", "activity_logs", "notes",
                         "fault_models", "fault_symptoms"):
            assert expected in names, f"الجدول مفقود: {expected}"


def test_seed_counts(app):
    with app.app_context():
        assert PrinterModel.query.count() == 2
        assert Category.query.count() == 9
        assert Fault.query.count() >= 50, "عدد الأعطال التأسيسية قليل جداً"
        assert Symptom.query.count() >= 20
        assert Question.query.count() >= 10
        assert Image.query.count() >= 5
        assert Reference.query.count() >= 4


def test_exactly_two_models(app):
    with app.app_context():
        names = sorted(m.name_en for m in PrinterModel.query.all())
        assert names == ["Epson FX-890", "Epson LX-350"], names


def test_every_fault_belongs_to_a_known_model(app):
    with app.app_context():
        for fault in Fault.query.all():
            assert fault.models, f"العطل بلا موديل: {fault.title_ar}"
            for m in fault.models:
                assert m.slug in {"epson-lx-350", "epson-fx-890"}


def test_faults_are_not_cross_contaminated(app):
    """لا يجوز أن يحتوي عطل خاص بموديل على إجراءات موديل آخر: نتحقق أن لا عطل يحمل موديلين مختلفين
    في نفس الوقت في البذرة التأسيسية (كل مقالة تُكتب لموديل بعينه)."""
    with app.app_context():
        multi = [f.title_ar for f in Fault.query.all() if len(f.models) > 1]
        assert multi == [], f"مقالات مرتبطة بأكثر من موديل: {multi}"


def test_mandatory_fields_present(app):
    with app.app_context():
        for fault in Fault.query.all():
            assert fault.title_ar.strip()
            assert fault.code.strip(), f"رمز فارغ: {fault.title_ar}"
            assert fault.symptoms_text.strip(), f"أعراض فارغة: {fault.title_ar}"
            assert fault.initial_checks, f"فحوصات أولية فارغة: {fault.title_ar}"
            assert fault.diagnosis_tree, f"شجرة تشخيص فارغة: {fault.title_ar}"
            assert fault.stop_when, f"لا يوجد شرط توقف: {fault.title_ar}"
            assert fault.confidence in {"service_manual", "user_manual", "secondary", "unverified"}
            assert fault.status in {"published", "review", "draft"}


def test_part_numbers_only_when_sourced(app):
    """رقم القطعة لا يُعرض إلا مصحوباً بمستوى موثوقية، ولا يُخترع."""
    with app.app_context():
        for fault in Fault.query.all():
            if fault.part_number:
                assert fault.part_number_confidence in {
                    "service_manual", "user_manual", "secondary", "unverified"}
                assert fault.source_name or fault.source_needed, \
                    f"رقم قطعة بلا مصدر: {fault.title_ar}"


def test_unverified_content_is_flagged(app):
    with app.app_context():
        unverified = Fault.query.filter_by(confidence="unverified").all()
        for fault in unverified:
            assert fault.source_needed or fault.status == "review", \
                f"محتوى غير متحقق منه بوسم مراجعة: {fault.title_ar}"


def test_search_blob_computed(app):
    with app.app_context():
        empty = [f.title_ar for f in Fault.query.all() if not (f.search_blob or "").strip()]
        assert empty == [], f"حقول بحث فارغة: {empty[:5]}"


def test_per_model_fault_count(app):
    with app.app_context():
        lx = db.session.get(PrinterModel, PrinterModel.query.filter_by(slug="epson-lx-350").first().id)
        fx = db.session.get(PrinterModel, PrinterModel.query.filter_by(slug="epson-fx-890").first().id)
        assert lx.faults.count() >= 40, f"LX-350: {lx.faults.count()}"
        assert fx.faults.count() >= 40, f"FX-890: {fx.faults.count()}"
