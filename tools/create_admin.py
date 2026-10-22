# -*- coding: utf-8 -*-
"""إنشاء حساب المالك/المسؤول بطريقة آمنة.

الاستخدام التفاعلي (موصى به):
    python3 tools/create_admin.py

أو غير تفاعلي عبر متغيرات بيئة (مفيد على PythonAnywhere):
    ADMIN_USERNAME=owner ADMIN_PASSWORD_HASH='pbkdf2:sha256:...' python3 tools/create_admin.py

ملاحظة: لا تضع كلمة مرور كنص صريح في الملفات أو في Git.
يمكن توليد hash بكلمة مرور عبر:
    python3 tools/hash_password.py
"""
from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


def create_admin_interactive(app) -> bool:
    from app.models import User, db
    from app.utils import log_activity

    existing = User.query.first()
    if existing:
        print(f"يوجد حساب بالفعل: {existing.username}")
        ans = input("هل تريد تغيير كلمة مروره؟ (ن/لا): ").strip().lower()
        if ans not in ("y", "yes", "ن", "نعم"):
            print("لم يُجرَ أي تغيير.")
            return False
        user = existing
    else:
        username = os.environ.get("ADMIN_USERNAME") or input("اسم المستخدم: ").strip()
        if not username:
            print("لم يُدخل اسم مستخدم.")
            return False
        user = User(username=username)

    env_hash = os.environ.get("ADMIN_PASSWORD_HASH")
    if env_hash and env_hash.startswith("pbkdf2:"):
        user.password_hash = env_hash
    else:
        pwd = getpass.getpass("كلمة المرور (10 أحرف على الأقل، لا تظهر أثناء الكتابة): ")
        confirm = getpass.getpass("تأكيد كلمة المرور: ")
        if pwd != confirm:
            print("كلمتا المرور غير متطابقتين.")
            return False
        try:
            user.set_password(pwd)
        except ValueError as exc:
            print(f"خطأ: {exc}")
            return False

    if user.id is None:
        db.session.add(user)
    db.session.commit()
    log_activity("create", "user", user.id, "إنشاء/تحديث حساب المسؤول", username=user.username)
    print(f"تم حفظ الحساب: {user.username}")
    return True


def main() -> int:
    from app import create_app
    app = create_app(os.environ.get("FLASK_ENV", "production"))
    with app.app_context():
        from app.models import db
        db.create_all()
        ok = create_admin_interactive(app)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
