"""لوحة الإدارة الخاصة: لا يُسمح لأي زائر مجهول، والحماية على مستوى الخادم."""
from __future__ import annotations

import io
import json
from datetime import date, datetime
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   send_file, url_for)
from sqlalchemy import func

from .. import current_user, login_required
from ..forms import (CategoryForm, FaultForm, ImageForm, MaintenanceLogForm, ModelForm,
                     NoteForm, ReferenceForm)
from ..models import (ActivityLog, Category, Fault, Image, LogAttachment, MaintenanceLog,
                      Note, PrinterModel, Reference, SEVERITY, db)
from ..utils import (create_backup, log_activity, make_search_blob, make_thumbnail,
                     restore_backup, save_private_upload, unique_slug)

admin_bp = Blueprint("admin", __name__)


def user_name() -> str:
    u = current_user()
    return u.username if u else "system"


# ------------------------------------------------------------------ لوحة التحكم


@admin_bp.route("/")
@login_required
def dashboard():
    models = PrinterModel.query.order_by(PrinterModel.sort_order).all()
    stats = {
        "faults": Fault.query.count(),
        "published": Fault.query.filter_by(status="published").count(),
        "review": Fault.query.filter_by(status="review").count(),
        "draft": Fault.query.filter_by(status="draft").count(),
        "unverified": Fault.query.filter_by(confidence="unverified").count(),
        "models": PrinterModel.query.count(),
        "categories": Category.query.count(),
        "images": Image.query.count(),
        "logs": MaintenanceLog.query.count(),
        "notes": Note.query.count(),
        "references": Reference.query.count(),
    }
    per_model = []
    for m in models:
        q = Fault.query.filter(Fault.models.any(id=m.id))
        per_model.append({"model": m, "count": q.count()})
    per_category = (db.session.query(Category.name_ar, func.count(Fault.id))
                    .join(Fault, Fault.category_id == Category.id)
                    .group_by(Category.id).order_by(func.count(Fault.id).desc()).all())
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(12).all()
    return render_template("admin/dashboard.html", stats=stats, per_model=per_model,
                           per_category=per_category, recent_activity=recent_activity)


# ------------------------------------------------------------------ الأعطال


@admin_bp.route("/faults")
@login_required
def faults():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    qs = Fault.query
    if q:
        qs = qs.filter(Fault.search_blob.like(f"%{q}%"))
    if status:
        qs = qs.filter_by(status=status)
    pagination = qs.order_by(Fault.updated_at.desc()).paginate(page=page, per_page=20,
                                                               error_out=False)
    return render_template("admin/faults.html", pagination=pagination, q=q, status=status)


def _apply_fault_form(fault: Fault, form: FaultForm, extra_model_ids: list[int] | None = None):
    fault.title_ar = form.title_ar.data.strip()
    fault.title_en = (form.title_en.data or "").strip() or None
    fault.category_id = form.category_id.data
    fault.code = (form.code.data or "").strip() or "لا يوجد رمز موثق"
    fault.severity = form.severity.data
    fault.symptoms_text = form.symptoms_text.data or ""
    fault.causes = form.causes.data or ""
    fault.suspect_part = form.suspect_part.data or None
    fault.part_number = form.part_number.data or None
    fault.part_number_confidence = form.part_number_confidence.data
    fault.tools = form.tools.data or ""
    fault.initial_checks = form.initial_checks.data or ""
    fault.diagnosis_tree = form.diagnosis_tree.data or ""
    fault.repair_steps = form.repair_steps.data or ""
    fault.verification = form.verification.data or ""
    fault.final_test = form.final_test.data or ""
    fault.common_mistakes = form.common_mistakes.data or ""
    fault.stop_when = form.stop_when.data or ""
    fault.safety_note = form.safety_note.data or ""
    fault.source_name = form.source_name.data or None
    fault.source_url = (form.source_url.data or "").strip() or None
    fault.source_needed = form.source_needed.data or None
    fault.reviewed_at = form.reviewed_at.data
    fault.confidence = form.confidence.data
    fault.status = form.status.data
    ids = set(extra_model_ids or [])
    if form.model_ids.data:
        ids.add(int(form.model_ids.data))
    # ملاحظة: النموذج يدعم اختيار موديل واحد لكل مرة؛
    # الموديلات الإضافية تُحفظ عبر خانة اختيار متعدد في القالب (extra_models).
    extra = request.form.getlist("extra_models")
    ids.update(int(x) for x in extra if str(x).isdigit())
    if ids:
        fault.models = PrinterModel.query.filter(PrinterModel.id.in_(ids)).all()
    fault.search_blob = make_search_blob(
        fault.title_ar, fault.title_en, fault.code, fault.symptoms_text,
        fault.causes, fault.suspect_part, fault.part_number, fault.tools,
        fault.repair_steps, fault.title_ar.replace("ال", " "),
    )


@admin_bp.route("/faults/new", methods=["GET", "POST"])
@login_required
def fault_new():
    form = FaultForm()
    models = PrinterModel.query.order_by(PrinterModel.sort_order).all()
    if form.validate_on_submit():
        fault = Fault(slug=unique_slug(Fault, form.title_ar.data))
        _apply_fault_form(fault, form)
        db.session.add(fault)
        db.session.commit()
        log_activity("create", "fault", fault.id, fault.title_ar, user_name())
        flash(f"تم إنشاء صفحة العطل «{fault.title_ar}».", "success")
        return redirect(url_for("admin.fault_edit", fault_id=fault.id))
    return render_template("admin/fault_form.html", form=form, fault=None, models=models,
                           SEVERITY=SEVERITY)


@admin_bp.route("/faults/<int:fault_id>/edit", methods=["GET", "POST"])
@login_required
def fault_edit(fault_id):
    fault = db.session.get(Fault, fault_id) or abort(404)
    form = FaultForm(obj=fault)
    models = PrinterModel.query.order_by(PrinterModel.sort_order).all()
    if request.method == "GET":
        form.model_ids.data = fault.models[0].id if fault.models else 0
    if form.validate_on_submit():
        _apply_fault_form(fault, form)
        if not fault.slug:
            fault.slug = unique_slug(Fault, fault.title_ar, fault.id)
        db.session.commit()
        log_activity("update", "fault", fault.id, fault.title_ar, user_name())
        flash("تم حفظ التعديلات.", "success")
        return redirect(url_for("admin.fault_edit", fault_id=fault.id))
    return render_template("admin/fault_form.html", form=form, fault=fault, models=models,
                           SEVERITY=SEVERITY)


@admin_bp.route("/faults/<int:fault_id>/delete", methods=["POST"])
@login_required
def fault_delete(fault_id):
    fault = db.session.get(Fault, fault_id) or abort(404)
    title = fault.title_ar
    db.session.delete(fault)
    db.session.commit()
    log_activity("delete", "fault", fault_id, title, user_name())
    flash(f"تم حذف العطل «{title}».", "warning")
    return redirect(url_for("admin.faults"))


# ------------------------------------------------------------------ التصنيفات


@admin_bp.route("/categories")
@login_required
def categories():
    return render_template("admin/categories.html",
                           categories=Category.query.order_by(Category.sort_order).all())


@admin_bp.route("/categories/new", methods=["GET", "POST"])
@login_required
def category_new():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(slug=unique_slug(Category, form.name_ar.data),
                       name_ar=form.name_ar.data.strip(),
                       name_en=(form.name_en.data or "").strip() or None,
                       description=form.description.data,
                       icon=(form.icon.data or "").strip() or None,
                       sort_order=form.sort_order.data or 10)
        db.session.add(cat)
        db.session.commit()
        log_activity("create", "category", cat.id, cat.name_ar, user_name())
        flash("تمت إضافة التصنيف.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", form=form, category=None)


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@login_required
def category_edit(cat_id):
    cat = db.session.get(Category, cat_id) or abort(404)
    form = CategoryForm(obj=cat)
    if form.validate_on_submit():
        cat.name_ar = form.name_ar.data.strip()
        cat.name_en = (form.name_en.data or "").strip() or None
        cat.description = form.description.data
        cat.icon = (form.icon.data or "").strip() or None
        cat.sort_order = form.sort_order.data or 10
        db.session.commit()
        log_activity("update", "category", cat.id, cat.name_ar, user_name())
        flash("تم حفظ التصنيف.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", form=form, category=cat)


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
def category_delete(cat_id):
    cat = db.session.get(Category, cat_id) or abort(404)
    if cat.faults.count():
        flash("لا يمكن حذف تصنيف يحتوي مقالات. انقل المقالات أولاً.", "danger")
        return redirect(url_for("admin.categories"))
    db.session.delete(cat)
    db.session.commit()
    log_activity("delete", "category", cat_id, cat.name_ar, user_name())
    flash("تم حذف التصنيف.", "warning")
    return redirect(url_for("admin.categories"))


# ------------------------------------------------------------------ الموديلات


@admin_bp.route("/models")
@login_required
def models():
    return render_template("admin/models.html",
                           models=PrinterModel.query.order_by(PrinterModel.sort_order).all())


@admin_bp.route("/models/new", methods=["GET", "POST"])
@login_required
def model_new():
    form = ModelForm()
    if form.validate_on_submit():
        m = PrinterModel(slug=unique_slug(PrinterModel, form.name_en.data or form.name_ar.data),
                         name_ar=form.name_ar.data.strip(),
                         name_en=form.name_en.data.strip(),
                         printer_class=form.printer_class.data,
                         pins=form.pins.data, columns=form.columns.data,
                         interfaces=form.interfaces.data,
                         ribbon_part=form.ribbon_part.data,
                         ribbon_part_confidence=form.ribbon_part_confidence.data,
                         mtbf=form.mtbf.data, print_head_life=form.print_head_life.data,
                         memory=form.memory.data, paper_paths=form.paper_paths.data,
                         summary=form.summary.data, specs_note=form.specs_note.data,
                         sort_order=form.sort_order.data or 10,
                         is_active=bool(form.is_active.data))
        db.session.add(m)
        db.session.commit()
        log_activity("create", "model", m.id, m.name_ar, user_name())
        flash("تمت إضافة الموديل.", "success")
        return redirect(url_for("admin.models"))
    return render_template("admin/model_form.html", form=form, model=None)


@admin_bp.route("/models/<int:model_id>/edit", methods=["GET", "POST"])
@login_required
def model_edit(model_id):
    m = db.session.get(PrinterModel, model_id) or abort(404)
    form = ModelForm(obj=m)
    if form.validate_on_submit():
        m.name_ar = form.name_ar.data.strip()
        m.name_en = form.name_en.data.strip()
        m.printer_class = form.printer_class.data
        m.pins = form.pins.data
        m.columns = form.columns.data
        m.interfaces = form.interfaces.data
        m.ribbon_part = form.ribbon_part.data
        m.ribbon_part_confidence = form.ribbon_part_confidence.data
        m.mtbf = form.mtbf.data
        m.print_head_life = form.print_head_life.data
        m.memory = form.memory.data
        m.paper_paths = form.paper_paths.data
        m.summary = form.summary.data
        m.specs_note = form.specs_note.data
        m.sort_order = form.sort_order.data or 10
        m.is_active = bool(form.is_active.data)
        db.session.commit()
        log_activity("update", "model", m.id, m.name_ar, user_name())
        flash("تم حفظ الموديل.", "success")
        return redirect(url_for("admin.models"))
    return render_template("admin/model_form.html", form=form, model=m)


# ------------------------------------------------------------------ الصور


@admin_bp.route("/images")
@login_required
def images():
    return render_template("admin/images.html",
                           images=Image.query.order_by(Image.id.desc()).all())


@admin_bp.route("/images/new", methods=["GET", "POST"])
@login_required
def image_new():
    form = ImageForm()
    if form.validate_on_submit():
        if not form.file.data:
            flash("يجب اختيار ملف صورة.", "danger")
        else:
            filename = save_private_upload(form.file.data, subdir="images")
            upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
            rel = f"images/{filename.split('/')[-1]}"
            thumb = make_thumbnail(upload_root / "images" / filename.split("/")[-1])
            img = Image(title=form.title.data.strip(),
                        description=form.description.data,
                        model_id=form.model_id.data or None,
                        fault_id=form.fault_id.data or None,
                        storage="uploaded", filename=rel, thumb_filename=thumb,
                        image_type=form.image_type.data,
                        is_original=bool(form.is_original.data),
                        source=(form.source.data or "").strip() or "رفع خاص بالمالك",
                        license_note=form.license_note.data, step_hint=form.step_hint.data)
            db.session.add(img)
            db.session.commit()
            log_activity("create", "image", img.id, img.title, user_name())
            flash("تم رفع الصورة وربطها.", "success")
            return redirect(url_for("admin.images"))
    return render_template("admin/image_form.html", form=form)


@admin_bp.route("/images/<int:image_id>/delete", methods=["POST"])
@login_required
def image_delete(image_id):
    img = db.session.get(Image, image_id) or abort(404)
    if img.storage == "uploaded":
        try:
            from ..utils import resolve_private_path
            p = resolve_private_path(img.filename)
            p.unlink(missing_ok=True)
        except Exception:
            pass
    db.session.delete(img)
    db.session.commit()
    log_activity("delete", "image", image_id, img.title, user_name())
    flash("تم حذف الصورة.", "warning")
    return redirect(url_for("admin.images"))


# ------------------------------------------------------------------ المراجع


@admin_bp.route("/references")
@login_required
def references():
    return render_template("admin/references.html",
                           refs=Reference.query.order_by(Reference.id.desc()).all())


@admin_bp.route("/references/new", methods=["GET", "POST"])
@login_required
def reference_new():
    form = ReferenceForm()
    if form.validate_on_submit():
        ref = Reference(title=form.title.data.strip(), url=(form.url.data or "").strip() or None,
                        publisher=form.publisher.data, ref_type=form.ref_type.data,
                        model_id=form.model_id.data or None, notes=form.notes.data,
                        verified=bool(form.verified.data))
        db.session.add(ref)
        db.session.commit()
        log_activity("create", "reference", ref.id, ref.title, user_name())
        flash("تمت إضافة المرجع.", "success")
        return redirect(url_for("admin.references"))
    return render_template("admin/reference_form.html", form=form, ref=None)


@admin_bp.route("/references/<int:ref_id>/edit", methods=["GET", "POST"])
@login_required
def reference_edit(ref_id):
    ref = db.session.get(Reference, ref_id) or abort(404)
    form = ReferenceForm(obj=ref)
    if form.validate_on_submit():
        ref.title = form.title.data.strip()
        ref.url = (form.url.data or "").strip() or None
        ref.publisher = form.publisher.data
        ref.ref_type = form.ref_type.data
        ref.model_id = form.model_id.data or None
        ref.notes = form.notes.data
        ref.verified = bool(form.verified.data)
        db.session.commit()
        log_activity("update", "reference", ref.id, ref.title, user_name())
        flash("تم حفظ المرجع.", "success")
        return redirect(url_for("admin.references"))
    return render_template("admin/reference_form.html", form=form, ref=ref)


@admin_bp.route("/references/<int:ref_id>/delete", methods=["POST"])
@login_required
def reference_delete(ref_id):
    ref = db.session.get(Reference, ref_id) or abort(404)
    db.session.delete(ref)
    db.session.commit()
    log_activity("delete", "reference", ref_id, ref.title, user_name())
    flash("تم حذف المرجع.", "warning")
    return redirect(url_for("admin.references"))


# ------------------------------------------------------------------ سجل الصيانة


@admin_bp.route("/logs")
@login_required
def logs():
    q = request.args.get("q", "").strip()
    model_id = request.args.get("model_id", 0, type=int)
    result = request.args.get("result", "")
    page = request.args.get("page", 1, type=int)
    qs = MaintenanceLog.query
    if q:
        qs = qs.filter(db.or_(MaintenanceLog.title.like(f"%{q}%"),
                              MaintenanceLog.symptoms.like(f"%{q}%"),
                              MaintenanceLog.repair_done.like(f"%{q}%")))
    if model_id:
        qs = qs.filter_by(model_id=model_id)
    if result:
        qs = qs.filter_by(result=result)
    pagination = qs.order_by(MaintenanceLog.log_date.desc()).paginate(page=page, per_page=20,
                                                                      error_out=False)
    models = PrinterModel.query.order_by(PrinterModel.sort_order).all()
    return render_template("admin/logs.html", pagination=pagination, models=models, q=q,
                           model_id=model_id, result=result)


@admin_bp.route("/logs/new", methods=["GET", "POST"])
@login_required
def log_new():
    form = MaintenanceLogForm()
    if request.method == "GET":
        form.log_date.data = date.today()
        # تعبئة مسبقة عند القدوم من صفحة عطل (رابط «تسجيل صيانة لهذا العطل»)
        fid = request.args.get("fault_id", type=int)
        if fid:
            form.fault_id.data = fid
            linked = db.session.get(Fault, fid)
            if linked and linked.models:
                form.model_id.data = linked.models[0].id
    if form.validate_on_submit():
        entry = MaintenanceLog(model_id=form.model_id.data or None,
                               fault_id=form.fault_id.data or None,
                               log_date=form.log_date.data,
                               title=form.title.data.strip(),
                               symptoms=form.symptoms.data,
                               initial_diagnosis=form.initial_diagnosis.data,
                               tests_done=form.tests_done.data,
                               parts_cleaned=form.parts_cleaned.data,
                               parts_replaced=form.parts_replaced.data,
                               repair_done=form.repair_done.data,
                               result=form.result.data, notes=form.notes.data)
        db.session.add(entry)
        db.session.commit()
        for kind in ("before", "after"):
            for file in request.files.getlist(f"photos_{kind}"):
                if file and file.filename:
                    filename = save_private_upload(file, subdir="logs")
                    rel = f"logs/{filename.split('/')[-1]}"
                    entry.attachments.append(
                        LogAttachment(filename=rel, kind=kind,
                                      caption="قبل الإصلاح" if kind == "before" else "بعد الإصلاح"))
        db.session.commit()
        log_activity("create", "log", entry.id, entry.title, user_name())
        flash("تم حفظ سجل الصيانة.", "success")
        return redirect(url_for("admin.log_edit", log_id=entry.id))
    return render_template("admin/log_form.html", form=form, entry=None)


@admin_bp.route("/logs/<int:log_id>")
@login_required
def log_view(log_id):
    entry = db.session.get(MaintenanceLog, log_id) or abort(404)
    return render_template("admin/log_view.html", entry=entry)


@admin_bp.route("/logs/<int:log_id>/print")
@login_required
def log_print(log_id):
    entry = db.session.get(MaintenanceLog, log_id) or abort(404)
    return render_template("print/log_print.html", entry=entry)


@admin_bp.route("/logs/<int:log_id>/edit", methods=["GET", "POST"])
@login_required
def log_edit(log_id):
    entry = db.session.get(MaintenanceLog, log_id) or abort(404)
    form = MaintenanceLogForm(obj=entry)
    if form.validate_on_submit():
        entry.model_id = form.model_id.data or None
        entry.fault_id = form.fault_id.data or None
        entry.log_date = form.log_date.data
        entry.title = form.title.data.strip()
        entry.symptoms = form.symptoms.data
        entry.initial_diagnosis = form.initial_diagnosis.data
        entry.tests_done = form.tests_done.data
        entry.parts_cleaned = form.parts_cleaned.data
        entry.parts_replaced = form.parts_replaced.data
        entry.repair_done = form.repair_done.data
        entry.result = form.result.data
        entry.notes = form.notes.data
        db.session.commit()
        log_activity("update", "log", entry.id, entry.title, user_name())
        flash("تم حفظ سجل الصيانة.", "success")
        return redirect(url_for("admin.log_edit", log_id=entry.id))
    return render_template("admin/log_form.html", form=form, entry=entry)


@admin_bp.route("/logs/<int:log_id>/delete", methods=["POST"])
@login_required
def log_delete(log_id):
    entry = db.session.get(MaintenanceLog, log_id) or abort(404)
    db.session.delete(entry)
    db.session.commit()
    log_activity("delete", "log", log_id, entry.title, user_name())
    flash("تم حذف السجل.", "warning")
    return redirect(url_for("admin.logs"))


# ------------------------------------------------------------------ الملاحظات


@admin_bp.route("/notes")
@login_required
def notes():
    return render_template("admin/notes.html",
                           notes=Note.query.order_by(Note.updated_at.desc()).all())


@admin_bp.route("/notes/new", methods=["GET", "POST"])
@login_required
def note_new():
    form = NoteForm()
    if form.validate_on_submit():
        note = Note(title=form.title.data.strip(), body=form.body.data,
                    model_id=form.model_id.data or None)
        db.session.add(note)
        db.session.commit()
        log_activity("create", "note", note.id, note.title, user_name())
        flash("تمت إضافة الملاحظة.", "success")
        return redirect(url_for("admin.notes"))
    return render_template("admin/note_form.html", form=form, note=None)


@admin_bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def note_edit(note_id):
    note = db.session.get(Note, note_id) or abort(404)
    form = NoteForm(obj=note)
    if form.validate_on_submit():
        note.title = form.title.data.strip()
        note.body = form.body.data
        note.model_id = form.model_id.data or None
        db.session.commit()
        log_activity("update", "note", note.id, note.title, user_name())
        flash("تم حفظ الملاحظة.", "success")
        return redirect(url_for("admin.notes"))
    return render_template("admin/note_form.html", form=form, note=note)


@admin_bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def note_delete(note_id):
    note = db.session.get(Note, note_id) or abort(404)
    db.session.delete(note)
    db.session.commit()
    log_activity("delete", "note", note_id, note.title, user_name())
    flash("تم حذف الملاحظة.", "warning")
    return redirect(url_for("admin.notes"))


# ------------------------------------------------------------------ النسخ الاحتياطي والتصدير


@admin_bp.route("/backup/create", methods=["POST"])
@login_required
def backup_create():
    try:
        path = create_backup(current_app)
        log_activity("backup", "system", None, path.name, user_name())
        flash(f"تم إنشاء النسخة الاحتياطية: {path.name}", "success")
        return redirect(url_for("admin.backups"))
    except Exception as exc:
        current_app.logger.exception("فشل النسخ الاحتياطي")
        flash("تعذّر إنشاء النسخة الاحتياطية. تحقق من صلاحيات الكتابة.", "danger")
        return redirect(url_for("admin.backups"))


@admin_bp.route("/backups")
@login_required
def backups():
    folder = Path(current_app.config["BACKUP_FOLDER"])
    files = []
    if folder.is_dir():
        files = sorted(folder.glob("backup-*.zip"), key=lambda p: p.stat().st_mtime,
                       reverse=True)
    return render_template("admin/backups.html", files=files)


@admin_bp.route("/backups/<name>/download")
@login_required
def backup_download(name):
    folder = Path(current_app.config["BACKUP_FOLDER"]).resolve()
    if name != Path(name).name or not name.startswith("backup-") or not name.endswith(".zip"):
        abort(404)
    path = (folder / name).resolve()
    if folder != path.parent:  # منع Path Traversal
        abort(404)
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=name)


@admin_bp.route("/backups/restore", methods=["POST"])
@login_required
def backup_restore():
    file = request.files.get("archive")
    if not file or not file.filename:
        flash("اختر ملف نسخة احتياطية أولاً.", "danger")
        return redirect(url_for("admin.backups"))
    from werkzeug.utils import secure_filename
    import tempfile
    name = secure_filename(file.filename)
    tmp_dir = Path(tempfile.mkdtemp(prefix="restore-"))
    tmp = tmp_dir / name
    file.save(tmp)
    try:
        info = restore_backup(current_app, tmp)
        log_activity("restore", "system", None, name, user_name())
        flash(f"تمت الاستعادة: قاعدة بيانات={info['db']}، ملفات={info['files']}.", "success")
    except Exception as exc:
        current_app.logger.exception("فشل الاستعادة")
        flash("تعذّرت الاستعادة. تأكد أن الملف نسخة احتياطية صالحة.", "danger")
    finally:
        try:
            tmp.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except Exception:
            pass
    return redirect(url_for("admin.backups"))


@admin_bp.route("/export")
@login_required
def export():
    """تصدير شامل بصيغة JSON (قابل للاستيراد اليدوي أو الأرشفة)."""
    fmt = request.args.get("fmt", "json")
    data = {
        "exported_at": datetime.utcnow().isoformat(timespec="seconds"),
        "app": current_app.config["APP_NAME_EN"],
        "models": [{k: getattr(m, k) for k in
                    ("slug", "name_ar", "name_en", "printer_class", "pins", "columns",
                     "interfaces", "ribbon_part", "mtbf", "print_head_life", "memory",
                     "paper_paths", "summary", "specs_note")} for m in
                   PrinterModel.query.all()],
        "categories": [{"slug": c.slug, "name_ar": c.name_ar, "name_en": c.name_en,
                        "description": c.description} for c in Category.query.all()],
        "faults": [],
        "logs": [],
        "notes": [],
    }
    for f in Fault.query.all():
        data["faults"].append({
            "slug": f.slug, "title_ar": f.title_ar, "title_en": f.title_en,
            "category": f.category.slug if f.category else None,
            "models": [m.slug for m in f.models],
            "code": f.code, "severity": f.severity, "symptoms_text": f.symptoms_text,
            "causes": f.causes, "suspect_part": f.suspect_part, "part_number": f.part_number,
            "tools": f.tools, "initial_checks": f.initial_checks,
            "diagnosis_tree": f.diagnosis_tree, "repair_steps": f.repair_steps,
            "verification": f.verification, "final_test": f.final_test,
            "common_mistakes": f.common_mistakes, "stop_when": f.stop_when,
            "source_name": f.source_name, "source_url": f.source_url,
            "confidence": f.confidence, "status": f.status,
            "reviewed_at": f.reviewed_at.isoformat() if f.reviewed_at else None,
        })
    for l in MaintenanceLog.query.all():
        data["logs"].append({
            "title": l.title, "date": l.log_date.isoformat() if l.log_date else None,
            "model": l.model.slug if l.model else None,
            "fault": l.fault.slug if l.fault else None,
            "symptoms": l.symptoms, "initial_diagnosis": l.initial_diagnosis,
            "tests_done": l.tests_done, "parts_cleaned": l.parts_cleaned,
            "parts_replaced": l.parts_replaced, "repair_done": l.repair_done,
            "result": l.result, "notes": l.notes,
        })
    for n in Note.query.all():
        data["notes"].append({"title": n.title, "body": n.body,
                              "model": n.model.slug if n.model else None})
    log_activity("export", "system", None, fmt, user_name())
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return send_file(io.BytesIO(payload.encode("utf-8")),
                     mimetype="application/json", as_attachment=True,
                     download_name=f"epson_repair_master_export_{date.today().isoformat()}.json")


@admin_bp.route("/activity")
@login_required
def activity():
    page = request.args.get("page", 1, type=int)
    pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False)
    return render_template("admin/activity.html", pagination=pagination)


@admin_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        results = Fault.query.filter(Fault.search_blob.like(f"%{q}%")).limit(50).all()
    return render_template("admin/search.html", q=q, results=results)
