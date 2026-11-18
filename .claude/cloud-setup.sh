#!/bin/bash
# ═══ تجهيز جلسة السحابة (claude.ai/code) — محلياً ما يسوي شي ═══
# ينزّل ffmpeg و numpy/scipy (مكتبة الخلفيات، الإيقاع، صوت الموشن). باقي أدوات السكل من خطوته 0.
# أسرع: حط نفس هالسكربت «Setup script» بإعدادات بيئة السحابة — ينحفظ بالكاش وما ينعاد كل جلسة.
[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0
SUDO=""; [ "$(id -u)" = "0" ] || SUDO="sudo"
if ! command -v ffmpeg >/dev/null 2>&1; then
  { $SUDO apt-get update -qq && DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq ffmpeg; } >/dev/null 2>&1 \
    || echo "⚠️ ما قدرت أنزّل ffmpeg — شغّل: apt-get install -y ffmpeg"
fi
if ! python3 -c "import numpy, scipy" >/dev/null 2>&1; then
  pip install -q numpy scipy >/dev/null 2>&1 || pip install -q --break-system-packages numpy scipy >/dev/null 2>&1 \
    || echo "⚠️ ما قدرت أنزّل numpy/scipy"
fi
FV="$(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3)"
echo "🎧 جلسة السحابة جاهزة — ffmpeg ${FV:-غير موجود} · سكلات المونتاج بـ.claude/skills · مكتبة الخلفيات الحلال بـhalal-audio/"
exit 0
