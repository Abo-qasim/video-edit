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

## مكتبة المؤثرات الحلال (بلا موسيقى)
| الملف | |
|---|---|
| `video-ad-editor/scripts/44_sfx_lib.py` | جديد — يلقى بلقن halal-sfx ويحمّل الأصوات (list · where · play) |
| `video-ad-editor/scripts/43_sfx.py` + `sfx-review.html` | جديد — تنزيل جزئي من Sonniss + صفحة «مقبول / مرفوض» |
| `video-ad-editor/scripts/05_sfx.py` | مفتاح `"lib"` بـ`sfx.json` — أصوات حقيقية بذروة ‎-18 dBFS |
| `video-ad-editor/motion/audio.py` | نوع `lib:<تصنيف أو رقم>` بـ`sfx.json` |
| `video-ad-editor/references/sfx-library.md` + أسطر بـ`SKILL.md` و`ENGINE-API.md` و`script-map.md` | الشرح |

المكتبة بجذر المستودع: `halal-sfx/` (المصدر: ملف المستخدم + مجلد درايف ADAX DS، فرز YAMNet ثم مراجعته بأذنه).

## إصلاحات ويندوز
| الملف | |
|---|---|
| `video-ad-editor/scripts/beat.py` | UTF-8 — كان يطيح لما يطبع عربي |
| `video-ad-editor/scripts/06c_loudfix.sh` | `_compat.sh` + `$PY` بدل `python3` — كان يفشل دايماً |
| `video-ad-editor/scripts/06b_master.sh` | `$PY` بدل `python3` بفحص المسار الصامت |

## غير كذا
- `video-ad-editor/motion/moves/previews.zip` — معاينات الـ100 حركة (من بلقن video-edit-previews).
- `.claude-plugin/plugin.json` — الاسم `video-edit-halal` (مزامنة claude.ai تشترط حروف صغيرة) والإصدار `6.0.1-halal.N`.
- `video-ad-editor/VERSION` — نفس الإصدار (فحص التحديث بـ`00_setup.sh` يقارنه بقت هب المؤلف).
- `video-ad-editor/scripts/00_setup.sh` — نسخة halal ما تستبدل ملفاتها بإصدار المؤلف (`--update` كان يمسح الإضافات) — تطبع خطوات الدمج بداله.

## لما ينزل إصدار جديد من المؤلف
1. انسخ الإصدار الجديد لمجلد مؤقت.
2. طبّق الرقعة من داخله: `patch -p1 < ~/.claude/backups/halal-audio-on-6.0.1.patch`
   (أو اطلب من كلود «حدّث البلقن من الإصدار الجديد» — يسوي الدمج ويحل أي تعارض).
3. حدّث `plugin.json` و`VERSION` (مثلاً `6.0.2-halal.1`) وحط `previews.zip`.
4. استبدل `.claude/skills/` بالمستودع بالناتج، ثم commit + push.
5. حسابك بـclaude.ai يسحبه لكل الأجهزة وحده (Sync automatically) — أو **Check for updates**.

## حزمة المؤثرات المضحكة 101–119 (6.0.1-halal.6)
| الملف | |
|---|---|
| `video-ad-editor/motion/moves.js` | آخره: `FX.stampSlam` `modeToggle` `heartEyes` `popPicture` `reactionPip` `calendarFlip` `blackoutGag` `zotTag` `routeTrace` `gaugeDrop` `ringCount` `compassSwing` `guestTag` `thanksRoll` `evolveTable` `fireLeak` `newsBar` `nameArrow` `underlineCaption` (101–119) + نسخ 16:9 `FX16.*` لـ#11 #65 #69 #71 #76 #97 (أقسام مفصولة بـ`═══ moves-extra.js` و`═══ moves-landscape.js`) |
| `video-ad-editor/motion/moves/catalog.json` | أسطر 101–119، كلها `role: "accent"` (لهجات فقط، ما تصير أساسية) إلا 116 انتقال النار؛ cues جديدة: verdict mode love reaction food time route progress guest thanks compare3 alert |
| `video-ad-editor/motion/moves/previews.zip` | + معاينات 101–119 (`previews/` طولي، `previews-landscape/` أفقي) |
| `video-ad-editor/references/motion-effects.md` | جديد — الدليل: متى تنقترح، الخيارات، الأصوات المناسبة |
| `video-ad-editor/scripts/48_tape_wind.py` | جديد — ترجيع/تقديم شريط بأصوات مسموعة |
| `video-ad-editor/references/moves.md` · `scripts/35_moves.py` | سطر يدل على الدليل + cues الجديدة بسطر الاستخدام |

## تنظيف المكتبات من الموسيقى (6.0.1-halal.7 · halal-audio 1.2.0 · halal-sfx 1.1.0)
- فحص آلي (تصنيف AudioSet + عزل الصوت البشري بـDemucs) ثم مراجعة المستخدم بأذنه.
- انحذفت 37 خلفية (فيها آلات أو غير مناسبة) — باقي 20: 03 05 06 12 14 19 20 27 28 30 33 34 38 39 42 43 44 49 52 56.
- انحذفت 4 مؤثرات: suspense-02 · suspense-03 · game-02 · whoosh-03 — باقي 33.
- الأعداد تحدّثت بـ`references/sfx-library.md` و`bg-library.md` و`README.md` و`CLAUDE.md` والـ`plugin.json`ات و`marketplace.json`.
- 6.0.1-halal.8: أمثلة الشروحات كانت تشير لملفات محذوفة — `game-02` ← `ui-03`، `lib:07` ← `lib:12`، `whoosh-03` ← `whoosh-04`.
