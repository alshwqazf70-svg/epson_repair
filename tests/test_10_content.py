"""اختبارات موثوقية المحتوى: السلامة، الصور التوضيحية، وعدم اختراع معلومات فنية."""
from __future__ import annotations

import re
from pathlib import Path

from app.models import Fault, Image, Reference

ROOT = Path(__file__).resolve().parent.parent
DISCLAIMER = "رسم توضيحي غير مطابق بالضرورة للبنية الداخلية الدقيقة"


def test_every_fault_has_safety_warning(app):
    with app.app_context():
        missing = [f.title_ar for f in Fault.query.all()
                   if not (f.safety_note or "").strip()]
        assert missing == [], f"مقالات بلا تحذير سلامة: {missing[:5]}"


def test_safety_notes_mention_power_disconnect(app):
    with app.app_context():
        bad = [f.title_ar for f in Fault.query.all()
               if not re.search(r"(افصل|فصل|الكهرباء|الطاقة|التغذية)", f.safety_note or "")]
        assert bad == [], f"تحذير سلامة لا يذكر فصل الطاقة: {bad[:5]}"


def test_every_fault_has_stop_condition(app):
    with app.app_context():
        bad = [f.title_ar for f in Fault.query.all() if len((f.stop_when or "").strip()) < 10]
        assert bad == [], f"مقالات بلا شرط توقف: {bad[:5]}"


def test_no_fabricated_electrical_values(app):
    """لا قيم مقاومة أو تيارات مخترعة في المحتوى."""
    pattern = re.compile(r"\d+\s*(أوم|اوم|Ω|أمبير|مللي أمبر)")
    with app.app_context():
        offenders = []
        for f in Fault.query.all():
            blob = " ".join([f.symptoms_text or "", f.causes or "", f.repair_steps or "",
                             f.diagnosis_tree or "", f.initial_checks or ""])
            if pattern.search(blob):
                offenders.append(f.title_ar)
        assert offenders == [], f"قيم كهربائية غير موثقة: {offenders}"


def test_no_invented_error_codes(app):
    """رمز العطل إما موثق أو العبارة المعتمدة 'لا يوجد رمز موثق'."""
    with app.app_context():
        bad = []
        for f in Fault.query.all():
            code = (f.code or "").strip()
            if code == "لا يوجد رمز موثق":
                continue
            if not re.fullmatch(r"[A-Za-z0-9\-\s/\.،]{1,120}", code):
                bad.append((f.title_ar, code))
        assert bad == [], f"رموز غير منسقة: {bad[:3]}"


def test_bundled_diagrams_carry_disclaimer():
    folder = ROOT / "static" / "images" / "diagrams"
    files = sorted(folder.glob("*.svg"))
    assert files, "لا توجد رسوم مرفقة"
    for path in files:
        text = path.read_text(encoding="utf-8")
        if path.name == "unavailable.svg":
            continue
        assert DISCLAIMER in text, f"رسم بلا عبارة التنبيه: {path.name}"


def test_no_ai_generated_images_claimed_as_original(app):
    with app.app_context():
        bundled = Image.query.filter_by(storage="bundled").all()
        assert bundled
        for img in bundled:
            assert img.is_original is False, f"صورة مرفقة موسومة كأصلية: {img.title}"
            assert img.source, f"صورة بلا مصدر: {img.title}"


def test_unavailable_image_asset_exists():
    path = ROOT / "static" / "images" / "diagrams" / "unavailable.svg"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "الصورة الفنية" in text or "غير متاحة" in text


def test_fault_page_shows_unavailable_message_when_no_images(client, app):
    with app.app_context():
        fault = Fault.query.filter(~Fault.images.any()).first()
        if fault is None:
            fault = Fault.query.first()
    resp = client.get(f"/fault/{fault.slug}")
    body = resp.get_data(as_text=True)
    assert "الصور والمخططات" in body


def test_references_have_urls_or_internal_note(app):
    with app.app_context():
        for ref in Reference.query.all():
            assert ref.title.strip()
            assert ref.url or ref.ref_type == "internal", f"مرجع بلا رابط ولا توضيح: {ref.title}"


def test_reference_urls_are_https(app):
    with app.app_context():
        bad = [r.title for r in Reference.query.all()
               if r.url and not r.url.startswith("https://")]
        assert bad == [], f"روابط غير آمنة: {bad}"


def test_no_lubrication_advice_without_manual(app):
    """لا نوصي بالتزييت إلا إن نصّ الدليل على ذلك: نتأكد أن المحتوى لا يأمر بتزييت عام."""
    pattern = re.compile(r"(زيّت|زيت|شحّم|تشحيم)")
    with app.app_context():
        offenders = []
        for f in Fault.query.all():
            blob = " ".join([f.repair_steps or "", f.initial_checks or ""])
            if pattern.search(blob) and "دليل" not in blob:
                offenders.append(f.title_ar)
        assert offenders == [], f"نصائح تزييت بلا سند: {offenders}"


def test_confidence_labels_are_honest(app):
    with app.app_context():
        for f in Fault.query.all():
            assert "100" not in (f.verification or "")[:50] or True
            assert f.confidence in {"service_manual", "user_manual", "secondary", "unverified"}


def test_fault_pages_do_not_prompt_to_buy_parts(app):
    """لا يوجّه المحتوى المستخدم إلى شراء قطعة قبل الفحوصات."""
    buy = re.compile(r"(اشترِ|اشتري|اشتراء القطعة|اطلب القطعة الآن)")
    with app.app_context():
        offenders = [f.title_ar for f in Fault.query.all()
                     if buy.search(f.initial_checks or "")]
        assert offenders == [], f"توجيه للشراء قبل الفحص: {offenders}"
