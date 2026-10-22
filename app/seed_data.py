# -*- coding: utf-8 -*-
"""البيانات التأسيسية: التصنيفات، الموديلات، المراجع، الأعراض، قواعد التشخيص، الصور المرفقة.

قواعد التوثيق:
    - كل معلومة تقنية مرفقة بمصدرها إن وُجد.
    - ما لم يتحقق يُوسم بـ confidence="unverified" ويُعرض كاحتمال لا كحقيقة.
    - لا توجد أرقام قطع أو قيم كهربائية من تأليف المشروع.
"""
from __future__ import annotations

DISCLAIMER_DIAGRAM = (
    "رسم توضيحي غير مطابق بالضرورة للبنية الداخلية الدقيقة. "
    "الغرض توضيح المبدأ العام فقط ولا يُستخدم كدليل خدمة أصلي."
)

# ------------------------------------------------------------------ التصنيفات
CATEGORIES = [
    {"slug": "power", "name_ar": "التشغيل والطاقة", "name_en": "Power & Startup",
     "description": "أعطال الإقلاع، انقطاع الطاقة، المؤشرات، لوحة التحكم.", "icon": "power",
     "sort_order": 10},
    {"slug": "print_quality", "name_ar": "الطباعة وجودة المخرجات", "name_en": "Print Quality",
     "description": "الطباعة الباهتة، النقاط المفقودة، الخطوط غير الطبيعية، الشريط الحبري.",
     "icon": "print", "sort_order": 20},
    {"slug": "paper_feed", "name_ar": "الورق والتغذية", "name_en": "Paper Handling",
     "description": "عدم السحب، الانحشار، الانحراف، الورق المستمر، إعدادات الورق.",
     "icon": "paper", "sort_order": 30},
    {"slug": "mechanics", "name_ar": "الحركة والآليات الميكانيكية", "name_en": "Mechanics",
     "description": "عربة رأس الطباعة، الأصوات غير الطبيعية، الأحزمة والتروس والمستشعرات.",
     "icon": "gear", "sort_order": 40},
    {"slug": "connectivity", "name_ar": "الاتصال والتحكم", "name_en": "Connectivity",
     "description": "التعريف على الكمبيوتر، USB/المنفذ المتوازي، التعريفات، طابور الطباعة.",
     "icon": "usb", "sort_order": 50},
    {"slug": "settings", "name_ar": "الإعدادات ومؤشرات الحالة", "name_en": "Settings & Indicators",
     "description": "تفسير المؤشرات، إعدادات الورق والسرعة، الاختبار الذاتي، إعادة الضبط.",
     "icon": "sliders", "sort_order": 60},
    {"slug": "preventive", "name_ar": "الصيانة الوقائية", "name_en": "Preventive Maintenance",
     "description": "التنظيف المسموح، فحص الشريط والورق، الجدول الدوري، التخزين والنقل.",
     "icon": "shield", "sort_order": 70},
    {"slug": "electrical", "name_ar": "الأعطال الكهربائية والإلكترونية",
     "name_en": "Electrical & Electronic",
     "description": "فحص خارجي آمن فقط، وحدود التوقف والإحالة إلى فني مؤهل.",
     "icon": "bolt", "sort_order": 80},
    {"slug": "compound", "name_ar": "الأعطال المركبة", "name_en": "Compound Faults",
     "description": "حالات متعددة الأسباب، أعطال متقطعة، أعطال بعد التنظيف أو النقل.",
     "icon": "layers", "sort_order": 90},
]

# ------------------------------------------------------------------ الموديلات
MODELS = [
    {
        "slug": "epson-lx-350",
        "name_ar": "Epson LX-350",
        "name_en": "Epson LX-350",
        "brand": "Epson",
        "printer_class": "طابعة نقطية 9 إبر — 80 عموداً",
        "pins": "9 إبر",
        "columns": "80 عموداً",
        "interfaces": "منفذ متوازي ثنائي الاتجاه، USB 2.0، RS-232 (تسلسلي)",
        "ribbon_part": "C13S015637 (S015637)",
        "ribbon_part_confidence": "user_manual",
        "mtbf": "10,000 ساعة تشغيل",
        "print_head_life": "400 مليون ضربة/إبرة",
        "memory": "128 كيلوبايت",
        "paper_paths": "ورق مفرد من الخلف، ورق مستمر من الخلف، إخراج من الخلف",
        "summary": (
            "طابعة نقطية مدمجة بـ 9 إبر و80 عموداً، مخصصة للتطبيقات المكتبية التي تستخدم "
            "الورق المستمر أو النماذج متعددة النسخ. تتميز باستهلاك منخفض للطاقة وعمر شريط "
            "مرتفع نسبياً، وتعمل بمحاكاة ESC/P وIBM PPDS."
        ),
        "specs_note": (
            "المواصفات أعلاه مأخوذة من صفحة منتج Epson الرسمية (Epson UK) لطراز LX-350، "
            "ورقم الشريط من صفحة ملحق Epson الرسمية. لا يدّعي هذا المشروع امتلاك دليل خدمة "
            "أصلي للطراز؛ لذلك كل إجراء داخلي في الموسوعة موسوم بمستوى ثقته ومصدره."
        ),
        "sort_order": 10,
    },
    {
        "slug": "epson-fx-890",
        "name_ar": "Epson FX-890",
        "name_en": "Epson FX-890",
        "brand": "Epson",
        "printer_class": "طابعة نقطية 9 إبر (18 إبرة: 2 × 9) — 80 عموداً",
        "pins": "18 إبرة (2 × 9)",
        "columns": "80 عموداً",
        "interfaces": "USB متوافق مع USB 2.0، منفذ متوازي ثنائي الاتجاه",
        "ribbon_part": "C13S015329 (S015329)",
        "ribbon_part_confidence": "user_manual",
        "mtbf": "غير مؤكد للجيل الأول (الجيل الثاني FX-890II: 25,000 ساعة)",
        "print_head_life": "400 مليون ضربة/إبرة (حسب صفحة FX-890II الرسمية)",
        "memory": "128 كيلوبايت (حسب صفحة FX-890II الرسمية)",
        "paper_paths": (
            "ورق مفرد من الأمام والخلف، ورق مستمر من الأمام والخلف، إخراج من الخلف "
            "(حسب صفحة FX-890II الرسمية)"
        ),
        "summary": (
            "طابعة نقطية بـ 9 إبر مخصصة للأحمال العالية، تدعم حتى 6 نسخ كربونية مع الأصل، "
            "وتوفّر تغذية أمامية وخلفية. تستخدم محاكاة ESC/P وIBM PPDS وتدعم خطوطاً ورموز "
            "شريطية متعددة."
        ),
        "specs_note": (
            "بعض المواصفات (عدد الإبر 18، مسارات التغذية الأمامية والخلفية، سعة النسخ) "
            "مأخوذة من صفحة منتج Epson الرسمية لطراز FX-890II(N) لأنها الصفحة المتاحة "
            "للتحقق. قد تختلف قيم الجيل الأول FX-890؛ لذلك تُعرض هذه الحقول مع تنبيه "
            "بضرورة التحقق من دليل المستخدم المرفق مع الجهاز قبل الاعتماد عليها في قرار "
            "فني. رقم الشريط C13S015329 مأخوذ من صفحة ملحق Epson الرسمية المخصصة لـ "
            "FX-890 / FX-890A."
        ),
        "sort_order": 20,
    },
]

# ------------------------------------------------------------------ المراجع
REFERENCES = [
    {"title": "صفحة منتج Epson LX-350 الرسمية (المواصفات التقنية)",
     "url": "https://www.epson.co.uk/en_GB/products/printers/dot-matrix/lx-350-dot-matrix-printer/p/11849",
     "publisher": "Epson", "ref_type": "spec_sheet", "model": "epson-lx-350", "verified": True,
     "notes": "مصدر المواصفات: عدد الإبر، الأعمدة، الواجهات، الاستهلاك، MTBF، عمر رأس الطباعة."},
    {"title": "شريط الحبر الأصلي لطابعات LX-350/LX-300/+/+II (C13S015637)",
     "url": "https://www.epson.co.uk/en_GB/products/ink-and-paper/ink-ribbons/sidm-black-ribbon-cartridge-for-lx-350-lx-300-%2B-%2Bii-%28c13s015637%29/p/11851",
     "publisher": "Epson", "ref_type": "spec_sheet", "model": "epson-lx-350", "verified": True,
     "notes": "مصدر رقم قطعة الشريط الحبري."},
    {"title": "صفحة منتج Epson FX-890IIN الرسمية (المواصفات التقنية)",
     "url": "https://www.epson.de/de_DE/produkte/drucker/dot-matrix/fx-890iin/p/21462",
     "publisher": "Epson", "ref_type": "spec_sheet", "model": "epson-fx-890", "verified": True,
     "notes": "مصدر جزئي لمواصفات سلسلة FX-890. الجيل الأول قد يختلف في بعض القيم."},
    {"title": "شريط الحبر الأصلي لـ FX-890 / FX-890A (C13S015329)",
     "url": "https://www.epson.de/de_DE/produkte/drucker/dot-matrix/fx-890iin/p/21462",
     "publisher": "Epson", "ref_type": "spec_sheet", "model": "epson-fx-890", "verified": True,
     "notes": "رقم الشريط كما يظهر في قسم الملحقات بصفحة منتج Epson لسلسلة FX-890II(N)."},
    {"title": "Epson — دعم الطابعات النقطية (مركز التحميل والأدلة)",
     "url": "https://epson.com/Support/Printers/Dot-Matrix-Printers",
     "publisher": "Epson", "ref_type": "user_guide", "model": None, "verified": False,
     "notes": "صفحة عامة: يجب تنزيل دليل المستخدم الخاص بالطراز والمنطقة للحصول على "
              "إجراءات لوحة التحكم والاختبار الذاتي الدقيقة."},
    {"title": "حامل لفة ورق A4 لسلسلة LX-350/300+II/1170II وFX-890 وغيرها (C12C811141)",
     "url": "https://www.epson.co.uk/en_GB/products/options/sidm-a4-paper-roll-holder-for-lx-350-300%2Bii-1170ii%2C-fx-890%2C-fx-890a%2C-fx-2190%2C-lq-690-350-300%2Bii-series/p/934",
     "publisher": "Epson", "ref_type": "spec_sheet", "model": None, "verified": True,
     "notes": "ملحق مشترك بين الطرازين؛ مفيد عند تشخيص مشكلات تغذية اللفات."},
]

# ------------------------------------------------------------------ الأعراض
# (slug, الاسم بالعربية, الاسم بالإنجليزية, التصنيف, كلمات بديلة/أخطاء إملائية شائعة)
SYMPTOMS = [
    ("power-none", "الطابعة لا تعمل إطلاقاً", "No power at all", "power",
     "لا تفتح ما تشتغل لا تعمل ميتة كهرباء باور"),
    ("power-intermittent", "انقطاع أو تذبذب التشغيل", "Intermittent power", "power",
     "تطفي تفصل تتوقف فجأة متقطع"),
    ("led-off", "مؤشر الطاقة لا يضيء", "Power LED off", "power", "لمبة الليد ما تضيء"),
    ("stops-mid-job", "توقف الطابعة أثناء العمل", "Stops during printing", "power",
     "توقف نص الصفحة تتوقف اثناء الطباعه"),
    ("panel-buttons", "أزرار لوحة التحكم لا تستجيب", "Control panel buttons dead", "power",
     "الازرار لا تعمل لوحة التحكم"),
    ("blank-output", "الورق يخرج دون طباعة", "Blank pages", "print_quality",
     "بيضاء فاضية ما تكتب تخرج بيضا"),
    ("faint-print", "الطباعة باهتة أو غير متساوية", "Faint / uneven print", "print_quality",
     "خفيفه باهته غير واضحه"),
    ("missing-dots", "اختفاء نقاط أو خطوط من الحروف", "Missing dots", "print_quality",
     "ناقص نقاط مقطعة حروف"),
    ("distorted-chars", "أحرف ناقصة أو مشوهة", "Missing / distorted characters",
     "print_quality", "حروف مشوهه مكسوره غريبه"),
    ("lines-abnormal", "خطوط أفقية أو عمودية غير طبيعية", "Abnormal lines", "print_quality",
     "خطوط خط طولي عرضي"),
    ("repeated-chars", "تكرار الأحرف أو انزياح الطباعة", "Repeated / shifted characters",
     "print_quality", "تكرار مزدوج ازاحه انزياح"),
    ("print-position", "الطباعة لا تطابق موضع النص", "Wrong print position", "print_quality",
     "مكان غلط موضع الطباعه"),
    ("density-ribbon", "مشكلات كثافة الطباعة والشريط", "Ribbon density issues", "print_quality",
     "شريط الحبر كثافه"),
    ("head-pins", "اشتباه في رأس الطباعة أو الإبر", "Print head / pins issue", "print_quality",
     "راس الطباعه ابر ابره"),
    ("no-paper-feed", "عدم سحب الورق", "Paper not feeding", "paper_feed",
     "ما تسحب الورق لا يدخل الورق"),
    ("paper-jam", "انحشار الورق", "Paper jam", "paper_feed", "ورق معلق جيم انحشار"),
    ("paper-skew", "انحراف الورق أو دخوله بزاوية", "Paper skew", "paper_feed",
     "مايل مائل زاويه"),
    ("tractor-issues", "مشكلات الورق المستمر والثقوب الجانبية", "Tractor feed issues",
     "paper_feed", "التراكتور الثقوب الجانبيه الورق المستمر"),
    ("release-path", "مشكلات تحرير الورق أو تغيير المسار", "Paper release / path switch",
     "paper_feed", "تحرير الورق تغيير المسار"),
    ("carriage-stuck", "عربة رأس الطباعة لا تتحرك", "Carriage stuck", "mechanics",
     "العربة ما تتحرك راس الطباعه واقف"),
    ("noise", "صوت احتكاك أو طرق غير طبيعي", "Abnormal noise", "mechanics",
     "صوت طرقه صرير احتكاك"),
    ("debris", "تراكم أوساخ أو أجسام غريبة", "Debris / contamination", "mechanics",
     "اوساخ غبار جسم غريب"),
    ("not-detected", "الكمبيوتر لا يتعرف على الطابعة", "Printer not detected", "connectivity",
     "ما يتعرف عليها مش متعرفه"),
    ("usb-fail", "تعذر الطباعة عبر USB", "USB printing failure", "connectivity",
     "يو اس بي USB ما يطبع"),
    ("port-settings", "إعدادات المنفذ غير الصحيحة", "Wrong port settings", "connectivity",
     "المنفذ بورت LPT"),
    ("driver-os", "مشكلات التعريف ونظام التشغيل", "Driver / OS issues", "connectivity",
     "التعريف درايفر ويندوز"),
    ("job-no-response", "مهمة الطباعة لا تستجيب", "Print job no response", "connectivity",
     "ارسلت وما طبعت"),
    ("app-specific", "الطباعة من برنامج دون آخر", "Prints from one app only", "connectivity",
     "برنامج معين وورد"),
    ("spooler", "مشكلات الطابور والذاكرة المؤقتة", "Spooler / buffer issues", "connectivity",
     "الطابور spooler معلقه"),
    ("indicators-beep", "مؤشرات أو أنماط صوتية غير مفهومة", "Indicators / beeps", "settings",
     "لمبات تومض صفاره بيب"),
    ("settings-general", "إعدادات الورق أو السرعة أو الخطوط", "Printer settings", "settings",
     "اعدادات سرعه خط"),
    ("self-test", "الاختبار الذاتي للطباعة", "Self test", "settings", "تست ذاتي سيلف تست"),
    ("reset", "إعادة الضبط أو استعادة الإعدادات", "Reset / defaults", "settings",
     "ريست ضبط المصنع"),
    ("preventive-cleaning", "التنظيف الدوري", "Routine cleaning", "preventive",
     "تنظيف صيانه"),
    ("ribbon-issue", "مشكلة في شريط الحبر", "Ribbon problem", "preventive", "شريط الحبر"),
    ("wear", "علامات تآكل مبكرة", "Early wear signs", "preventive", "تاكل استهلاك"),
    ("electrical", "اشتباه في مصدر الطاقة أو اللوحة", "Power supply / board suspicion",
     "electrical", "كهرباء لوحة دخان ريحه حرق"),
]

# ------------------------------------------------------------------ أسئلة المعالج
# trigger: slug العرض المحفّز أو None (سؤال عام)
QUESTIONS = [
    {
        "slug": "q-power-outlet", "trigger": "power-none", "model": None, "sort": 10,
        "text": "هل تم التحقق من أن مقبس الكهرباء يعمل بجهاز آخر؟",
        "help": "استخدم مصباحاً أو شاحناً للتأكد من المقبس قبل لمس الطابعة.",
        "options": [
            ("المقبس لا يعمل (لا كهرباء)", {"no-power-complete": 2, "safe-external-cable-check": 2}),
            ("المقبس يعمل والطابعة لا تستجيب", {"no-power-complete": 2, "safe-external-cable-check": 1}),
            ("لم أتحقق بعد", {"safe-external-cable-check": 3}),
        ],
    },
    {
        "slug": "q-power-cable", "trigger": "power-none", "model": None, "sort": 20,
        "text": "هل كابل الطاقة موصول بإحكام من الطرفين وسليم ظاهرياً؟",
        "help": "فحص خارجي فقط: لا تفتح غطاء مزود الطاقة.",
        "options": [
            ("الكابل تالف أو مرتخٍ أو غير أصلي", {"safe-external-cable-check": 3, "no-power-complete": 2}),
            ("الكابل سليم وموصول جيداً", {"control-board-power-supply-triage": 2, "no-power-complete": 1}),
        ],
    },
    {
        "slug": "q-power-led", "trigger": "led-off", "model": None, "sort": 30,
        "text": "هل يصدر عن الطابعة أي صوت أو حركة عند التشغيل؟",
        "help": "صوت المراوح أو حركة العربة مؤشر على وصول الطاقة للوحة التحكم.",
        "options": [
            ("لا صوت ولا حركة إطلاقاً", {"no-power-complete": 2, "control-board-power-supply-triage": 2}),
            ("توجد حركة أو صوت لكن لا طباعة", {"control-panel-buttons-unresponsive": 2, "print-job-no-response": 1}),
        ],
    },
    {
        "slug": "q-ribbon-age", "trigger": "faint-print", "model": None, "sort": 40,
        "text": "ما حالة شريط الحبر؟",
        "help": "الشريط الجاف أو المستهلك هو السبب الأكثر شيوعاً للطباعة الباهتة.",
        "options": [
            ("قديم / مستخدم لفترة طويلة", {"ribbon-density-issues": 3, "faint-uneven-print": 2}),
            ("جديد ولكن الطباعة باهتة", {"ribbon-inspection-installation": 3, "faint-uneven-print": 2}),
            ("غير متأكد", {"ribbon-density-issues": 1, "faint-uneven-print": 1}),
        ],
    },
    {
        "slug": "q-faint-pattern", "trigger": "faint-print", "model": None, "sort": 50,
        "text": "هل البهتان منتظم على كامل السطر أم يظهر في مناطق محددة؟",
        "help": "البهتان الموضعي غالباً سببه مسار الورق أو الشريط غير المركب جيداً.",
        "options": [
            ("منتظم على كامل السطر", {"ribbon-density-issues": 2, "print-head-pins-limits": 1}),
            ("يظهر في جهة واحدة أو على شكل بقع", {"faint-uneven-print": 2, "ribbon-inspection-installation": 2,
                                                  "abnormal-horizontal-vertical-lines": 1}),
        ],
    },
    {
        "slug": "q-missing-dots", "trigger": "missing-dots", "model": None, "sort": 60,
        "text": "هل النقاط المفقودة ثابتة في نفس المواقع على كل الصفحات؟",
        "help": "غياب نقطة في نفس الموضع دائماً يشير غالباً إلى إبرة أو مسار حبر؛ "
                "أما النقاط المتغيرة فغالباً شريط أو ورق.",
        "options": [
            ("نفس المواقع دائماً", {"print-head-pins-limits": 3, "missing-dots-lines": 2}),
            ("مواقع متغيرة أو عشوائية", {"ribbon-density-issues": 2, "missing-dots-lines": 2,
                                         "abnormal-horizontal-vertical-lines": 1}),
        ],
    },
    {
        "slug": "q-copies", "trigger": "faint-print", "model": None, "sort": 70,
        "text": "هل تستخدم ورقاً متعدد النسخ (كربون)؟",
        "help": "مع النسخ المتعددة يلزم رفع كثافة الطباعة وضبط مسافة رأس الطباعة.",
        "options": [
            ("نعم، عدة نسخ", {"ribbon-density-issues": 2, "paper-settings-mismatch": 2}),
            ("لا، ورقة واحدة", {"faint-uneven-print": 1}),
        ],
    },
    {
        "slug": "q-paper-type", "trigger": "no-paper-feed", "model": None, "sort": 80,
        "text": "أي نوع ورق تستخدمه الآن؟",
        "help": "تحديد نوع الورق يحدد مسار التغذية الصحيح وإعدادات الطابعة.",
        "options": [
            ("ورق مفرد (A4)", {"paper-not-feeding": 2, "paper-release-path-switch": 1}),
            ("ورق مستمر ذو ثقوب جانبية", {"continuous-paper-tractor": 3, "paper-not-feeding": 1}),
            ("لفة ورق", {"paper-settings-mismatch": 2}),
        ],
    },
    {
        "slug": "q-feed-sound", "trigger": "no-paper-feed", "model": None, "sort": 90,
        "text": "هل تسمع صوت محرك التغذية عند إرسال مهمة الطباعة؟",
        "help": "صوت المحرك يعني أن الأمر يصل للمحرك والمشكلة غالباً ميكانيكية أو في الورق.",
        "options": [
            ("نعم، يوجد صوت ولا يدخل الورق", {"paper-not-feeding": 2, "abnormal-noise": 1}),
            ("لا يوجد أي صوت", {"paper-not-feeding": 1, "carriage-not-moving": 1,
                                "print-job-no-response": 2}),
        ],
    },
    {
        "slug": "q-jam-location", "trigger": "paper-jam", "model": None, "sort": 100,
        "text": "أين يتوقف الورق بالتحديد؟",
        "help": "موضع التوقف يحدد الجزء المشتبه به.",
        "options": [
            ("عند المدخل قبل الدخول", {"paper-not-feeding": 2, "paper-jam": 2}),
            ("في منتصف المسار", {"paper-jam": 3, "debris-contamination": 2}),
            ("عند الخرج بعد الطباعة", {"paper-release-path-switch": 2, "paper-jam": 2}),
        ],
    },
    {
        "slug": "q-carriage-free", "trigger": "carriage-stuck", "model": None, "sort": 110,
        "text": "هل تتحرك العربة يدوياً بسلاسة عند إطفاء الطابعة؟",
        "help": "افصل الطابعة عن الكهرباء أولاً قبل أي لمس للعربة.",
        "options": [
            ("تتحرك بسلاسة", {"carriage-not-moving": 1, "printer-stops-mid-job": 1}),
            ("مقاومة أو عالقة أو توقف مفاجئ", {"intermittent-carriage-motion": 3,
                                               "abnormal-noise": 2, "debris-contamination": 2}),
        ],
    },
    {
        "slug": "q-interface", "trigger": "not-detected", "model": None, "sort": 120,
        "text": "أي واجهة تستخدم للتوصيل؟",
        "help": "الواجهة تحدد خطوات الفحص الصحيحة.",
        "options": [
            ("USB", {"pc-not-detecting-printer": 2, "usb-print-failure": 3}),
            ("منفذ متوازي (Parallel/LPT)", {"wrong-port-settings": 3, "pc-not-detecting-printer": 1}),
            ("منفذ تسلسلي أو شبكة (إن وُجد)", {"wrong-port-settings": 2,
                                               "fx890-interface-selection": 2,
                                               "lx350-interface-selection": 2}),
        ],
    },
    {
        "slug": "q-other-device", "trigger": "not-detected", "model": None, "sort": 130,
        "text": "هل جرّبت كابلاً أو منفذ كمبيوتر آخر؟",
        "help": "استبعاد الكابل والمنفذ قبل التشكيك في لوحة الطابعة.",
        "options": [
            ("نعم ولا تزال المشكلة", {"pc-not-detecting-printer": 2, "driver-os-compatibility": 2}),
            ("لا، لم أجرّب بعد", {"safe-external-cable-check": 3}),
        ],
    },
    {
        "slug": "q-self-test", "trigger": "blank-output", "model": None, "sort": 140,
        "text": "هل يعمل الاختبار الذاتي للطابعة (إن كان متاحاً لديك)؟",
        "help": "الاختبار الذاتي يفصل بين مشكلة الطابعة ومشكلة الكمبيوتر.",
        "options": [
            ("الاختبار الذاتي يطبع بشكل سليم", {"print-job-no-response": 3,
                                                "driver-os-compatibility": 2,
                                                "spooler-buffer-issues": 2}),
            ("الاختبار الذاتي لا يطبع أو باهت", {"blank-paper-no-print": 3,
                                                 "ribbon-density-issues": 2,
                                                 "print-head-pins-limits": 1}),
            ("لا أعرف كيف أشغّله", {"self-test-procedure": 3}),
        ],
    },
    {
        "slug": "q-after-service", "trigger": None, "model": None, "sort": 150,
        "text": "هل ظهرت المشكلة بعد تنظيف أو تغيير شريط أو نقل الطابعة؟",
        "help": "كثير من الأعطال المتكررة تظهر مباشرة بعد تدخل صيانة غير مكتمل.",
        "options": [
            ("نعم، بعد تنظيف أو تغيير الشريط", {"fault-after-cleaning-or-ribbon": 4,
                                                 "ribbon-inspection-installation": 2}),
            ("نعم، بعد نقل أو تخزين الطابعة", {"fault-after-moving-printer": 4}),
            ("لا، ظهرت أثناء التشغيل العادي", {"intermittent-faults": 1}),
        ],
    },
    {
        "slug": "q-intermittent", "trigger": None, "model": None, "sort": 160,
        "text": "هل تتكرر المشكلة في أوقات محددة أم عشوائياً؟",
        "help": "الانتظام يرتبط غالباً بالحرارة أو الحمل أو مصدر الطاقة.",
        "options": [
            ("بعد فترة تشغيل طويلة أو مع الحمل العالي", {"printer-stops-mid-job": 2,
                                                          "intermittent-power-loss": 2}),
            ("عشوائياً تماماً", {"intermittent-faults": 3}),
        ],
    },
    {
        "slug": "q-electrical", "trigger": "electrical", "model": None, "sort": 170,
        "text": "هل توجد رائحة احتراق أو دخان أو سخونة غير طبيعية؟",
        "help": "في هذه الحالة أوقف التشغيل فوراً ولا تكمل أي فحص.",
        "options": [
            ("نعم", {"when-to-stop-electrical": 5, "control-board-power-supply-triage": 2}),
            ("لا", {"safe-external-cable-check": 2, "control-board-power-supply-triage": 1}),
        ],
    },
]

# ------------------------------------------------------------------ الصور المرفقة (مخططات توضيحية)
BUNDLED_IMAGES = [
    {"title": "مخطط توضيحي: مسار الورق — Epson LX-350",
     "description": DISCLAIMER_DIAGRAM + " يوضح مبدأ دخول الورق من الخلف ومروره فوق الأسطوانة "
                    "ثم الخروج من الخلف.",
     "model": "epson-lx-350", "filename": "diagrams/paper_path_lx350.svg",
     "image_type": "diagram", "is_original": False,
     "source": "رسم توضيحي (SVG) أنتج داخل المشروع", "license_note": "أصل للمشروع — توضيحي",
     "step_hint": "مسار الورق"},
    {"title": "مخطط توضيحي: مسار الورق — Epson FX-890",
     "description": DISCLAIMER_DIAGRAM + " يوضح مبدأ وجود مساري تغذية (أمامي وخلفي) في طابعات "
                    "سلسلة FX-890، ويجب تأكيد التفاصيل من دليل المستخدم.",
     "model": "epson-fx-890", "filename": "diagrams/paper_path_fx890.svg",
     "image_type": "diagram", "is_original": False,
     "source": "رسم توضيحي (SVG) أنتج داخل المشروع", "license_note": "أصل للمشروع — توضيحي",
     "step_hint": "مسار الورق"},
    {"title": "مخطط توضيحي: رأس الطباعة وعربة الحركة",
     "description": DISCLAIMER_DIAGRAM + " يوضح مبدأ حركة عربة رأس الطباعة على قضيب التوجيه "
                    "أفقّياً أثناء الطباعة.",
     "model": None, "filename": "diagrams/print_head_carriage.svg",
     "image_type": "diagram", "is_original": False,
     "source": "رسم توضيحي (SVG) أنتج داخل المشروع", "license_note": "أصل للمشروع — توضيحي",
     "step_hint": "رأس الطباعة"},
    {"title": "مخطط توضيحي: آلية الشريط الحبري",
     "description": DISCLAIMER_DIAGRAM + " يوضح مبدأ مرور الشريط بين رأس الطباعة والورق وحركة "
                    "لفّه المستمرة.",
     "model": None, "filename": "diagrams/ribbon_mechanism.svg",
     "image_type": "diagram", "is_original": False,
     "source": "رسم توضيحي (SVG) أنتج داخل المشروع", "license_note": "أصل للمشروع — توضيحي",
     "step_hint": "الشريط الحبري"},
    {"title": "مخطط توضيحي: نقاط التنظيف والصيانة المسموح بها",
     "description": DISCLAIMER_DIAGRAM + " يوضح الأجزاء الخارجية التي يُسمح بتنظيفها عادةً "
                    "والأجزاء التي تتطلب فنياً.",
     "model": None, "filename": "diagrams/cleaning_points.svg",
     "image_type": "diagram", "is_original": False,
     "source": "رسم توضيحي (SVG) أنتج داخل المشروع", "license_note": "أصل للمشروع — توضيحي",
     "step_hint": "التنظيف"},
    {"title": "مخطط توضيحي: لوحة التحكم (هيكل عام)",
     "description": DISCLAIMER_DIAGRAM + " تخطيط لوحة التحكم يختلف بين الطرازين؛ تحقق من دليل "
                    "المستخدم قبل الاعتماد على أي زر أو مؤشر.",
     "model": None, "filename": "diagrams/control_panel.svg",
     "image_type": "panel", "is_original": False,
     "source": "رسم توضيحي (SVG) أنتج داخل المشروع", "license_note": "أصل للمشروع — توضيحي",
     "step_hint": "لوحة التحكم"},
    {"title": "صورة بديلة: الصورة الفنية لهذا الجزء غير متاحة بعد",
     "description": "يُستخدم هذا العنصر مكان أي صورة فنية لم يتوفر لها مصدر موثوق أو ترخيص "
                    "مناسب. لا نختلق صوراً للموديل.",
     "model": None, "filename": "diagrams/unavailable.svg",
     "image_type": "diagram", "is_original": False,
     "source": "عنصر نائب داخل المشروع", "license_note": "أصل للمشروع",
     "step_hint": "بديل الصورة غير المتاحة"},
]
