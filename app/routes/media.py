"""تقديم الملفات الخاصة: خارج static، ولا تُقدَّم إلا بعد التحقق من الجلسة."""
from __future__ import annotations

from flask import Blueprint, abort, send_file

from .. import current_user
from ..utils import resolve_private_path

media_bp = Blueprint("media", __name__)


@media_bp.route("/media/<path:rel_path>")
def private_media(rel_path: str):
    """الوصول إلى الملفات المرفوعة يتطلب جلسة صالحة.

    الزائر المجهول يحصل على 403، ولا يمكن الوصول إلى أي ملف خارج مجلد الرفع.
    """
    if current_user() is None:
        abort(403)
    path = resolve_private_path(rel_path)
    return send_file(path, conditional=True, max_age=0)
