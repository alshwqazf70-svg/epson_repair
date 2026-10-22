"""المصادقة: دخول، خروج، تغيير كلمة المرور. لا يوجد تسجيل عام."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .. import current_user, login_required, login_user, logout_user
from ..forms import ChangePasswordForm, LoginForm
from ..models import User, db
from ..utils import log_activity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("admin.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        # الحد من المحاولات: قفل مؤقت بعد عدة محاولات فاشلة
        if user and user.is_locked():
            flash("تم قفل الحساب مؤقتاً بسبب محاولات دخول فاشلة متكررة. حاول لاحقاً.", "danger")
            log_activity("login_locked", "user", user.id, "حساب مقفل")
            return render_template("auth/login.html", form=form), 429
        if user and user.check_password(form.password.data):
            user.failed_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            login_user(user)
            log_activity("login", "user", user.id, "دخول ناجح", username=user.username)
            flash("تم تسجيل الدخول بنجاح.", "success")
            nxt = request.args.get("next") or ""
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard"))
        # رسالة موحّدة: لا نكشف ما إذا كان المستخدم موجوداً
        if user:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            max_attempts = 5
            if user.failed_attempts >= max_attempts:
                user.locked_until = datetime.utcnow() + timedelta(minutes=10)
                user.failed_attempts = 0
            db.session.commit()
        log_activity("login_failed", "user", user.id if user else None, "محاولة دخول فاشلة")
        flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """الخروج يتم بطلب POST مع توكن CSRF لإنهاء الجلسة فعلياً."""
    user = current_user()
    if user:
        log_activity("logout", "user", user.id, "خروج", username=user.username)
    logout_user()
    session.clear()
    flash("تم إنهاء الجلسة بنجاح.", "success")
    return redirect(url_for("public.index"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    user = current_user()
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not user.check_password(form.current_password.data):
            flash("كلمة المرور الحالية غير صحيحة.", "danger")
        else:
            try:
                user.set_password(form.new_password.data)
                db.session.commit()
                log_activity("password_change", "user", user.id, "تغيير كلمة المرور",
                             username=user.username)
                flash("تم تغيير كلمة المرور بنجاح.", "success")
                return redirect(url_for("admin.dashboard"))
            except ValueError as exc:
                flash(str(exc), "danger")
    return render_template("auth/change_password.html", form=form)
