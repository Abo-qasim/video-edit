# مستودع المونتاج الحلال — بلقن Video-Edit + مكتبة الخلفيات الحلال

- `.claude/skills/` — سكلات المونتاج: `video-ad-editor` (المحرّك) · `montage-video` · `motion-video` · `podcast-video` · `thumbnail-video`.
  نفس ملفات بلقن **Video-Edit** اللي ينزل على الأجهزة من `.claude-plugin/marketplace.json`.
- `halal-audio/` — مكتبة الخلفيات الحلال (أصوات بشرية بلا موسيقى، علو موحّد، `catalog.json`).
  `42_bg_audio.py` و`motion/audio.py` يلقونها وحدهم — لا تمرّر مسار.

## بجلسة السحابة
- **الأدوات:** hook البداية (`.claude/cloud-setup.sh`) ينزّل ffmpeg وnumpy/scipy. الباقي من الخطوة 0 بـ`references/start.md`.
- **المقاطع:** المستخدم يرفعها بـ`work/<اسم-المشروع>/` (commit من جهازه، أو رابط تحميل مباشر). قت هب يرفض أي ملف فوق 100 ميقا.
- **التسليم:** الملف النهائي بـ`work/<اسم-المشروع>/out/` ← commit + push لفرع الجلسة، وقل له يحمّله من قت هب. ⛔ لا تدفع لـ`main`.
- **الشبكة Trusted:** تنزيل موديلات التفريغ ممكن ينحجب — قل له يخلي شبكة البيئة **Full**، أو يجيب التفريغ جاهز.
- **لينكس:** ميزات الماك (قصّ الشخص، تتبّع الوجه بـVision) ما تشتغل — البدائل بـ`references/any-environment.md`.
- **صفحة التصنيف** (`42_bg_audio.py page`) تحتاج متصفح على جهازه — بالسحابة `list` و`suggest` و`pick` بس.

## ⛔ لا تعدّل
- `halal-audio/*.mp3` — نسخة معالجة. الإضافة بـ`build` على جهاز المستخدم (`README.md`).
- `.claude/skills/` إلا بطلبه — أي تعديل هني يوصل لكل أجهزته بعد التحديث.
