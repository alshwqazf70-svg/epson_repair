# -*- coding: utf-8 -*-
"""نقطة الدخول WSGI للنشر (PythonAnywhere وأي خادم WSGI آخر).

في PythonAnywhere اكتب في ملف WSGI ما يشبه:

    import sys
    path = "/home/USERNAME/epson_repair_master"
    if path not in sys.path:
        sys.path.insert(0, path)
    from wsgi import application
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# تحميل متغيرات البيئة من ملف .env إن وُجد (لا يحتوي أسراراً حقيقية في Git)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

from app import create_app  # noqa: E402
from app.seed import ensure_seed  # noqa: E402

application = create_app(os.environ.get("FLASK_ENV", "production"))

# تجهيز قاعدة البيانات عند أول تشغيل (لا ينشئ حساباً ولا يضع كلمة مرور)
with application.app_context():
    try:
        ensure_seed()
    except Exception as _exc:  # لا نكشف تفاصيل داخلية للزائر
        application.logger.warning("تعذّر التحميل التلقائي للمحتوى: %s", _exc)


if __name__ == "__main__":
    application.run()
