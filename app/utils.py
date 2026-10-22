"""أدوات مساعدة: تطبيع النص العربي، البحث، الرفع الآمن، النسخ الاحتياطي، السجل."""
from __future__ import annotations

import json
import os
import re
import secrets
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from flask import abort, current_app, request
from werkzeug.utils import secure_filename

from .models import ActivityLog, db

# ---------------------------------------------------------------- تطبيع النص


_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_NORMALIZE_MAP = {
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ی": "ي",
    "ة": "ه", "ؤ": "و", "ئ": "ي", "ء": "", "ً": "", "ٌ": "", "ٍ": "",
}
_AR_PUNCT = re.compile(r"[^\w\s\u0600-\u06FF]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize_text(text: str | None) -> str:
    """تطبيع النص للمطابقة: إزالة التشكيل وتوحيد الألف والهمزة والتاء المربوطة."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = _DIACRITICS.sub("", text)
    text = "".join(_NORMALIZE_MAP.get(ch, ch) for ch in text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = _WS.sub(" ", text)
    return text.strip().lower()


def make_search_blob(*parts: str | None) -> str:
    return normalize_text(" ".join(p for p in parts if p))


def highlight(text: str | None, query: str | None) -> str:
    """إبراز كلمات البحث مع ترميز المخرجات (تمنع XSS عبر escape)."""
    from markupsafe import escape

    if not text:
        return ""
    safe = escape(str(text))
    if not query:
        return safe
    tokens = [normalize_text(t) for t in query.split() if normalize_text(t)]
    if not tokens:
        return safe
    out = escape(str(text))
    for token in tokens[:6]:
        if len(token) < 2:
            continue
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        out = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", out)
    return out


def slugify(text: str, fallback: str = "item") -> str:
    base = normalize_text(text).replace(" ", "-")
    base = re.sub(r"-+", "-", base).strip("-")
    if not base:
        base = fallback
    # الأبجدية العربية والحروف اللاتينية والأرقام فقط
    base = re.sub(r"[^\w\u0600-\u06FF\-]", "", base, flags=re.UNICODE)
    return base[:80] or fallback


def unique_slug(model, value: str, obj_id: int | None = None) -> str:
    """يولّد slug فريداً داخل الجدول."""
    base = slugify(value)
    candidate = base
    i = 2
    while True:
        q = model.query.filter(model.slug == candidate)
        if obj_id:
            q = q.filter(model.id != obj_id)
        if q.first() is None:
            return candidate
        candidate = f"{base}-{i}"
        i += 1


# ---------------------------------------------------------------- البحث


def search_faults(query: str, model_id: int | None = None, category_id: int | None = None,
                  published_only: bool = True):
    """بحث يقبل العربية والإنجليزية والكلمات البديلة والأخطاء الإملائية الشائعة.

    المطابقة تتم على حقل search_blob المطبَّع (بدون تشكيل/همزات).
    """
    from .models import Fault

    qs = Fault.query
    if published_only:
        qs = qs.filter(Fault.status == "published")
    if model_id:
        qs = qs.filter(Fault.models.any(id=model_id))
    if category_id:
        qs = qs.filter(Fault.category_id == category_id)

    # نتجاهل الرموز المفردة (مثل حرف "a") لأنها تُطابق كل شيء ولا معنى لها
    tokens = [t for t in normalize_text(query).split() if len(t) >= 2]
    if not tokens:
        return qs.order_by(Fault.title_ar).all()

    results = {}
    for token in tokens:
        like = f"%{token}%"
        for fault in qs.filter(Fault.search_blob.like(like)).all():
            results[fault.id] = results.get(fault.id, 0) + 1
    if not results:
        return []
    ids = sorted(results, key=lambda k: (-results[k], k))
    order = {fid: i for i, fid in enumerate(ids)}
    faults = Fault.query.filter(Fault.id.in_(ids)).all()
    return sorted(faults, key=lambda f: order[f.id])


# ---------------------------------------------------------------- الرفع الآمن

_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"BM": "bmp",
}


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def sniff_image(stream) -> str | None:
    """التحقق من نوع الصورة من توقيع البايتات (لا نثق بالامتداد وحده)."""
    head = stream.read(32)
    stream.seek(0)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:2] == b"BM":
        return "bmp"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def save_private_upload(file_storage, subdir: str = "") -> str:
    """يحفظ ملفاً مرفوعاً باسم آمن وفريد داخل مجلد خاص خارج static."""
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target_dir = (upload_root / subdir).resolve() if subdir else upload_root
    # منع Path Traversal: يجب أن يبقى المسار داخل مجلد الرفع
    if upload_root != target_dir and upload_root not in target_dir.parents:
        abort(400, "مسار رفع غير صالح")
    target_dir.mkdir(parents=True, exist_ok=True)

    original = secure_filename(file_storage.filename or "")
    if not original or not allowed_file(original):
        abort(400, "نوع الملف غير مسموح به. المسموح: صور PNG/JPG/JPEG/GIF/WEBP/BMP فقط.")
    kind = sniff_image(file_storage.stream)
    if kind is None:
        abort(400, "محتوى الملف ليس صورة صالحة.")
    ext = original.rsplit(".", 1)[1].lower()
    if kind == "jpg" and ext not in {"jpg", "jpeg"}:
        abort(400, "امتداد الملف لا يطابق محتواه.")

    max_len = current_app.config.get("MAX_CONTENT_LENGTH") or 5 * 1024 * 1024
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_len:
        abort(413, f"حجم الملف يتجاوز الحد المسموح ({max_len // (1024 * 1024)} ميغابايت).")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{stamp}-{secrets.token_hex(8)}.{ext}"
    dest = target_dir / filename
    file_storage.save(dest)
    return filename if not subdir else str(Path(subdir) / filename).replace("\\", "/")


def resolve_private_path(rel_path: str) -> Path:
    """يحوّل مساراً نسبياً إلى مسار آمن داخل مجلد الرفع، ويمنع Path Traversal."""
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    candidate = (upload_root / rel_path).resolve()
    if upload_root != candidate and upload_root not in candidate.parents:
        abort(404)
    if not candidate.is_file():
        abort(404)
    return candidate


def make_thumbnail(path: Path) -> str | None:
    """يولّد صورة مصغّرة إن كانت مكتبة Pillow متاحة. يعيد None بدون Pillow."""
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        thumbs_dir = path.parent / "thumbs"
        thumbs_dir.mkdir(exist_ok=True)
        dest = thumbs_dir / path.name
        with Image.open(path) as img:
            img.thumbnail((420, 420))
            img.save(dest)
        return str(Path(path.parent.name) / "thumbs" / path.name).replace("\\", "/") \
            if path.parent.name else f"thumbs/{path.name}"
    except Exception:
        return None


# ---------------------------------------------------------------- النسخ الاحتياطي


def create_backup(app) -> Path:
    """ينشئ أرشيفاً مضغوطاً فيه قاعدة البيانات + الملفات الخاصة."""
    backup_dir = Path(app.config["BACKUP_FOLDER"]).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(app.config["DATABASE_PATH"]).resolve()
    uploads = Path(app.config["UPLOAD_FOLDER"]).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = backup_dir / f"backup-{stamp}.zip"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_path.is_file():
            zf.write(db_path, arcname=f"data/{db_path.name}")
        if uploads.is_dir():
            for p in uploads.rglob("*"):
                if p.is_file() and "thumbs" not in p.parts:
                    zf.write(p, arcname=f"private_uploads/{p.relative_to(uploads).as_posix()}")
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app": app.config["APP_NAME_EN"],
            "db": db_path.name,
        }
        zf.writestr("backup_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    return out


def restore_backup(app, archive: Path) -> dict:
    """يستعيد قاعدة البيانات والملفات من أرشيف النسخ الاحتياطي."""
    if not zipfile.is_zipfile(archive):
        raise ValueError("الملف ليس أرشيفاً مضغوطاً صالحاً.")
    db_path = Path(app.config["DATABASE_PATH"]).resolve()
    uploads = Path(app.config["UPLOAD_FOLDER"]).resolve()
    uploads.mkdir(parents=True, exist_ok=True)
    restored = {"db": False, "files": 0}
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        db_member = next((n for n in names if n.startswith("data/") and n.endswith(".db")), None)
        if db_member:
            data = zf.read(db_member)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = db_path.with_suffix(".db.restore")
            tmp.write_bytes(data)
            tmp.replace(db_path)
            restored["db"] = True
        for n in names:
            if n.startswith("private_uploads/") and not n.endswith("/"):
                rel = n[len("private_uploads/"):]
                dest = (uploads / rel).resolve()
                if uploads != dest.parent and uploads not in dest.parents:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(n))
                restored["files"] += 1
    return restored


# ---------------------------------------------------------------- السجل


def log_activity(action: str, entity: str | None = None, entity_id: int | None = None,
                 details: str | None = None, username: str | None = None) -> None:
    """يسجّل حدثاً. لا يسجّل كلمات مرور أو بيانات حساسة أبداً."""
    try:
        entry = ActivityLog(
            username=username or "system",
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=(details or "")[:290],
            ip=(request.headers.get("X-Forwarded-For", request.remote_addr) if request else None),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:  # لا نسماح بانهيار التطبيق بسبب فشل التسجيل
        db.session.rollback()
        current_app.logger.exception("تعذّر تسجيل النشاط")


def parse_weight_map(raw: str | None) -> dict:
    try:
        data = json.loads(raw or "{}")
        if isinstance(data, dict):
            return {str(k): int(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def multiline_to_list(text: str | None) -> list[str]:
    if not text:
        return []
    return [line.strip(" \t-–•") for line in str(text).splitlines() if line.strip()]


def json_export(rows) -> str:
    return json.dumps(rows, ensure_ascii=False, indent=2, default=str)
