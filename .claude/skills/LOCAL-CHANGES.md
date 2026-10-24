# تعديلات هالنسخة فوق video-edit الأصلي

هذي نسخة من بلقن **video-edit 6.0.1** (ماجد الزعابي — رخصة MIT) داخل مستودع `video-edit-halal`، ومضاف فوقها:

## مكتبة الخلفيات الحلال
| الملف | |
|---|---|
| `video-ad-editor/scripts/42_bg_audio.py` | جديد — build · list · suggest · pick · page · sync · where |
| `video-ad-editor/scripts/bg-library.html` | جديد — صفحة الاستماع والتصنيف + زر المزامنة |
| `video-ad-editor/references/bg-library.md` | جديد — الشرح لكلود |
| `video-ad-editor/motion/audio.py` | `music.file` (خلفية من ملف أو `lib:07`) + UTF-8 |
| `video-ad-editor/SKILL.md` · `montage-video/SKILL.md` · `references/montage.md` · `references/motion-mode.md` · `references/script-map.md` · `motion/ENGINE-API.md` | أسطر تدل على المكتبة |

المكتبة بجذر المستودع: `halal-audio/` (المصدر الأصلي: مجلد «الأصوات حلال» على جهاز المستخدم).

## إصلاحات ويندوز
| الملف | |
|---|---|
| `video-ad-editor/scripts/beat.py` | UTF-8 — كان يطيح لما يطبع عربي |
| `video-ad-editor/scripts/06c_loudfix.sh` | `_compat.sh` + `$PY` بدل `python3` — كان يفشل دايماً |
| `video-ad-editor/scripts/06b_master.sh` | `$PY` بدل `python3` بفحص المسار الصامت |

## غير كذا
- `video-ad-editor/motion/moves/previews.zip` — معاينات الـ100 حركة (من بلقن video-edit-previews).
- `.claude-plugin/plugin.json` — الاسم `Video-Edit` والإصدار `6.0.1-halal.N`.
- `video-ad-editor/VERSION` — نفس الإصدار (فحص التحديث بـ`00_setup.sh` يقارنه بقت هب المؤلف).

## لما ينزل إصدار جديد من المؤلف
1. انسخ الإصدار الجديد لمجلد مؤقت.
2. طبّق الرقعة من داخله: `patch -p1 < ~/.claude/backups/halal-audio-on-6.0.1.patch`
   (أو اطلب من كلود «حدّث البلقن من الإصدار الجديد» — يسوي الدمج ويحل أي تعارض).
3. حدّث `plugin.json` و`VERSION` (مثلاً `6.0.2-halal.1`) وحط `previews.zip`.
4. استبدل `.claude/skills/` بالمستودع بالناتج، ثم commit + push.
5. بكل جهاز: `claude plugin marketplace update halal-video` و`claude plugin update Video-Edit@halal-video`.
