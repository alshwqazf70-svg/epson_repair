"""حزمة التطبيق: مصنع التطبيق create_app()."""
from __future__ import annotations

from datetime import timedelta
from functools import wraps
from datetime import datetime
from flask import Flask, abort, flash, g, redirect, render_template, session, url_for
from flask_wtf.csrf import CSRFProtect, generate_csrf

from .config import BASE_DIR, get_config
from .models import Category, PrinterModel, User, db

csrf = CSRFProtect()

# ثوابت جلسة الدخول
SESSION_KEY = "uid"
CSRF_FIELD = "csrf_token"


def create_app(config_name: str | None = None, database_uri: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
        static_url_path="/static",
    )
    cfg = get_config(config_name)
    app.config.from_object(cfg)
    cfg.init_dirs()

    if database_uri:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    if app.config.get("TESTING"):
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri or "sqlite:///:memory:"

    app.permanent_session_lifetime = timedelta(seconds=app.config["PERMANENT_SESSION_LIFETIME"])

    db.init_app(app)
    csrf.init_app(app)

    # ---------------------------------------------------------- المخططات
    from .routes.auth import auth_bp
    from .routes.public import public_bp
    from .routes.diag import diag_bp
    from .routes.admin import admin_bp
    from .routes.media import media_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(diag_bp, url_prefix="/diag")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(media_bp)

    # ---------------------------------------------------------- السياق العام
    @app.context_processor
    def inject_globals():
        try:
            nav_models = PrinterModel.query.filter_by(is_active=True).order_by(
                PrinterModel.sort_order).all()
            nav_categories = Category.query.order_by(Category.sort_order).all()
        except Exception:
            nav_models, nav_categories = [], []
        return {
            "APP_NAME_AR": app.config["APP_NAME_AR"],
            "APP_NAME_EN": app.config["APP_NAME_EN"],
            "nav_models": nav_models,
            "nav_categories": nav_categories,
            "current_user": current_user(),
            "csrf_token": generate_csrf,
        }

    @app.template_filter("datetimeformat")
    def _datetimeformat(value):
        """تحويل طابع زمني (ثوانٍ منذ 1970) إلى نص مقروء."""
        try:
            return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "—"

    @app.before_request
    def _make_session_permanent():
        session.permanent = True

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'",
        )
        return resp

    # ---------------------------------------------------------- صفحات الخطأ
    @app.errorhandler(403)
    def _e403(err):
        return render_template("errors/403.html", error=err), 403

    @app.errorhandler(404)
    def _e404(err):
        return render_template("errors/404.html", error=err), 404

    @app.errorhandler(413)
    def _e413(err):
        flash("حجم الملف المرفوع أكبر من الحد المسموح.", "danger")
        return render_template("errors/413.html", error=err), 413

    @app.errorhandler(500)
    def _e500(err):
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template("errors/500.html", error=err), 500

    if app.config.get("TESTING"):
        @app.route("/_test/500")
        def _raise_500():
            raise RuntimeError("اختبار صفحة الخطأ 500")

    # ---------------------------------------------------------- أوامر CLI
    @app.cli.command("init-db")
    def init_db_cmd():
        with app.app_context():
            from .seed import seed_all
            seed_all(force=False)
        print("تم تجهيز قاعدة البيانات.")

    @app.cli.command("seed-db")
    def seed_db_cmd():
        with app.app_context():
            from .seed import seed_all
            seed_all(force=True)
        print("تم تحميل المحتوى التأسيسي.")

    return app


# ------------------------------------------------------------------ الجلسة


def current_user() -> User | None:
    if getattr(g, "_current_user", None) is not None:
        return g._current_user
    uid = session.get(SESSION_KEY)
    user = None
    if uid:
        user = db.session.get(User, uid)
        if user is None or not user.is_active:
            session.clear()
            user = None
    g._current_user = user
    return user


def login_user(user: User) -> None:
    session.clear()
    session[SESSION_KEY] = user.id
    session["login_at"] = datetime.utcnow().isoformat()


def logout_user() -> None:
    session.clear()


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            from flask import request
            flash("يجب تسجيل الدخول للوصول إلى هذه الصفحة.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    """حماية على مستوى الخادم: كل حساب في النظام هو حساب المالك/المسؤول."""
    return login_required(view)


def require_owner_or_404(obj) -> None:
    if obj is None:
        abort(404)
