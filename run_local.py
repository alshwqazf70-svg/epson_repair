# -*- coding: utf-8 -*-
"""تشغيل المشروع محلياً على جهازك أو داخل بيئة التطوير.

الاستخدام:
    python3 run_local.py                 # تشغيل على http://127.0.0.1:8000
    python3 run_local.py --port 5000
    python3 run_local.py --init          # تجهيز قاعدة البيانات والمحتوى التأسيسي
    python3 run_local.py --create-admin  # إنشاء حساب المالك (يطلب كلمة مرور)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="تشغيل موسوعة إبسون للصيانة محلياً")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--init", action="store_true", help="إنشاء قاعدة البيانات والمحتوى")
    parser.add_argument("--create-admin", action="store_true", help="إنشاء حساب المسؤول")
    parser.add_argument("--debug", action="store_true", help="وضع التصحيح (للتطوير فقط)")
    args = parser.parse_args()

    from app import create_app
    app = create_app("development" if args.debug else "production")

    if args.init or args.create_admin:
        with app.app_context():
            if args.init:
                from app.seed import seed_all
                from app.models import db
                db.create_all()
                stats = seed_all()
                print("تم تحميل المحتوى التأسيسي:", stats)
            if args.create_admin:
                from tools.create_admin import create_admin_interactive
                create_admin_interactive(app)
        # الأوامر الإدارية تنتهي دون تشغيل الخادم
        return 0

    print(f"الرابط: http://{args.host}:{args.port}")
    print("للإيقاف: Ctrl+C")
    app.run(host=args.host, port=args.port, debug=bool(args.debug))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
