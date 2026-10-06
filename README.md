<div dir="rtl">

# DULE — RE4 Classic Trainer

أداة خارجية (Windows · ملف `.exe` واحد) للعبة **Resident Evil 4 Classic** (إصدار Steam 2005 / UHD):

- 🎨 **سكنات ليون** — تُكتب في البدلتين (`pl00` العادية و `pl08` الـ Mafia) مع التكستشرات، فتظهر في أي حفظ.
- ⚡ **بعث فوري** — لحظة وصول الصحة صفر تُرفع فوراً، بدون شاشة موت ولا أي ضغطة زر.
- 🛡️ **حماية من الضرر (اختياري)** — مفتاح منفصل مع دعم invulnerability من re4_tweaks.
- 💾 **شيك بوينت** — تخزين/استرجاع حفظك مع نسخة أمان إجبارية قبل أي استرجاع.
- 🔁 **إعادة تشغيل اللعبة بضغطة** — لأن RE4 يُبقي موديل ليون في الذاكرة.
- 📂 **يتّبع نسخة اللعبة تلقائياً** — أي نسخة تشغّلها، ولها نسخ احتياطية مستقلة.
- 🧯 **نسخ احتياطية آمنة** — كل ملف أصلي يُخزَّن قبل أي تعديل، مع `Restore Original`.
- 🌐 **موقع تعريفي** عربي/إنجليزي في مجلد [`website/`](website/) — وصفحة الأسئلة تشرح كل شي.

## التحميل

**الموقع الرسمي:** https://zxwxg.github.io/re4-classic-trainer/

**آخر نسخة جاهزة:** [Releases v1.0.0](https://github.com/zxwxg/re4-classic-trainer/releases/latest) — ملف واحد `RE4ClassicTrainer.exe` (19.8 ميجا)، بدون تثبيت.
شغّله كمسؤول (Run as administrator) لأنه يكتب في مجلد اللعبة.

## تشغيل الكود من المصدر

```bat
py -m pip install customtkinter pillow
py -m re4_trainer
```

بناء الملف التنفيذي:

```bat
build_exe.bat
```

## النشر على GitHub

دليل كامل خطوة بخطوة (الرفع، رابط التحميل، الصفحات، وكل ما هو مجاني وما هو مدفوع):
[`PUBLISHING.md`](PUBLISHING.md)

## الموقع

```bat
website\start_website.cmd
```

أو افتح `website/index.html` مباشرة.

## ملاحظات تقنية

- اللعبة المدعومة: `bio4.exe` (Steam release 2005 / UHD). المؤشرات في `re4_trainer/core/pattern.py`.
- صحة اللاعب: `GLOBAL_WK` + `0x4FB4` (القيمة القصوى `+0x4FB6`).
- كل تعديل على ملفات اللعبة يمر عبر نسخة احتياطية + بصمة `SHA-256`.

---

</div>

# DULE — RE4 Classic Trainer (EN)

An external Windows trainer (single `.exe`) for **Resident Evil 4 Classic** (Steam 2005 / UHD):

- 🎨 **Leon skins** written into **both** outfits (`pl00` Normal + `pl08` Mafia) with their textures.
- ⚡ **Instant respawn** — health is restored the moment it would hit zero, no death screen, no clicks.
- 🛡️ **Optional damage protection** (health guard + re4_tweaks invulnerability when present).
- 💾 **Checkpoints** for your save file, always with a safety copy before restoring.
- 🔁 **One-click game restart** (RE4 keeps Leon's model in memory for the whole session).
- 📂 **Follows the game copy you run**, with a separate backup set per install.
- 🧯 **Safe backups** — every original file is stored (size + SHA-256) and can be restored.
- 🌐 **Bilingual website** (Arabic / English) in [`website/`](website/).

**Download:** the latest build is on the [Releases page](https://github.com/zxwxg/re4-classic-trainer/releases/latest) · **Live site:** https://zxwxg.github.io/re4-classic-trainer/

**From source:** `py -m pip install customtkinter pillow` then `py -m re4_trainer` (build with `build_exe.bat`).

> Unofficial fan tool. Resident Evil 4 and all related trademarks belong to Capcom.
