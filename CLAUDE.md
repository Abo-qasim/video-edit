# مستودع المونتاج الحلال — Video edit (halal) + مكتبة الخلفيات الحلال

هذا المستودع هو أصل بلقنين ينزلون من حساب المستخدم بـclaude.ai على أجهزته:
- `.claude/skills/` — بلقن **video-edit-halal**: `video-ad-editor` (المحرّك) · `montage-video` · `motion-video` · `podcast-video` · `thumbnail-video`.
- `halal-audio/` — بلقن **halal-audio**: الخلفيات الحلال (أصوات بشرية بلا موسيقى، علو موحّد، `catalog.json`).
  `42_bg_audio.py` و`motion/audio.py` يلقونها وحدهم — لا تمرّر مسار.
- `halal-sfx/` — بلقن **halal-sfx**: 33 مؤثر بلا موسيقى (`references/sfx-library.md`) — `44_sfx_lib.py` يلقاه وحده.
  أصوات جديدة: فرز YAMNet (`~/.claude/models/yamnet-qualcomm` على جهازه) ← `43_sfx.py review` ← المقبول هني ← ارفع إصدار `halal-sfx`.

## بجلسة السحابة
- **الأدوات:** hook البداية (`.claude/cloud-setup.sh`) ينزّل ffmpeg وnumpy/scipy. الباقي من الخطوة 0 بـ`references/start.md`.
- **المقاطع:** المستخدم يرفعها بـ`work/<اسم-المشروع>/` (commit من جهازه، أو رابط تحميل مباشر). قت هب يرفض أي ملف فوق 100 ميقا.
- **التسليم:** الملف النهائي بـ`work/<اسم-المشروع>/out/` ← commit + push لفرع الجلسة، وقل له يحمّله من قت هب. ⛔ لا تدفع لـ`main`.
- **الشبكة Trusted:** تنزيل موديلات التفريغ ممكن ينحجب — قل له يخلي شبكة البيئة **Full**، أو يجيب التفريغ جاهز.
- **لينكس:** ميزات الماك (قصّ الشخص، تتبّع الوجه بـVision) ما تشتغل — البدائل بـ`references/any-environment.md`.
- **صفحة التصنيف** (`42_bg_audio.py page`) تحتاج متصفح على جهازه — بالسحابة `list` و`suggest` و`pick` بس.

## لما تعدّل هالمستودع (على جهاز المستخدم)
- أي تعديل بـ`.claude/skills/` ← ارفع `version` بـ`.claude/skills/.claude-plugin/plugin.json` و`video-ad-editor/VERSION` (`6.0.1-halal.N`).
- ملفات صوت جديدة ← `build` هني (`references/bg-library.md`) ← ارفع `version` بـ`halal-audio/.claude-plugin/plugin.json`.
  ⚠️ البلقن ~56 من 200 ميقا (حد claude.ai) — أكثر من كذا = بلقن أصوات ثاني.
- بدون رفع الإصدار، حسابه ما يوزّع النسخة الجديدة على أجهزته.

## ⛔ لا تعدّل
- `halal-audio/*.mp3` — نسخة معالجة. الإضافة بـ`build` بس.
- `.claude/skills/` إلا بطلبه — أي تعديل هني يوصل لكل أجهزته.
