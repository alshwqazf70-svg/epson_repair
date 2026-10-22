"""إعدادات التطبيق.

كل القيم الحساسة تُقرأ من متغيرات البيئة. لا توجد أسرار ثابتة داخل الشيفرة.
"""
from __future__ import annotations

import os
from pathlib import Path

# جذر المشروع: المجلد الأب لمجلد الحزمة app/
BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


class Config:
    """الإعدادات الأساسية المشتركة."""

    BASE_DIR = BASE_DIR

    # لا نستخدم مفتاحاً ثابتاً في الإنتاج: يجب ضبط SECRET_KEY في البيئة.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-insecure-key-change-me"

    # قاعدة البيانات: مسار مطلق دائماً حتى لا يعتمد على مجلد التشغيل.
    DB_DIR = Path(os.environ.get("DATA_DIR") or (BASE_DIR / "data"))
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH = Path(os.environ.get("DATABASE_PATH") or (DB_DIR / "epson_repair_master.db"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}

    # مجلد الملفات الخاصة: خارج static ولا يُقدَّم إلا بعد التحقق من الجلسة.
    UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER") or (BASE_DIR / "private_uploads"))
    BACKUP_FOLDER = Path(os.environ.get("BACKUP_FOLDER") or (DB_DIR / "backups"))
    MAX_CONTENT_LENGTH = _env_int("MAX_UPLOAD_MB", 5) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}

    # الجلسات والكوكيز
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = _env_int("SESSION_LIFETIME_MINUTES", 120) * 60

    # الحماية
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = _env_int("CSRF_TIME_LIMIT", 3600)
    LOGIN_MAX_ATTEMPTS = _env_int("LOGIN_MAX_ATTEMPTS", 5)
    LOGIN_LOCK_MINUTES = _env_int("LOGIN_LOCK_MINUTES", 10)

    # نصوص الواجهة
    APP_NAME_AR = "موسوعة إبسون الاحترافية لتشخيص أعطال الطابعات وصيانتها"
    APP_NAME_EN = "EPSON REPAIR MASTER — ULTIMATE PRIVATE REPAIR ENCYCLOPEDIA"

    JSON_AS_ASCII = False
    ITEMS_PER_PAGE = _env_int("ITEMS_PER_PAGE", 20)

    # وضع التصحيح: ممنوع افتراضياً
    DEBUG = _env_bool("FLASK_DEBUG", False)
    TESTING = False

    @classmethod
    def init_dirs(cls) -> None:
        cls.DB_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.BACKUP_FOLDER.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = _env_bool("FLASK_DEBUG", True)


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)


class TestingConfig(Config):
    """إعدادات الاختبارات: قاعدة بيانات منفصلة داخل مجلد مؤقت."""

    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = True  # نختبر الحماية فعلياً، ثم نمرّر توكن صالح
    LOGIN_MAX_ATTEMPTS = 5


def get_config(name: str | None = None):
    name = (name or os.environ.get("FLASK_ENV") or "production").lower()
    return {
        "development": DevelopmentConfig,
        "dev": DevelopmentConfig,
        "testing": TestingConfig,
        "test": TestingConfig,
        "production": ProductionConfig,
        "prod": ProductionConfig,
    }.get(name, ProductionConfig)
