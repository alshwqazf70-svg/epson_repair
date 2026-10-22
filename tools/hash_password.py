# -*- coding: utf-8 -*-
"""توليد hash لكلمة مرور باستخدام Werkzeug لاستخدامه في الإعداد غير التفاعلي.

الاستخدام:
    python3 tools/hash_password.py
ثم انسخ الناتج إلى المتغير ADMIN_PASSWORD_HASH في بيئة الاستضافة.
"""
from __future__ import annotations

import getpass

from werkzeug.security import generate_password_hash


def main() -> int:
    pwd = getpass.getpass("كلمة المرور: ")
    confirm = getpass.getpass("تأكيد كلمة المرور: ")
    if pwd != confirm:
        print("كلمتا المرور غير متطابقتين.")
        return 1
    if len(pwd) < 10:
        print("كلمة المرور يجب ألا تقل عن 10 أحرف.")
        return 1
    print("\nانسخ السطر التالي إلى ADMIN_PASSWORD_HASH:\n")
    print(generate_password_hash(pwd, method="pbkdf2:sha256", salt_length=16))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
