"""البحث والتشخيص: معالج تشخيص محلي بقواعد صريحة + أداة مقارنة الأعراض."""
from __future__ import annotations

from flask import Blueprint, abort, render_template, request, session

from ..models import (Category, Fault, PrinterModel, Question, QuestionOption, Symptom,
                      db, fault_symptoms)
from ..utils import parse_weight_map, search_faults

diag_bp = Blueprint("diag", __name__)

MAX_CONFIDENCE = 92  # سقف درجة الثقة: التقدير إرشادي وليس ضماناً


def _rules_for(model_id: int) -> list[Symptom]:
    return (Symptom.query.order_by(Symptom.category_id, Symptom.name_ar).all())


@diag_bp.route("/")
def start():
    models = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    if not models:
        abort(404)
    return render_template("diag/start.html", models=models)


@diag_bp.route("/symptoms", methods=["GET", "POST"])
def symptoms():
    """الخطوة 2: اختيار الموديل ثم تحديد الأعراض."""
    models = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    model_id = request.values.get("model_id", type=int)
    if request.method == "POST":
        model_id = request.form.get("model_id", type=int)
        if not model_id:
            abort(400, "يجب اختيار الموديل")
        session["diag_model"] = model_id
        session["diag_symptoms"] = []
        session["diag_answers"] = {}
    model_id = model_id or session.get("diag_model")
    if not model_id:
        return render_template("diag/start.html", models=models)
    model = db.session.get(PrinterModel, model_id)
    if model is None:
        abort(404)
    symptoms_list = _rules_for(model_id)
    grouped = {}
    for s in symptoms_list:
        grouped.setdefault(s.category_id, []).append(s)
    categories = {c.id: c for c in Category.query.all()}
    return render_template("diag/symptoms.html", model=model, grouped=grouped,
                           categories=categories,
                           selected=[int(x) for x in session.get("diag_symptoms", [])])


@diag_bp.route("/questions", methods=["POST"])
def questions():
    """الخطوة 3: أسئلة متفرّعة حسب الأعراض المختارة."""
    model_id = session.get("diag_model")
    if not model_id:
        return redirect_start()
    selected = [int(x) for x in request.form.getlist("symptoms") if x.isdigit()]
    session["diag_symptoms"] = selected
    if not selected:
        return render_template("diag/symptoms.html",
                               model=db.session.get(PrinterModel, model_id),
                               grouped={}, categories={}, selected=[],
                               error="اختر عرضاً واحداً على الأقل للمتابعة.")
    qs = (Question.query.filter(Question.trigger_symptom_id.in_(selected))
          .filter(db.or_(Question.model_id.is_(None), Question.model_id == model_id))
          .order_by(Question.sort_order).all())
    # أسئلة عامة (بدون عرض محفّز) تُعرض دائماً
    general = (Question.query.filter(Question.trigger_symptom_id.is_(None))
               .filter(db.or_(Question.model_id.is_(None), Question.model_id == model_id))
               .order_by(Question.sort_order).all())
    all_questions = list(dict.fromkeys(qs + general))
    return render_template("diag/questions.html",
                           model=db.session.get(PrinterModel, model_id),
                           questions=all_questions)


def redirect_start():
    from flask import redirect, url_for
    return redirect(url_for("diag.start"))


@diag_bp.route("/result", methods=["POST"])
def result():
    """الخطوة 4: حساب النتائج محلياً بقواعد صريحة."""
    model_id = session.get("diag_model")
    symptom_ids = session.get("diag_symptoms", [])
    if not model_id or not symptom_ids:
        return redirect_start()
    model = db.session.get(PrinterModel, model_id)
    answers = {}
    for key, value in request.form.items():
        if key.startswith("q_"):
            try:
                answers[int(key[2:])] = int(value)
            except (TypeError, ValueError):
                continue
    session["diag_answers"] = answers

    # 1) رصد الأوزان الأساسية من الأعراض
    scores: dict[int, float] = {}
    rows = db.session.execute(
        db.select(fault_symptoms.c.fault_id, fault_symptoms.c.symptom_id,
                  fault_symptoms.c.weight)
        .where(fault_symptoms.c.symptom_id.in_(symptom_ids))
    ).all()
    for fault_id, symptom_id, weight in rows:
        scores[fault_id] = scores.get(fault_id, 0.0) + float(weight or 3)

    # 2) تعديل الأوزان بناءً على إجابات الأسئلة
    evidence = []
    for qid, opt_id in answers.items():
        opt = db.session.get(QuestionOption, opt_id)
        if not opt or opt.question_id != qid:
            continue
        question = db.session.get(Question, qid)
        weights = parse_weight_map(opt.weight_map)
        evidence.append({"question": question.text_ar if question else "",
                         "answer": opt.label_ar})
        for slug, delta in weights.items():
            fault = Fault.query.filter_by(slug=slug).first()
            if fault:
                scores[fault.id] = scores.get(fault.id, 0.0) + float(delta)

    if not scores:
        matches = []
        confidence = 0
    else:
        # 3) تصفية حسب الموديل: الأعطال غير المنطبقة تُستبعد تماماً
        model_fault_ids = {f.id for f in
                           Fault.query.filter(Fault.models.any(id=model_id)).all()}
        filtered = {fid: sc for fid, sc in scores.items() if fid in model_fault_ids}
        if not filtered:
            filtered = {fid: sc * 0.35 for fid, sc in scores.items()}  # احتمال عام ضعيف
        ranked = sorted(filtered.items(), key=lambda kv: -kv[1])
        top_score = ranked[0][1]
        ids = [i for i, _ in ranked[:8]]
        faults_by_id = {f.id: f for f in Fault.query.filter(Fault.id.in_(ids)).all()}
        matches = []
        for fid, score in ranked[:8]:
            fault = faults_by_id.get(fid)
            if not fault:
                continue
            raw = (score / top_score) if top_score else 0
            pct = int(min(MAX_CONFIDENCE, max(12, round(raw * 88))))
            matches.append({"fault": fault, "score": round(score, 1), "confidence": pct})
        confidence = matches[0]["confidence"] if matches else 0

    ambiguous = len(matches) > 1 and matches and matches[0]["score"] - matches[1]["score"] < 1.0
    return render_template("diag/result.html", model=model, matches=matches,
                           confidence=confidence, evidence=evidence,
                           ambiguous=ambiguous,
                           symptoms=Symptom.query.filter(Symptom.id.in_(symptom_ids)).all(),
                           max_confidence=MAX_CONFIDENCE)


@diag_bp.route("/compare")
def compare():
    """أداة مقارنة الأعراض: الأعطال المتشابهة والاختبارات التي تميّز بينها."""
    symptom_slug = request.args.get("symptom", "")
    model_id = request.args.get("model_id", type=int)
    symptoms = Symptom.query.order_by(Symptom.name_ar).all()
    chosen = Symptom.query.filter_by(slug=symptom_slug).first() if symptom_slug else None
    rows = []
    if chosen:
        faults = (Fault.query.filter(Fault.symptom_links.any(id=chosen.id),
                                     Fault.status == "published")
                  .order_by(Fault.title_ar).all())
        if model_id:
            faults = [f for f in faults if any(m.id == model_id for m in f.models)]
        for f in faults:
            rows.append({
                "fault": f,
                "models": f.models,
                "differentiator": (f.initial_checks or "")[:400],
            })
    models = PrinterModel.query.filter_by(is_active=True).order_by(PrinterModel.sort_order).all()
    return render_template("diag/compare.html", symptoms=symptoms, chosen=chosen,
                           rows=rows, models=models, model_id=model_id or 0)


@diag_bp.route("/lookup")
def lookup():
    """بحث سريع بالأعراض أو القطعة أو الرمز (يدعم العربية والإنجليزية)."""
    q = request.args.get("q", "").strip()
    model_id = request.args.get("model_id", 0, type=int)
    results = search_faults(q, model_id or None) if q else []
    return render_template("diag/lookup.html", q=q, results=results, model_id=model_id)
