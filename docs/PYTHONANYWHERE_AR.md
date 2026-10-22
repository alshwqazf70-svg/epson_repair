# دليل النشر على PythonAnywhere (بالعربية، خطوة بخطوة)

هذا الدليل مكتوب لحساب **مجاني أو مدفوع** على PythonAnywhere. المشروع لا يحتاج Docker
ولا قاعدة بيانات خارجية (SQLite مدمج).

---

## 0. ما تحتاجه قبل البدء

- حساب على https://www.pythonanywhere.com
- اسم المستخدم في الحساب (سنرمز له بـ `USERNAME`) — **لا تكتبه حرفياً في أي ملف**،
  بل استبدله في الأوامر.
- ملف ZIP الخاص بالمشروع مرفوع، أو اتصال إنترنت في الـ Bash لنسخه من Git.

---

## 1. رفع المشروع

### الطريقة أ: رفع ملف ZIP
1. اضغط **Files** ← **Upload a file** وارفع `epson_repair_master_ultimate.zip`.
2. في **Bash** نفّذ:
   ```bash
   cd ~
   unzip epson_repair_master_ultimate.zip
   ls epson_repair_master
   ```

### الطريقة ب: من Git
```bash
cd ~
git clone https://github.com/USER/epson_repair_master.git
```

> بعد فك الضغط، مجلد المشروع يجب أن يكون: `/home/USERNAME/epson_repair_master`

---

## 2. إنشاء البيئة الافتراضية وتثبيت المتطلبات

```bash
cd ~/epson_repair_master
python3.11 -m venv ~/.virtualenvs/epsonrm
source ~/.virtualenvs/epsonrm/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

إن ظهرت مشكلة في تثبيت Pillow، يمكنك الاستغناء عنه:
```bash
pip install Flask Flask-SQLAlchemy Flask-WTF WTForms python-dotenv
```
(التطبيق يعمل بدونه، لكن لا تُولَّد صور مصغّرة للمرفوعات.)

---

## 3. ملف البيئة والمتغيرات السرية

```bash
cd ~/epson_repair_master
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # انسخ الناتج
nano .env
```

عدّل القيم الآتية (بمسارات **مطلقة** تبدأ بـ `/home/USERNAME/`):

```ini
SECRET_KEY=القيمة-العشوائية-الطويلة-التي-نسختها
FLASK_ENV=production
FLASK_DEBUG=false
DATA_DIR=/home/USERNAME/epson_repair_master/data
DATABASE_PATH=/home/USERNAME/epson_repair_master/data/epson_repair_master.db
UPLOAD_FOLDER=/home/USERNAME/epson_repair_master/private_uploads
BACKUP_FOLDER=/home/USERNAME/epson_repair_master/data/backups
SESSION_COOKIE_SECURE=true        # لأن PythonAnywhere يعمل عبر HTTPS
SESSION_COOKIE_SAMESITE=Lax
MAX_UPLOAD_MB=5
```

> ⚠️ لا ترفع ملف `.env` إلى Git ولا تضعه في ZIP عند مشاركة المشروع.

---

## 4. صلاحيات الكتابة (مهم جداً)

قاعدة البيانات ومجلد الرفع يجب أن يكونا قابلين للكتابة من عملية الويب
(التي تعمل بنفس مستخدم حسابك على PythonAnywhere):

```bash
mkdir -p ~/epson_repair_master/data/backups ~/epson_repair_master/private_uploads
chmod 755 ~/epson_repair_master/data ~/epson_repair_master/private_uploads
chmod 755 ~/epson_repair_master/data/backups
touch ~/epson_repair_master/data/epson_repair_master.db
chmod 664 ~/epson_repair_master/data/epson_repair_master.db
```

---

## 5. تهيئة قاعدة البيانات وإنشاء حساب المالك

```bash
cd ~/epson_repair_master
source ~/.virtualenvs/epsonrm/bin/activate
python3 run_local.py --create-admin     # تفاعلي: اسم مستخدم + كلمة مرور (10 أحرف فأكثر)
python3 run_local.py --init             # إنشاء الجداول + تحميل المحتوى التأسيسي
```

أو باستخدام أوامر Flask:
```bash
export FLASK_APP=wsgi.py
flask init-db
```

### إنشاء المالك بدون تفاعل (إن تعذّر الإدخال التفاعلي)
```bash
python3 tools/hash_password.py "كلمة-المرور-الخاصة"
ADMIN_USERNAME=your-admin ADMIN_PASSWORD_HASH=pbkdf2:sha256:... python3 tools/create_admin.py
```

---

## 6. إعداد تطبيق الويب في PythonAnywhere

1. اذهب إلى تبويب **Web** ← **Add a new web app** ← اختر **Manual configuration**
   ← اختر Python **3.11** (أو 3.10).
2. في صفحة التطبيق، تحت **Code**:
   - **Source code:** `/home/USERNAME/epson_repair_master`
   - **Working directory:** `/home/USERNAME/epson_repair_master`
   - **WSGI configuration file:** افتحه واستبدل محتواه بالكامل بـ:

     ```python
     # -*- coding: utf-8 -*-
     import os
     import sys

     path = "/home/USERNAME/epson_repair_master"
     if path not in sys.path:
         sys.path.insert(0, path)

     from dotenv import load_dotenv
     load_dotenv(os.path.join(path, ".env"))

     from wsgi import application  # noqa: E402
     ```

     > بديل أبسط: اجعل محتوى الملف:
     > `import sys; sys.path.insert(0, "/home/USERNAME/epson_repair_master"); from wsgi import application`
     >
     > واترك تحميل `.env` لملف `wsgi.py` في المشروع (يقوم بتحميله تلقائياً).

3. تحت **Virtualenv**، اكتب المسار الكامل:
   `/home/USERNAME/.virtualenvs/epsonrm`

4. تحت **Static files** أضف:
   | URL | Directory |
   |---|---|
   | `/static/` | `/home/USERNAME/epson_repair_master/static` |

   > لا تضف مجلد `private_uploads` كملفات ثابتة أبداً — محتواه خاص ويُقدَّم
   > عبر `/media/...` بعد التحقق من الجلسة فقط.

5. اضغط **Reload** أعلى الصفحة.

6. افتح `https://USERNAME.pythonanywhere.com` — يجب أن تظهر الصفحة الرئيسية بالعربية.
   لوحة الإدارة في `/admin` وتتطلب الدخول.

---

## 7. متغيرات البيئة من واجهة PythonAnywhere (بديل عن ملف .env)

تبويب **Web** ← قسم **Environment variables** أضف:

```
SECRET_KEY = قيمة-عشوائية-طويلة
FLASK_ENV = production
DATA_DIR = /home/USERNAME/epson_repair_master/data
UPLOAD_FOLDER = /home/USERNAME/epson_repair_master/private_uploads
BACKUP_FOLDER = /home/USERNAME/epson_repair_master/data/backups
SESSION_COOKIE_SECURE = true
```

تذكر الضغط على **Reload** بعد أي تغيير.

---

## 8. بعد كل تعديل على الملفات

- أي تعديل على ملفات `.py` أو القوالب: اضغط **Reload** في تبويب Web.
- أي تعديل على ملف `.env`: اضغط **Reload** أيضاً.
- لا حاجة لإعادة التهيئة بعد الـ Reload (قاعدة البيانات محفوظة على القرص).

---

## 9. استكشاف الأخطاء

| العرض | السبب المحتمل | الحل |
|---|---|---|
| خطأ 500 بعد الرفع | خطأ في مسار WSGI أو المتطلبات | افتح **Log files** ← **Error log** واقرأ آخر سطر |
| `unable to open database file` | مجلد `data` غير قابل للكتابة أو المسار خطأ | راجع الخطوة 4 وتأكد من `DATABASE_PATH` المطلق |
| الصفحة بلا تنسيق | مجلد static غير مضبوط | راجع الخطوة 6/4 |
| لا أستطيع الدخول | الحساب غير منشأ أو كلمة المرور خطأ | أعد `python3 run_local.py --create-admin` |
| القفل بعد محاولات فاشلة | 5 محاولات خاطئة | انتظر 10 دقائق أو امسح القفل: أنشئ كلمة مرور جديدة عبر `tools/create_admin.py` |
| رفع الصور يفشل | الحجم > 5MB أو النوع غير مسموح | صغّر الصورة؛ المسموح PNG/JPG/GIF/WEBP/BMP |

---

## 10. النسخ الاحتياطي على PythonAnywhere

من لوحة الإدارة داخل التطبيق: `/admin/backups` ← «إنشاء نسخة احتياطية» ← «تنزيل».
النسخة تُحفظ أيضاً في `/home/USERNAME/epson_repair_master/data/backups`.

لنسخ يدوي من Bash:
```bash
cd ~/epson_repair_master
zip -r ~/backup-manual-$(date +%F).zip data/epson_repair_master.db private_uploads
```
التفاصيل الكاملة في [BACKUP_RESTORE_AR.md](BACKUP_RESTORE_AR.md).

---

## 11. ملاحظات أمنية للنشر

- فعّل `SESSION_COOKIE_SECURE=true` لأن الموقع يعمل عبر HTTPS.
- لا تجعل مجلد `private_uploads` أو `data` قابلاً للتصفح.
- غيّر كلمة المرور دورياً من `/auth/change-password`.
- لا تشارك ملف `.env` ولا النسخ الاحتياطية (تحتوي قاعدة البيانات كاملة).
