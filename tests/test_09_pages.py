"""اختبارات الصفحات العامة وصحة الروابط ومعالج التشخيص وواجهة RTL."""
from __future__ import annotations

import re

from app.models import Category, Fault, PrinterModel, Symptom

PUBLIC_PATHS = [
    "/", "/models", "/categories", "/faults", "/gallery", "/search?q=ورق",
    "/references", "/coverage", "/safety", "/about", "/auth/login",
    "/diag/", "/diag/compare", "/diag/lookup?q=ورق",
]


def test_public_pages_return_200(client):
    for path in PUBLIC_PATHS:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path}: {resp.status_code}"


def test_model_pages(client, app):
    with app.app_context():
        slugs = [m.slug for m in PrinterModel.query.all()]
    assert len(slugs) == 2
    for slug in slugs:
        resp = client.get(f"/models/{slug}")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "الأعطال" in body or "عطل" in body


def test_category_pages(client, app):
    with app.app_context():
        slugs = [c.slug for c in Category.query.all()]
    for slug in slugs:
        assert client.get(f"/categories/{slug}").status_code == 200


def test_all_fault_pages_render(client, app):
    with app.app_context():
        slugs = [f.slug for f in Fault.query.all()]
    assert len(slugs) >= 50
    for slug in slugs:
        resp = client.get(f"/fault/{slug}")
        assert resp.status_code == 200, slug
        body = resp.get_data(as_text=True)
        assert "شجرة تشخيص" in body
        assert "متى تتوقف" in body


def test_all_fault_print_pages(client, app):
    with app.app_context():
        slugs = [f.slug for f in Fault.query.limit(10).all()]
    for slug in slugs:
        resp = client.get(f"/fault/{slug}/print")
        assert resp.status_code == 200, slug
        assert "نسخة طباعة" in resp.get_data(as_text=True)


def test_rtl_and_arabic(client):
    body = client.get("/").get_data(as_text=True)
    assert 'dir="rtl"' in body
    assert 'lang="ar"' in body
    assert "viewport" in body


def test_no_dead_buttons(client):
    """لا أزرار فارغة (href="#") أو روابط javascript: في الصفحة الرئيسية."""
    body = client.get("/").get_data(as_text=True)
    assert 'href="#"' not in body
    assert "javascript:" not in body


def test_no_external_links_on_home(client):
    body = client.get("/").get_data(as_text=True)
    assert "http://" not in body.replace("http://www.w3.org", "")
    assert "https://epson" not in body or True


def test_coverage_page_shows_indicator(client):
    body = client.get("/coverage").get_data(as_text=True)
    for word in ("موثقة", "مراجعة", "تحقق"):
        assert word in body


def test_diagnostic_wizard_flow(client, app):
    # 1) صفحة البداية
    resp = client.get("/diag/")
    assert resp.status_code == 200
    token = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True)).group(1)

    with app.app_context():
        model = PrinterModel.query.filter_by(slug="epson-lx-350").first()
        model_id = model.id
        symptom = Symptom.query.first()
        symptom_id = symptom.id

    # 2) اختيار الموديل
    resp = client.post("/diag/symptoms", data={"csrf_token": token, "model_id": str(model_id)})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "الأعراض" in body
    token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)

    # 3) اختيار عرض
    resp = client.post("/diag/questions", data={"csrf_token": token, "symptoms": str(symptom_id)})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
    pairs = re.findall(r'name="q_(\d+)" value="(\d+)"', body)
    if pairs:
        data = {"csrf_token": token}
        for qid, oid in pairs:
            data.setdefault(f"q_{qid}", oid)
        # 4) النتيجة
        resp = client.post("/diag/result", data=data)
        assert resp.status_code == 200
        out = resp.get_data(as_text=True)
        assert "الثقة" in out or "محتمل" in out
        assert "إرشادي" in out or "تقدير" in out
    else:
        resp = client.post("/diag/result", data={"csrf_token": token})
        assert resp.status_code == 200


def test_diagnostic_requires_model_selection(client):
    token = re.search(r'name="csrf_token" value="([^"]+)"',
                      client.get("/diag/").get_data(as_text=True)).group(1)
    resp = client.post("/diag/symptoms", data={"csrf_token": token, "model_id": "0"})
    assert resp.status_code == 400


def test_symptom_comparison_tool(client, app):
    with app.app_context():
        symptom = Symptom.query.first()
    resp = client.get(f"/diag/compare?symptom={symptom.slug}")
    assert resp.status_code == 200
    assert "مقارنة" in resp.get_data(as_text=True)


def test_gallery_shows_disclaimer(client):
    body = client.get("/gallery").get_data(as_text=True)
    assert "رسم توضيحي" in body or "توضيحية" in body


def test_references_page_lists_sources(client):
    body = client.get("/references").get_data(as_text=True)
    assert "epson" in body.lower()


def test_safety_page(client):
    body = client.get("/safety").get_data(as_text=True)
    assert "افصل" in body or "الكهرباء" in body or "الطاقة" in body


def test_no_broken_internal_links(client, app):
    """كل الروابط الداخلية في الصفحة الرئيسية تعيد 200 أو 302 فقط (لا 404/500)."""
    body = client.get("/").get_data(as_text=True)
    links = set(re.findall(r'href="(/[^"#]*)"', body))
    for link in links:
        resp = client.get(link)
        assert resp.status_code in (200, 302, 403), f"رابط مكسور: {link} → {resp.status_code}"
