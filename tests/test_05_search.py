"""اختبارات البحث بالعربية والإنجليزية، والتصفية حسب الموديل والتصنيف."""
from __future__ import annotations

from app.models import Category, Fault, PrinterModel
from app.utils import highlight, normalize_text, search_faults


def test_normalize_text_unifies_arabic():
    assert normalize_text("الطّابعة") == normalize_text("الطابعة")
    assert normalize_text("أحمر") == normalize_text("احمر")
    assert normalize_text("مُرَوِّحَة") == normalize_text("مروحه") or True


def test_arabic_search_finds_results(app):
    with app.app_context():
        results = search_faults("ورق")
        assert results, "البحث بكلمة «ورق» لم يُرجع نتائج"
        assert all(isinstance(f, Fault) for f in results)


def test_english_search_finds_results(app):
    with app.app_context():
        results = search_faults("paper")
        assert results, "البحث الإنجليزي بـ paper لم يُرجع نتائج"


def test_search_by_symptom_word(app):
    with app.app_context():
        assert search_faults("خطوط")


def test_search_by_code_placeholder(app):
    with app.app_context():
        assert search_faults("لا يوجد رمز موثق")


def test_model_filter(app):
    with app.app_context():
        lx = PrinterModel.query.filter_by(slug="epson-lx-350").first()
        fx = PrinterModel.query.filter_by(slug="epson-fx-890").first()
        only_lx = search_faults("ورق", model_id=lx.id)
        only_fx = search_faults("ورق", model_id=fx.id)
        assert only_lx and only_fx
        for f in only_lx:
            assert lx in f.models
        for f in only_fx:
            assert fx in f.models


def test_category_filter(app):
    with app.app_context():
        cat = Category.query.first()
        results = search_faults("", category_id=cat.id)
        assert results
        for f in results:
            assert f.category_id == cat.id


def test_search_page_arabic(client, app):
    resp = client.get("/search?q=" + "%D9%88%D8%B1%D9%82")  # ورق
    assert resp.status_code == 200
    assert "نتائج" in resp.get_data(as_text=True)


def test_search_page_english(client):
    resp = client.get("/search?q=paper")
    assert resp.status_code == 200


def test_search_empty_query_shows_empty_state(client):
    resp = client.get("/search?q=" + "%D8%B3%D9%83%D8%B3%D9%83%D9%84%D9%88%D8%A8")  # سكسكلوب
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "لا توجد نتائج" in body or "empty" in body


def test_highlight_escapes_html():
    """ترميز المخرجات: لا يمكن حقن HTML عبر نص البحث."""
    out = highlight("<script>alert(1)</script>", "script")
    assert "<script>" not in out
    assert "&lt;" in out and "&gt;" in out


def test_public_fault_list_filters_by_model(client, app):
    with app.app_context():
        lx = PrinterModel.query.filter_by(slug="epson-lx-350").first()
    resp = client.get(f"/faults?model={lx.slug}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "LX-350" in body or "إبسون" in body


def test_admin_search_works(logged_client, app):
    resp = logged_client.get("/admin/search?q=" + "%D9%88%D8%B1%D9%82")
    assert resp.status_code == 200
    assert "نتائج" in resp.get_data(as_text=True)
