# -*- coding: utf-8 -*-
"""تحميل المحتوى التأسيسي إلى قاعدة البيانات."""
from __future__ import annotations

from datetime import date

from .models import (Category, Fault, Image, PrinterModel, Question, QuestionOption, Reference,
                     Symptom, db, fault_symptoms)
from .seed_data import BUNDLED_IMAGES, CATEGORIES, MODELS, QUESTIONS, REFERENCES, SYMPTOMS
from .seed_faults_a import PAPER, POWER, PRINT_QUALITY
from .seed_faults_b import COMPOUND, CONNECTIVITY, ELECTRICAL, MECHANICS, PREVENTIVE, SETTINGS
from .utils import make_search_blob

BASE_FAULTS = (POWER + PRINT_QUALITY + PAPER + MECHANICS + CONNECTIVITY
               + SETTINGS + PREVENTIVE + ELECTRICAL + COMPOUND)

# أرقام شرائط الحبر الموثقة لكل طراز (من صفحات إبسون الرسمية)
RIBBON_PART_BY_MODEL = {"epson-lx-350": "C13S015637", "epson-fx-890": "C13S015329"}
MODEL_SHORT = {"epson-lx-350": "lx350", "epson-fx-890": "fx890"}


def _per_model_part_number(raw: str | None, model_slug: str) -> str | None:
    """إن كان رقم القطعة يذكر الطرازين، نُبقي الرقم الصحيح لهذا الطراز فقط."""
    if not raw:
        return None
    own = RIBBON_PART_BY_MODEL.get(model_slug)
    if own and own in raw and len(RIBBON_PART_BY_MODEL) > 1:
        others = [v for k, v in RIBBON_PART_BY_MODEL.items() if k != model_slug]
        if any(o in raw for o in others):
            return own
    return raw


def expand_per_model(faults: list[dict]) -> list[dict]:
    """كل مقالة تُنسب إلى موديل واحد فقط.

    المقالات العامة (التي تنطبق على الطرازين) تُنسخ إلى مقالتين مستقلتين،
    لكل منهما slug ومحتوى رقم قطعة خاصان بالموديل، حتى لا يظهر رقم قطعة أو
    إجراء خاص بموديل على صفحة موديل آخر.
    """
    expanded: list[dict] = []
    for data in faults:
        models = data.get("models", [])
        if len(models) <= 1:
            expanded.append(data)
            continue
        for model_slug in models:
            short = MODEL_SHORT.get(model_slug, model_slug.replace("epson-", ""))
            item = dict(data)
            item["slug"] = f"{data['slug']}-{short}"
            item["models"] = [model_slug]
            item["model_slug"] = model_slug
            item["part_number"] = _per_model_part_number(data.get("part_number"), model_slug)
            expanded.append(item)
    return expanded


ALL_FAULTS = expand_per_model(BASE_FAULTS)


def seed_all(force: bool = False) -> dict:
    """ينشئ الجداول ويحمّل المحتوى التأسيسي.

    force=True يعيد تحميل المقالات المفقودة فقط (لا يحذف بيانات المالك).
    """
    db.create_all()
    stats = {"categories": 0, "models": 0, "faults": 0, "symptoms": 0,
             "questions": 0, "images": 0, "references": 0}

    # ---------------------------------------------------------- التصنيفات
    cat_by_slug = {}
    for data in CATEGORIES:
        cat = Category.query.filter_by(slug=data["slug"]).first()
        if cat is None:
            cat = Category(slug=data["slug"])
            db.session.add(cat)
            stats["categories"] += 1
        cat.name_ar = data["name_ar"]
        cat.name_en = data["name_en"]
        cat.description = data["description"]
        cat.icon = data["icon"]
        cat.sort_order = data["sort_order"]
        cat_by_slug[data["slug"]] = cat
    db.session.flush()

    # ---------------------------------------------------------- الموديلات
    model_by_slug = {}
    for data in MODELS:
        m = PrinterModel.query.filter_by(slug=data["slug"]).first()
        if m is None:
            m = PrinterModel(slug=data["slug"])
            db.session.add(m)
            stats["models"] += 1
        for key in ("name_ar", "name_en", "brand", "printer_class", "pins", "columns",
                    "interfaces", "ribbon_part", "ribbon_part_confidence", "mtbf",
                    "print_head_life", "memory", "paper_paths", "summary", "specs_note",
                    "sort_order"):
            setattr(m, key, data.get(key))
        m.is_active = True
        model_by_slug[data["slug"]] = m
    db.session.flush()

    # ---------------------------------------------------------- الأعراض
    symptom_by_slug = {}
    for slug, name_ar, name_en, cat_slug, keywords in SYMPTOMS:
        s = Symptom.query.filter_by(slug=slug).first()
        if s is None:
            s = Symptom(slug=slug)
            db.session.add(s)
            stats["symptoms"] += 1
        s.name_ar = name_ar
        s.name_en = name_en
        s.category_id = cat_by_slug[cat_slug].id if cat_slug in cat_by_slug else None
        s.keywords = keywords
        symptom_by_slug[slug] = s
    db.session.flush()

    # ---------------------------------------------------------- المقالات
    for data in ALL_FAULTS:
        fault = Fault.query.filter_by(slug=data["slug"]).first()
        if fault is None:
            fault = Fault(slug=data["slug"])
            db.session.add(fault)
            stats["faults"] += 1
        fault.title_ar = data["title_ar"]
        fault.title_en = data.get("title_en")
        fault.category_id = cat_by_slug[data["category"]].id
        fault.code = data.get("code") or "لا يوجد رمز موثق"
        fault.severity = data.get("severity", "medium")
        fault.symptoms_text = data["symptoms"]
        fault.causes = data.get("causes", "")
        fault.suspect_part = data.get("suspect_part")
        fault.part_number = data.get("part_number")
        fault.part_number_confidence = data.get("part_number_confidence", "unverified")
        fault.tools = data.get("tools", "")
        fault.initial_checks = data.get("initial_checks", "")
        fault.diagnosis_tree = data.get("diagnosis_tree", "")
        fault.repair_steps = data.get("repair_steps", "")
        fault.verification = data.get("verification", "")
        fault.final_test = data.get("final_test", "")
        fault.common_mistakes = data.get("common_mistakes", "")
        fault.stop_when = data.get("stop_when", "")
        fault.safety_note = data.get("safety_note")
        fault.source_name = data.get("source_name")
        fault.source_url = data.get("source_url")
        fault.source_needed = data.get("source_needed")
        fault.confidence = data.get("confidence", "unverified")
        fault.status = data.get("status", "published")
        fault.reviewed_at = date.today()
        fault.models = [model_by_slug[s] for s in data.get("models", []) if s in model_by_slug]
        fault.search_blob = make_search_blob(
            fault.title_ar, fault.title_en, fault.code, fault.symptoms_text, fault.causes,
            fault.suspect_part, fault.part_number, fault.tools, fault.repair_steps,
            fault.diagnosis_tree, fault.title_ar.replace("ال", " "),
        )
        db.session.flush()
        # روابط الأعراض (تشخيص + مقارنة الأعراض)
        links = {row[0] for row in db.session.execute(
            db.select(fault_symptoms.c.symptom_id).where(
                fault_symptoms.c.fault_id == fault.id)).all()}
        for key in data.get("symptoms_keys", []):
            sym = symptom_by_slug.get(key)
            if sym and sym.id not in links:
                db.session.execute(fault_symptoms.insert().values(
                    fault_id=fault.id, symptom_id=sym.id, weight=4))
                links.add(sym.id)

    # ---------------------------------------------------------- أسئلة المعالج
    for data in QUESTIONS:
        q = Question.query.filter_by(slug=data["slug"]).first()
        if q is None:
            q = Question(slug=data["slug"])
            db.session.add(q)
            stats["questions"] += 1
        q.text_ar = data["text"]
        q.help_ar = data.get("help")
        trigger = data.get("trigger")
        q.trigger_symptom_id = symptom_by_slug[trigger].id if trigger else None
        model_slug = data.get("model")
        q.model_id = model_by_slug[model_slug].id if model_slug else None
        q.sort_order = data.get("sort", 10)
        db.session.flush()
        for label, weight_map in data["options"]:
            opt = QuestionOption.query.filter_by(question_id=q.id, label_ar=label).first()
            if opt is None:
                opt = QuestionOption(question_id=q.id, label_ar=label)
                db.session.add(opt)
            import json
            opt.weight_map = json.dumps(weight_map, ensure_ascii=False)
    db.session.flush()

    # ---------------------------------------------------------- المراجع
    for data in REFERENCES:
        ref = Reference.query.filter_by(title=data["title"]).first()
        if ref is None:
            ref = Reference(title=data["title"])
            db.session.add(ref)
            stats["references"] += 1
        ref.url = data.get("url")
        ref.publisher = data.get("publisher")
        ref.ref_type = data.get("ref_type", "user_guide")
        ref.model_id = model_by_slug[data["model"]].id if data.get("model") else None
        ref.notes = data.get("notes")
        ref.verified = bool(data.get("verified"))

    # ---------------------------------------------------------- المخططات المرفقة
    for data in BUNDLED_IMAGES:
        img = Image.query.filter_by(filename=data["filename"], storage="bundled").first()
        if img is None:
            img = Image(filename=data["filename"], storage="bundled")
            db.session.add(img)
            stats["images"] += 1
        img.title = data["title"]
        img.description = data["description"]
        img.model_id = model_by_slug[data["model"]].id if data.get("model") else None
        img.image_type = data.get("image_type", "diagram")
        img.is_original = bool(data.get("is_original"))
        img.source = data.get("source")
        img.license_note = data.get("license_note")
        img.step_hint = data.get("step_hint")

    db.session.commit()
    return stats


def ensure_seed(force: bool = False) -> dict | None:
    """ينفّذ التحميل مرة واحدة فقط إن كانت قاعدة البيانات فارغة."""
    from .models import Fault
    try:
        if Fault.query.count() == 0 or force:
            return seed_all(force=force)
    except Exception:
        db.session.rollback()
        return None
    return None
