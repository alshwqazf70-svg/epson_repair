"""الصفحات العامة للموسوعة: الرئيسية، الموديلات، التصنيفات، الأعطال، المعرض، البحث."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, render_template, request

from ..models import (Category, Fault, Image, MaintenanceLog, PrinterModel, Reference,
                      SEVERITY, db)
from ..utils import highlight, search_faults

public_bp = Blueprint("public", __name__)


def coverage_stats() -> dict:
    """مؤشر تغطية الموسوعة: عدد المقالات الموثقة / قيد المراجعة / غير المتحققة."""
    published = Fault.query.filter_by(status="published").count()
    review = Fault.query.filter_by(status="review").count()
    draft = Fault.query.filter_by(status="draft").count()
    unverified = Fault.query.filter_by(confidence="unverified").count()
    verified = Fault.query.filter(Fault.confidence.in_(["service_manual", "user_manual"])).count()
    secondary = Fault.query.filter_by(confidence="secondary").count()
    empty_categories = Category.query.filter(
        ~Category.faults.any()).order_by(Category.sort_order).all()
    return {
        "published": published,
        "review": review,
        "draft": draft,
        "total": published + review + draft,
        "verified": verified,
        "secondary": secondary,
        "unverified": unverified,
        "empty_categories": empty_categories,
        "models": PrinterModel.query.filter_by(is_active=True).count(),
        "images": Image.query.count(),
        "logs": MaintenanceLog.query.count(),
    }


@public_bp.route("/")
def index():
    models = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    categories = Category.query.order_by(Category.sort_order).all()
    recent = (Fault.query.filter_by(status="published")
              .order_by(Fault.updated_at.desc()).limit(6).all())
    return render_template("index.html",
                           models=models,
                           categories=categories,
                           recent=recent,
                           stats=coverage_stats())


@public_bp.route("/models")
def models():
    items = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    return render_template("models.html", models=items)


@public_bp.route("/models/<slug>")
def model_detail(slug):
    model = PrinterModel.query.filter_by(slug=slug, is_active=True).first_or_404()
    faults = (Fault.query.filter(Fault.models.any(id=model.id), Fault.status == "published")
              .order_by(Fault.category_id, Fault.title_ar).all())
    by_category = {}
    for f in faults:
        by_category.setdefault(f.category_id, []).append(f)
    categories = Category.query.order_by(Category.sort_order).all()
    images = Image.query.filter_by(model_id=model.id).all()
    refs = Reference.query.filter_by(model_id=model.id).all()
    counts = {}
    for c in categories:
        counts[c.id] = len(by_category.get(c.id, []))
    return render_template("model_detail.html", model=model, faults=faults,
                           categories=categories, by_category=by_category, counts=counts,
                           images=images, refs=refs)


@public_bp.route("/categories")
def categories():
    items = Category.query.order_by(Category.sort_order).all()
    return render_template("categories.html", categories=items)


@public_bp.route("/categories/<slug>")
def category_detail(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    q = Fault.query.filter_by(category_id=category.id, status="published").order_by(Fault.title_ar)
    pagination = q.paginate(page=page, per_page=20, error_out=False)
    return render_template("category_detail.html", category=category, faults=pagination.items,
                           pagination=pagination)


@public_bp.route("/faults")
def faults():
    page = request.args.get("page", 1, type=int)
    model_slug = request.args.get("model", "")
    cat_slug = request.args.get("category", "")
    severity = request.args.get("severity", "")
    q = Fault.query.filter_by(status="published")
    model = None
    category = None
    if model_slug:
        model = PrinterModel.query.filter_by(slug=model_slug).first_or_404()
        q = q.filter(Fault.models.any(id=model.id))
    if cat_slug:
        category = Category.query.filter_by(slug=cat_slug).first_or_404()
        q = q.filter_by(category_id=category.id)
    if severity in SEVERITY:
        q = q.filter_by(severity=severity)
    pagination = q.order_by(Fault.title_ar).paginate(page=page, per_page=20, error_out=False)
    return render_template("fault_list.html", faults=pagination.items, pagination=pagination,
                           model=model, category=category, severity=severity,
                           severity_labels=SEVERITY)


@public_bp.route("/fault/<slug>")
def fault_detail(slug):
    fault = Fault.query.filter_by(slug=slug).first_or_404()
    fault.view_count = (fault.view_count or 0) + 1
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    images = fault.images.all()
    related = []
    if fault.category_id:
        related = (Fault.query.filter(Fault.category_id == fault.category_id,
                                      Fault.id != fault.id,
                                      Fault.status == "published").limit(5).all())
    return render_template("fault_detail.html", fault=fault, images=images, related=related)


@public_bp.route("/fault/<slug>/print")
def fault_print(slug):
    """نسخة للطباعة: بلا قوائم، مع ترويسة وتذييل مناسبين."""
    fault = Fault.query.filter_by(slug=slug).first_or_404()
    moment = date.today().strftime("%Y-%m-%d")
    return render_template("print/fault_print.html", fault=fault, images=fault.images.all(),
                           moment=moment)


@public_bp.route("/gallery")
def gallery():
    model_slug = request.args.get("model", "")
    models = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    model = None
    images = []
    if model_slug:
        model = PrinterModel.query.filter_by(slug=model_slug).first_or_404()
        images = Image.query.filter_by(model_id=model.id).all()
    else:
        images = Image.query.order_by(Image.model_id, Image.id).all()
    return render_template("gallery.html", models=models, model=model, images=images)


@public_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    model_id = request.args.get("model_id", 0, type=int)
    category_id = request.args.get("category_id", 0, type=int)
    results = []
    if q or model_id or category_id:
        results = search_faults(q, model_id or None, category_id or None)
    return render_template("search.html", q=q, results=results, model_id=model_id,
                           category_id=category_id, highlight=highlight)


@public_bp.route("/references")
def references():
    refs = Reference.query.order_by(Reference.ref_type, Reference.title).all()
    return render_template("references.html", refs=refs)


@public_bp.route("/coverage")
def coverage():
    """صفحة مؤشر التغطية والشفافية: ما هو موثق وما يحتاج تحققاً."""
    models = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    per_model = []
    for m in models:
        q = Fault.query.filter(Fault.models.any(id=m.id))
        per_model.append({
            "model": m,
            "published": q.filter_by(status="published").count(),
            "review": q.filter_by(status="review").count(),
            "verified": q.filter(Fault.confidence.in_(["service_manual", "user_manual"])).count(),
            "unverified": q.filter_by(confidence="unverified").count(),
        })
    unverified_list = (Fault.query.filter_by(confidence="unverified")
                       .order_by(Fault.title_ar).all())
    review_list = Fault.query.filter_by(status="review").order_by(Fault.title_ar).all()
    return render_template("coverage.html", stats=coverage_stats(), per_model=per_model,
                           unverified_list=unverified_list, review_list=review_list)


@public_bp.route("/safety")
def safety():
    return render_template("safety.html")


@public_bp.route("/about")
def about():
    return render_template("about.html")
