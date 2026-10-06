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

آخر نسخة جاهزة في صفحة [Releases](../../releases/latest) — ملف واحد، بدون تثبيت.
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

**Download:** the latest build is on the [Releases](../../releases/latest) page.

**From source:** `py -m pip install customtkinter pillow` then `py -m re4_trainer` (build with `build_exe.bat`).

> Unofficial fan tool. Resident Evil 4 and all related trademarks belong to Capcom.
