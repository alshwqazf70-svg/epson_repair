"""نماذج الإدخال (WTForms + حماية CSRF) مع تحقق على الخادم."""
from __future__ import annotations

import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import (BooleanField, DateField, IntegerField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from .models import Category, PrinterModel


class LoginForm(FlaskForm):
    username = StringField("اسم المستخدم", validators=[DataRequired("اسم المستخدم مطلوب"),
                                                       Length(min=3, max=64)])
    password = StringField("كلمة المرور", validators=[DataRequired("كلمة المرور مطلوبة")])
    submit = SubmitField("دخول")


class ChangePasswordForm(FlaskForm):
    current_password = StringField("كلمة المرور الحالية",
                                   validators=[DataRequired("الحقل مطلوب")])
    new_password = StringField("كلمة المرور الجديدة",
                               validators=[DataRequired("الحقل مطلوب"), Length(min=10, max=128)])
    confirm_password = StringField("تأكيد كلمة المرور الجديدة",
                                   validators=[DataRequired("الحقل مطلوب")])
    submit = SubmitField("تغيير كلمة المرور")

    def validate_new_password(self, field):
        value = field.data or ""
        if len(value) < 10:
            raise ValidationError("كلمة المرور يجب ألا تقل عن 10 أحرف.")
        if value.lower() == "password" or value.isdigit():
            raise ValidationError("كلمة المرور ضعيفة جداً.")
        if self.confirm_password.data and value != self.confirm_password.data:
            raise ValidationError("كلمتا المرور غير متطابقتين.")


MAX_UPLOAD_MB = 5


class FaultForm(FlaskForm):
    title_ar = StringField("اسم العطل بالعربية",
                           validators=[DataRequired("اسم العطل مطلوب"), Length(max=200)])
    title_en = StringField("الاسم الفني بالإنجليزية", validators=[Optional(), Length(max=200)])
    category_id = SelectField("تصنيف العطل", coerce=int, validators=[DataRequired("التصنيف مطلوب")])
    model_ids = SelectField("الموديل", coerce=int, validators=[Optional()])
    code = StringField("رمز العطل أو المؤشر", validators=[Optional(), Length(max=120)])
    severity = SelectField("درجة الخطورة", choices=[
        ("low", "منخفضة"), ("medium", "متوسطة"), ("high", "مرتفعة"),
        ("electrical", "خطر كهربائي")], validators=[DataRequired()])
    symptoms_text = TextAreaField("وصف الأعراض كما يلاحظها المستخدم",
                                  validators=[DataRequired("وصف الأعراض مطلوب")])
    causes = TextAreaField("الأسباب المحتملة (مرتبة حسب الاحتمال، سطر لكل سبب)",
                           validators=[Optional()])
    suspect_part = StringField("القطعة أو المنطقة المحتملة", validators=[Optional(), Length(max=200)])
    part_number = StringField("رقم القطعة", validators=[Optional(), Length(max=120)])
    part_number_confidence = SelectField("موثوقية رقم القطعة", choices=[
        ("service_manual", "موثق بدليل الخدمة"),
        ("user_manual", "موثق بدليل المستخدم"),
        ("secondary", "مرجع فني ثانوي"),
        ("unverified", "يحتاج إلى تحقق")], default="unverified")
    tools = TextAreaField("الأدوات المطلوبة (سطر لكل أداة)", validators=[Optional()])
    initial_checks = TextAreaField("فحوصات أولية بسيطة وآمنة", validators=[Optional()])
    diagnosis_tree = TextAreaField("شجرة تشخيص متدرجة", validators=[Optional()])
    repair_steps = TextAreaField("خطوات الإصلاح التفصيلية", validators=[Optional()])
    verification = TextAreaField("طريقة التحقق من نجاح الإصلاح", validators=[Optional()])
    final_test = TextAreaField("اختبار نهائي بعد الإصلاح", validators=[Optional()])
    common_mistakes = TextAreaField("أخطاء شائعة يجب تجنبها", validators=[Optional()])
    stop_when = TextAreaField("متى تتوقف وتطلب فنياً مختصاً", validators=[Optional()])
    safety_note = TextAreaField("تحذير سلامة إضافي", validators=[Optional()])
    source_name = StringField("اسم المصدر", validators=[Optional(), Length(max=200)])
    source_url = TextAreaField("رابط المرجع", validators=[Optional()])
    source_needed = TextAreaField("مصدر فني مطلوب (إن لم يتحقق المصدر)", validators=[Optional()])
    reviewed_at = DateField("تاريخ آخر مراجعة فنية (YYYY-MM-DD)", validators=[Optional()],
                            format="%Y-%m-%d")
    confidence = SelectField("مستوى الثقة", choices=[
        ("service_manual", "موثق بدليل الخدمة"),
        ("user_manual", "موثق بدليل المستخدم"),
        ("secondary", "مرجع فني ثانوي"),
        ("unverified", "يحتاج إلى تحقق")], validators=[DataRequired()])
    status = SelectField("حالة المقالة", choices=[
        ("published", "مكتمل"), ("review", "قيد المراجعة"), ("draft", "مسودة")],
        validators=[DataRequired()])
    submit = SubmitField("حفظ")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name_ar) for c in
                                    Category.query.order_by(Category.sort_order).all()]
        self.model_ids.choices = [(0, "— اختر موديلاً —")] + [
            (m.id, m.name_ar) for m in PrinterModel.query.order_by(PrinterModel.sort_order).all()]

    def validate_source_url(self, field):
        if field.data and not re.match(r"^https?://", field.data.strip(), re.I):
            raise ValidationError("الرابط يجب أن يبدأ بـ http:// أو https://")


class CategoryForm(FlaskForm):
    name_ar = StringField("اسم التصنيف بالعربية",
                          validators=[DataRequired("الاسم مطلوب"), Length(max=120)])
    name_en = StringField("الاسم بالإنجليزية", validators=[Optional(), Length(max=120)])
    description = TextAreaField("وصف التصنيف", validators=[Optional()])
    icon = StringField("رمز (اختياري)", validators=[Optional(), Length(max=40)])
    sort_order = IntegerField("ترتيب العرض", default=10)
    submit = SubmitField("حفظ")


class ModelForm(FlaskForm):
    name_ar = StringField("اسم الموديل بالعربية",
                          validators=[DataRequired("الاسم مطلوب"), Length(max=120)])
    name_en = StringField("الاسم بالإنجليزية",
                          validators=[DataRequired("الاسم مطلوب"), Length(max=120)])
    printer_class = StringField("فئة الطابعة", validators=[Optional(), Length(max=120)])
    pins = StringField("عدد الإبر", validators=[Optional(), Length(max=60)])
    columns = StringField("عدد الأعمدة", validators=[Optional(), Length(max=60)])
    interfaces = StringField("الواجهات", validators=[Optional(), Length(max=200)])
    ribbon_part = StringField("رقم شريط الحبر", validators=[Optional(), Length(max=120)])
    ribbon_part_confidence = SelectField("موثوقية رقم الشريط", choices=[
        ("service_manual", "موثق بدليل الخدمة"),
        ("user_manual", "موثق بدليل المستخدم"),
        ("secondary", "مرجع فني ثانوي"),
        ("unverified", "يحتاج إلى تحقق")], default="user_manual")
    mtbf = StringField("MTBF", validators=[Optional(), Length(max=80)])
    print_head_life = StringField("عمر رأس الطباعة", validators=[Optional(), Length(max=80)])
    memory = StringField("الذاكرة", validators=[Optional(), Length(max=80)])
    paper_paths = TextAreaField("مسارات الورق", validators=[Optional()])
    summary = TextAreaField("نبذة عن الموديل", validators=[Optional()])
    specs_note = TextAreaField("ملاحظات التحقق من المواصفات", validators=[Optional()])
    sort_order = IntegerField("ترتيب العرض", default=10)
    is_active = BooleanField("مفعّل")
    submit = SubmitField("حفظ")


class ImageForm(FlaskForm):
    title = StringField("عنوان الصورة", validators=[DataRequired("العنوان مطلوب"),
                                                    Length(max=200)])
    description = TextAreaField("وصف الصورة")
    model_id = SelectField("الموديل", coerce=int, validators=[Optional()])
    fault_id = SelectField("العطل المرتبط", coerce=int, validators=[Optional()])
    image_type = SelectField("نوع الصورة", choices=[
        ("photo", "صورة"), ("diagram", "مخطط توضيحي"), ("panel", "لوحة تحكم")],
        default="photo")
    is_original = BooleanField("صورة أصلية من مصدر موثوق (غير توضيحية)")
    source = StringField("المصدر", validators=[Optional(), Length(max=300)])
    license_note = StringField("ملاحظة الترخيص", validators=[Optional(), Length(max=300)])
    step_hint = StringField("الخطوة أو القطعة المرتبطة", validators=[Optional(), Length(max=200)])
    file = FileField("ملف الصورة", validators=[
        FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "bmp"], "نوع صورة غير مسموح"),
        FileSize(max_size=MAX_UPLOAD_MB * 1024 * 1024,
                 message=f"حجم الصورة يتجاوز {MAX_UPLOAD_MB} ميغابايت")])
    submit = SubmitField("رفع الصورة")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Fault
        self.model_id.choices = [(0, "— عام —")] + [
            (m.id, m.name_ar) for m in PrinterModel.query.order_by(PrinterModel.sort_order).all()]
        self.fault_id.choices = [(0, "— بدون —")] + [
            (f.id, f.title_ar[:70]) for f in Fault.query.order_by(Fault.title_ar).all()]


class ReferenceForm(FlaskForm):
    title = StringField("عنوان المرجع", validators=[DataRequired("العنوان مطلوب"),
                                                    Length(max=250)])
    url = TextAreaField("الرابط", validators=[Optional()])
    publisher = StringField("الناشر", validators=[Optional(), Length(max=120)])
    ref_type = SelectField("نوع المرجع", choices=[
        ("user_guide", "دليل المستخدم"), ("service_manual", "دليل الخدمة"),
        ("spec_sheet", "ورقة مواصفات"), ("article", "مقال/مرجع ثانوي"),
        ("internal", "ملاحظة داخلية")], default="user_guide")
    model_id = SelectField("الموديل", coerce=int, validators=[Optional()])
    notes = TextAreaField("ملاحظات")
    verified = BooleanField("تم التحقق من المرجع")
    submit = SubmitField("حفظ")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_id.choices = [(0, "— عام —")] + [
            (m.id, m.name_ar) for m in PrinterModel.query.order_by(PrinterModel.sort_order).all()]


class MaintenanceLogForm(FlaskForm):
    model_id = SelectField("الموديل", coerce=int, validators=[Optional()])
    fault_id = SelectField("العطل المرتبط", coerce=int, validators=[Optional()])
    log_date = DateField("تاريخ الصيانة", validators=[DataRequired("التاريخ مطلوب")],
                         format="%Y-%m-%d")
    title = StringField("عنوان العملية", validators=[DataRequired("العنوان مطلوب"),
                                                     Length(max=200)])
    symptoms = TextAreaField("الأعراض")
    initial_diagnosis = TextAreaField("التشخيص الأولي")
    tests_done = TextAreaField("الاختبارات التي أُجريت")
    parts_cleaned = TextAreaField("القطع التي تم تنظيفها")
    parts_replaced = TextAreaField("القطع التي تم تغييرها")
    repair_done = TextAreaField("الإصلاح الذي تم")
    result = SelectField("النتيجة النهائية", choices=[
        ("success", "نجح الإصلاح"), ("partial", "نجاح جزئي"),
        ("failed", "لم ينجح"), ("unknown", "غير محدد")], default="unknown")
    notes = TextAreaField("ملاحظات إضافية")
    submit = SubmitField("حفظ السجل")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Fault
        self.model_id.choices = [(0, "— غير محدد —")] + [
            (m.id, m.name_ar) for m in PrinterModel.query.order_by(PrinterModel.sort_order).all()]
        self.fault_id.choices = [(0, "— بدون —")] + [
            (f.id, f.title_ar[:70]) for f in Fault.query.order_by(Fault.title_ar).all()]


class NoteForm(FlaskForm):
    title = StringField("عنوان الملاحظة", validators=[DataRequired("العنوان مطلوب"),
                                                      Length(max=200)])
    body = TextAreaField("نص الملاحظة")
    model_id = SelectField("الموديل", coerce=int, validators=[Optional()])
    submit = SubmitField("حفظ الملاحظة")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_id.choices = [(0, "— عام —")] + [
            (m.id, m.name_ar) for m in PrinterModel.query.order_by(PrinterModel.sort_order).all()]


class SearchForm(FlaskForm):
    q = StringField("بحث", validators=[Optional(), Length(max=120)])
    model_id = SelectField("الموديل", coerce=int, validators=[Optional()])
    category_id = SelectField("التصنيف", coerce=int, validators=[Optional()])
    submit = SubmitField("بحث")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_id.choices = [(0, "كل الموديلات")] + [
            (m.id, m.name_ar) for m in PrinterModel.query.order_by(PrinterModel.sort_order).all()]
        self.category_id.choices = [(0, "كل التصنيفات")] + [
            (c.id, c.name_ar) for c in Category.query.order_by(Category.sort_order).all()]


class DiagnosticStartForm(FlaskForm):
    model_id = SelectField("موديل الطابعة", coerce=int, validators=[DataRequired("اختر الموديل")])
    submit = SubmitField("ابدأ التشخيص")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_id.choices = [
            (m.id, m.name_ar) for m in PrinterModel.query.filter_by(is_active=True)
            .order_by(PrinterModel.sort_order).all()]
