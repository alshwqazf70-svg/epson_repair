"""نماذج قاعدة البيانات.

العلاقات:
    PrinterModel 1---* Fault (عبر جدول وصل fault_models، لأن العطل قد ينطبق على أكثر من موديل)
    Category     1---* Fault
    Fault        1---* Image / MaintenanceLog
    Symptom      *---* Fault (عبر جدول وصل fault_symptoms مع وزن)
    Question     1---* QuestionOption
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, ForeignKey, Index, Integer, Table
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# جداول الوصل (Many-to-Many)
fault_models = Table(
    "fault_models",
    db.metadata,
    Column("fault_id", Integer, ForeignKey("faults.id", ondelete="CASCADE"), primary_key=True),
    Column("model_id", Integer, ForeignKey("printer_models.id", ondelete="CASCADE"), primary_key=True),
)

fault_symptoms = Table(
    "fault_symptoms",
    db.metadata,
    Column("fault_id", Integer, ForeignKey("faults.id", ondelete="CASCADE"), primary_key=True),
    Column("symptom_id", Integer, ForeignKey("symptoms.id", ondelete="CASCADE"), primary_key=True),
    Column("weight", Integer, nullable=False, default=3),
)


def utcnow() -> datetime:
    """توقيت UTC بدون منطقة زمنية (متوافق مع تخزين SQLite والمقارنات)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class User(TimestampMixin, db.Model):
    """حساب المالك/المسؤول. لا يوجد تسجيل عام."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, raw_password: str) -> None:
        if len(raw_password) < 10:
            raise ValueError("كلمة المرور يجب ألا تقل عن 10 أحرف.")
        # pbkdf2:sha256 مع عدد تكرارات أعلى من الافتراضي
        self.password_hash = generate_password_hash(raw_password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_locked(self) -> bool:
        if not self.locked_until:
            return False
        locked = self.locked_until
        if locked.tzinfo is not None:  # احتياط: قراءة قيمة قديمة بمنطقة زمنية
            locked = locked.astimezone(timezone.utc).replace(tzinfo=None)
        return locked > utcnow()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"


class PrinterModel(TimestampMixin, db.Model):
    """موديل الطابعة. الإصدار الأول يحتوي موديلين فقط، والبنية تقبل الإضافة."""

    __tablename__ = "printer_models"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(120), nullable=False)
    name_en = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60), nullable=False, default="Epson")
    printer_class = db.Column(db.String(120), nullable=True)     # فئة الطابعة
    pins = db.Column(db.String(60), nullable=True)               # عدد الإبر
    columns = db.Column(db.String(60), nullable=True)            # عدد الأعمدة
    interfaces = db.Column(db.String(200), nullable=True)        # الواجهات
    ribbon_part = db.Column(db.String(120), nullable=True)       # رقم شريط الحبر
    ribbon_part_confidence = db.Column(db.String(32), nullable=False, default="user_manual")
    mtbf = db.Column(db.String(80), nullable=True)
    print_head_life = db.Column(db.String(80), nullable=True)
    memory = db.Column(db.String(80), nullable=True)
    paper_paths = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    specs_note = db.Column(db.Text, nullable=True)   # ملاحظات التحقق من المواصفات
    sort_order = db.Column(db.Integer, nullable=False, default=10)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    faults = db.relationship("Fault", secondary=fault_models, back_populates="models", lazy="dynamic")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PrinterModel {self.slug}>"


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(120), nullable=False)
    name_en = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(40), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=10)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category {self.slug}>"


SEVERITY = {
    "low": "منخفضة",
    "medium": "متوسطة",
    "high": "مرتفعة",
    "electrical": "خطر كهربائي",
}

CONFIDENCE = {
    "service_manual": "موثق بدليل الخدمة",
    "user_manual": "موثق بدليل المستخدم",
    "secondary": "مرجع فني ثانوي",
    "unverified": "يحتاج إلى تحقق",
}

STATUS = {
    "published": "مكتمل",
    "review": "قيد المراجعة",
    "draft": "مسودة",
}


class Fault(TimestampMixin, db.Model):
    """صفحة عطل فني مستقلة بحقول القالب الإلزامي العشرين."""

    __tablename__ = "faults"
    __table_args__ = (
        Index("ix_faults_status_category", "status", "category_id"),
        Index("ix_faults_title_ar", "title_ar"),
    )

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title_ar = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    # 3) رمز العطل أو "لا يوجد رمز موثق"
    code = db.Column(db.String(120), nullable=False, default="لا يوجد رمز موثق")
    # 4) الأعراض
    symptoms_text = db.Column(db.Text, nullable=False, default="")
    # 5) درجة الخطورة
    severity = db.Column(db.String(20), nullable=False, default="medium", index=True)
    # 6) الأسباب المحتملة
    causes = db.Column(db.Text, nullable=False, default="")
    # 7) القطعة/المنطقة
    suspect_part = db.Column(db.String(200), nullable=True)
    # 8) رقم القطعة
    part_number = db.Column(db.String(120), nullable=True)
    part_number_confidence = db.Column(db.String(32), nullable=False, default="unverified")
    # 9) الأدوات
    tools = db.Column(db.Text, nullable=True)
    # 10) فحوصات أولية
    initial_checks = db.Column(db.Text, nullable=True)
    # 11) شجرة تشخيص
    diagnosis_tree = db.Column(db.Text, nullable=True)
    # 12) خطوات الإصلاح
    repair_steps = db.Column(db.Text, nullable=True)
    # 13) التحقق من نجاح الإصلاح
    verification = db.Column(db.Text, nullable=True)
    # 14) اختبار نهائي
    final_test = db.Column(db.Text, nullable=True)
    # 15) أخطاء شائعة
    common_mistakes = db.Column(db.Text, nullable=True)
    # 16) متى تتوقف
    stop_when = db.Column(db.Text, nullable=True)
    # 18) المصدر
    source_name = db.Column(db.String(200), nullable=True)
    source_url = db.Column(db.Text, nullable=True)
    # 19) تاريخ آخر مراجعة
    reviewed_at = db.Column(db.Date, nullable=True)
    # 20) مستوى الثقة
    confidence = db.Column(db.String(32), nullable=False, default="unverified", index=True)
    status = db.Column(db.String(20), nullable=False, default="published", index=True)
    safety_note = db.Column(db.Text, nullable=True)
    source_needed = db.Column(db.Text, nullable=True)   # مصدر فني مطلوب
    view_count = db.Column(db.Integer, nullable=False, default=0)
    # حقل بحث مُطبَّع (بدون تشكيل/همزات) لتسريع المطابقة
    search_blob = db.Column(db.Text, nullable=True)

    category = db.relationship("Category", backref=db.backref("faults", lazy="dynamic"))
    models = db.relationship("PrinterModel", secondary=fault_models, back_populates="faults")
    images = db.relationship("Image", backref="fault", lazy="dynamic", cascade="all, delete-orphan")
    symptom_links = db.relationship("Symptom", secondary=fault_symptoms, backref="faults")

    @property
    def severity_label(self) -> str:
        return SEVERITY.get(self.severity, self.severity)

    @property
    def confidence_label(self) -> str:
        return CONFIDENCE.get(self.confidence, self.confidence)

    @property
    def status_label(self) -> str:
        return STATUS.get(self.status, self.status)

    def model_names(self) -> str:
        return "، ".join(m.name_ar for m in self.models) or "غير محدد"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Fault {self.slug}>"


class Symptom(TimestampMixin, db.Model):
    """عرض يمكن للمستخدم اختياره في معالج التشخيص."""

    __tablename__ = "symptoms"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)
    keywords = db.Column(db.Text, nullable=True)   # كلمات بديلة وأخطاء إملائية شائعة

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Symptom {self.slug}>"


class Question(TimestampMixin, db.Model):
    """سؤال متفرّع في معالج التشخيص."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    text_ar = db.Column(db.String(300), nullable=False)
    help_ar = db.Column(db.Text, nullable=True)
    trigger_symptom_id = db.Column(db.Integer, db.ForeignKey("symptoms.id"), nullable=True, index=True)
    model_id = db.Column(db.Integer, db.ForeignKey("printer_models.id"), nullable=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=10)

    options = db.relationship("QuestionOption", backref="question", lazy="dynamic",
                              cascade="all, delete-orphan")


class QuestionOption(TimestampMixin, db.Model):
    """خيار إجابة مع تعديلات الأوزان على الأعطال."""

    __tablename__ = "question_options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    label_ar = db.Column(db.String(200), nullable=False)
    # خريطة أوزان: {"slug-العطل": +2 أو -1}
    weight_map = db.Column(db.Text, nullable=False, default="{}")
    sort_order = db.Column(db.Integer, nullable=False, default=10)


class Image(TimestampMixin, db.Model):
    """صورة أو مخطط مرتبط بموديل أو عطل."""

    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey("printer_models.id"), nullable=True, index=True)
    fault_id = db.Column(db.Integer, db.ForeignKey("faults.id", ondelete="CASCADE"),
                         nullable=True, index=True)
    # bundled: ملف مرفق داخل static  | uploaded: ملف مرفوع في private_uploads
    storage = db.Column(db.String(20), nullable=False, default="bundled")
    filename = db.Column(db.String(255), nullable=False)      # مسار نسبي أو اسم آمن
    thumb_filename = db.Column(db.String(255), nullable=True)
    image_type = db.Column(db.String(40), nullable=False, default="photo")  # photo|diagram|panel
    is_original = db.Column(db.Boolean, nullable=False, default=False)      # أصلي أم توضيحي
    source = db.Column(db.String(300), nullable=True)
    license_note = db.Column(db.String(300), nullable=True)
    step_hint = db.Column(db.String(200), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Image {self.title}>"


class Reference(TimestampMixin, db.Model):
    """مرجع فني / مصدر معلومات."""

    __tablename__ = "references"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    url = db.Column(db.Text, nullable=True)
    publisher = db.Column(db.String(120), nullable=True)
    ref_type = db.Column(db.String(40), nullable=False, default="user_guide")
    model_id = db.Column(db.Integer, db.ForeignKey("printer_models.id"), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)


class MaintenanceLog(TimestampMixin, db.Model):
    """سجل صيانة شخصي (خاص، لا يُعرض للزوار)."""

    __tablename__ = "maintenance_logs"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("printer_models.id"), nullable=True, index=True)
    fault_id = db.Column(db.Integer, db.ForeignKey("faults.id", ondelete="SET NULL"),
                         nullable=True, index=True)
    log_date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False, default="عملية صيانة")
    symptoms = db.Column(db.Text, nullable=True)
    initial_diagnosis = db.Column(db.Text, nullable=True)
    tests_done = db.Column(db.Text, nullable=True)
    parts_cleaned = db.Column(db.Text, nullable=True)
    parts_replaced = db.Column(db.Text, nullable=True)
    repair_done = db.Column(db.Text, nullable=True)
    result = db.Column(db.String(40), nullable=False, default="unknown", index=True)  # success|partial|failed|unknown
    notes = db.Column(db.Text, nullable=True)

    model = db.relationship("PrinterModel")
    fault = db.relationship("Fault")
    attachments = db.relationship("LogAttachment", backref="log", lazy="dynamic",
                                  cascade="all, delete-orphan")

    @property
    def result_label(self) -> str:
        return {
            "success": "نجح الإصلاح",
            "partial": "نجاح جزئي",
            "failed": "لم ينجح",
            "unknown": "غير محدد",
        }.get(self.result, self.result)


class LogAttachment(TimestampMixin, db.Model):
    __tablename__ = "log_attachments"

    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey("maintenance_logs.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(20), nullable=False, default="before")  # before|after|other
    caption = db.Column(db.String(200), nullable=True)


class ActivityLog(db.Model):
    """سجل تعديلات المحتوى وإجراءات الحساب الحساسة."""

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    username = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(60), nullable=False, index=True)   # create|update|delete|login|...
    entity = db.Column(db.String(60), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(300), nullable=True)
    ip = db.Column(db.String(60), nullable=True)


class Note(TimestampMixin, db.Model):
    """ملاحظة صيانة شخصية سريعة."""

    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey("printer_models.id"), nullable=True, index=True)
    fault_id = db.Column(db.Integer, db.ForeignKey("faults.id", ondelete="SET NULL"), nullable=True)
