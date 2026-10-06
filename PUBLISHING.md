<div dir="rtl">

# دليل النشر على GitHub (DULE — RE4 Classic Trainer)

هذا الملف يشرح **بالضبط** كيف يُرفع المشروع، كيف يُنشر الموقع، كيف يُنزَّل ملف الـ exe،
وما هو مجاني وما الذي يطلب دفع (اختياري بالكامل).

---

## 1) الأدوات المطلوبة (مرة واحدة فقط)

| الأداة | الأمر للتأكد | ملاحظة |
|---|---|---|
| Git | `git --version` | لازم يكون مثبّت |
| GitHub CLI | `gh --version` | السكربتات تستخدمه للإنشاء والنشر |

تسجيل الدخول (مرة واحدة فقط — بعدها يتذكّر الحساب):

```bat
gh auth login
:: اختر: GitHub.com → HTTPS → Login with a web browser
```

للتحقق:

```bat
gh auth status
```

---

## 2) رفع المشروع (أول مرة)

من داخل مجلد المشروع:

```bat
git init -b main
git config user.name "ABO 3MAD"
git config user.email "اسمك@users.noreply.github.com"
git add -A
git commit -m "أول نسخة"
gh repo create re4-classic-trainer --public --source=. --remote=origin --push
```

النتيجة: مستودع عام على `https://github.com/<حسابك>/re4-classic-trainer`

> **مهم:** خَلّ المستودع **Public**. لو صار Private يتوقّف الموقع وتتوقف روابط التحميل للآخرين.

---

## 3) إنشاء رابط تحميل (Release)

ملف الـ exe **لا يُرفع داخل الكود** — يُرفع كـ **Release Asset** (مخزن منفصل، بلا حد باندويث).
ابنِ البرنامج أولاً:

```bat
build_exe.bat
```

ثم:

```bat
gh release create v1.0.0 "dist\RE4ClassicTrainer.exe#RE4ClassicTrainer.exe" ^
  --title "DULE RE4 Classic Trainer v1.0" ^
  --notes "أول إصدار: سكنات لبدلتين، بعث فوري، شيك بوينت، نسخ احتياطية."
```

رابط التحميل الثابت يصير بهذا الشكل:

```
https://github.com/<حسابك>/<الريبو>/releases/download/v1.0.0/RE4ClassicTrainer.exe
```

رابط دائم لكل الأجهزة (يجي أحدث نسخة تلقائياً):

```
https://github.com/<حسابك>/<الريبو>/releases/latest
```

---

## 4) نشر الموقع (GitHub Pages)

الموقع في مجلد `website/`. انشره على فرع مستقل اسمه `gh-pages`:

```bat
git subtree push --prefix website origin gh-pages
```

ثم فعّل Pages مرة واحدة (لو ما اشتغل تلقائياً):

```bat
gh api --method POST repos/<حسابك>/<الريبو>/pages ^
  -f "source[branch]=gh-pages" -f "source[path]=/"
```

رابط الموقع:

```
https://<حسابك>.github.io/<الريبو>/
```

### تحديث الموقع لاحقاً (كل مرة تعدّل الموقع)

```bat
git add -A
git commit -m "update website"
git push                                :: حدّث الكود
git subtree push --prefix website origin gh-pages   :: حدّث الموقع المنشور
```

خلال دقيقة يصير الموقع محدّث.

---

## 5) المجانية — بالتفصيل الرسمي

### ✅ مجاني دائماً (بلا بطاقة بنكية أبداً)

| الخدمة | الحد المجاني |
|---|---|
| **المستودعات** | بلا حد للعامة والخاصة |
| **GitHub Pages** (من مستودع عام) | موقع بحجم **1 جيجا** · باندويث **100 جيجا/شهر** (حد "لطيف" = soft) · **10 نشرات/ساعة** |
| **Releases (ملف exe)** | كل ملف **أقل من 2 جيجا** · حتى **1000 ملف** في الإصدار · **بلا حد على الباندويث ولا الحجم الكلي** |
| **حجم المستودع الموصى به** | 1 جيجا (مستودعك الآن أقل من 1 ميجا!) |

**معنى "soft limit":** لو تجاوزته، GitHub **ما يخصم فلوس ولا يطلب دفع** — يجيك إيميل يقترح تحسينات
(أو يستخدم CDN)، وفي أسوأ حالات نادرة يوقف تقديم الموقع مؤقتاً.

### 💳 يطلب دفع فقط لو اخترت أنت (كلها غير ضرورية لك)

| الحالة | التكلفة | الحل المجاني |
|---|---|---|
| تبي الموقع من مستودع **خاص** | GitHub **Pro** ≈ 4$ شهرياً | خلّ المستودع **عام** |
| تبي **دومين** باسمك مثل `dule.com` | تشتريه من مزوّد ≈ 10–15$ **بالسنة** | استخدم `zxwxg.github.io/...` مجاناً |
| ملفات ضخمة جداً (> 100 ميجا) داخل الكود عبر **Git LFS** | 1 جيجا مجاناً ثم مدفوع | ارفع الملفات الكبيرة كـ **Release** (مجاني بلا حد) |
| دقائق **Actions** إضافية (للمستودعات الخاصة) | مدفوعة | المستودع العام = بلا حد فعلي |
| **Copilot / Codespaces / Sponsors** | مدفوعة | غير مستخدمة أصلاً |

### 🚫 الحالة الوحيدة اللي يُستبعد فيها الاستخدام

سياسة GitHub: **GitHub Pages ليس لاستخدامه كاستضافة تجارية** (متجر/خدمة SaaS مدفوعة).
موقعك التعريفي + روابط تحميل مجانية = استخدام طبيعي مئة بالمئة.

---

## 6) ملخّص سريع (ورقة واحدة)

```text
الكود        → github.com/zxwxg/re4-classic-trainer          (مجاني، عام)
الموقع       → zxwxg.github.io/re4-classic-trainer/          (مجاني دائم)
التحميل      → github.com/.../releases/download/v1.0.0/RE4ClassicTrainer.exe  (مجاني بلا حد باندويث)
التكلفة      → 0$
متى أدفع؟    → فقط لو أبغى مستودع خاص (4$)، أو دومين مخصص، أو LFS
```

---

## 7) مشاكل شائعة

| المشكلة | السبب | الحل |
|---|---|---|
| `gh: command not found` | GitHub CLI غير مثبّت | نزّله من `cli.github.com` |
| `remote origin already exists` | سبق ربط المستودع | `git remote set-url origin <الرابط>` |
| الموقع يعطي 404 | انتظر أول بناء أو تأكد من الفرع | `gh api repos/<حساب>/<ريبو>/pages` وتبحث عن `"status":"built"` |
| التحميل يفتح صفحة خطأ | اسم الملف في الرابط غير مطابق | افتح صفحة Releases وانسخ الرابط من الزر الأخضر |
| Pages توقف بعد ما خليت المستودع خاص | الخطة المجانية ما تدعم Pages للخاص | رجّعه عام أو اشترك Pro |
| ظهور `Permission denied` عند `git push` | الحساب غير مسجّل | `gh auth login` من جديد |

---

</div>

## English quick summary

- **Push code:** `git init -b main` → `git add -A` → `git commit` → `gh repo create <name> --public --source=. --push`
- **Download link:** `gh release create v1.0.0 "dist\RE4ClassicTrainer.exe#RE4ClassicTrainer.exe"` → serves from GitHub Releases (each file < 2 GiB, **no bandwidth limit**).
- **Website:** `git subtree push --prefix website origin gh-pages` + enable Pages → `https://<user>.github.io/<repo>/` (site ≤ 1 GB, soft 100 GB/month bandwidth).
- **Always free** for public repositories — no credit card required. You only pay if you *choose* extras: Pages from a **private** repo (GitHub Pro ~$4/mo), a **custom domain** (registrar ~$10–15/yr), or Git LFS over 1 GB.
- GitHub Pages must not be used as commercial/e-commerce hosting.
