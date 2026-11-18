#!/usr/bin/env python3
"""48_tape_wind.py — ترجيع / تقديم شريط (فيديو كاسيت) بصوت مسموع.

يجمع لقطات (فيديو+صوت) ويشغّلها للخلف (ترجيع) أو للأمام (تقديم) بسرعة S مرة، بلقطة مهزوزة وضجيج شريط وكلمة «ترجيع»/«تقديم»
بسهمين. الفرق عن الطريقة العادية (asetrate): الصوت يمشي بـatempo — يعني الأصوات تبقى **مسموعة** (جعجعة سريعة)، مو صفير ما ينسمع.

أمثلة:
  python3 scripts/48_tape_wind.py rewind hook1.mp4 hook2.mp4 hook3.mp4 -o rewind.mp4            # ترجيع بعد الهوكات
  python3 scripts/48_tape_wind.py ff intro1.mp4 intro2.mp4 -o ff.mp4 --speed 8 --text "تقديم"      # تقديم
الخيارات: --speed 7 · --size 1920x1080 · --text "ترجيع" · --font <ttf> (الافتراضي: Tajawal-Bold من motion/fonts) · --level 1.1 (قوة الأصوات)
المدخلات لازم تكون بنفس الأبعاد/الفريم، وفيها مسار صوت. الناتج: mp4 (h264 + aac 48k) وطوله = مجموع المدخلات ÷ السرعة.
يحتاج ffmpeg وPillow.  التوصية: ركّب فوقه مؤثر whoosh-05 من halal-sfx عند بداية الترجيع.
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout.strip())

def tempo_chain(s):
    """atempo يقبل 0.5–2 لكل مرحلة (النسخ القديمة): نقسم السرعة لمراحل ≤2 ونكمل بالباقي"""
    out = []
    while s > 2.0: out.append(2.0); s /= 2.0
    out.append(s); return ",".join(f"atempo={x:.4f}" for x in out)

def hud(path, text, size, font, wind):
    W, H = size; im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(font), int(H * 0.065), layout_engine=ImageFont.Layout.RAQM)
    tw = d.textlength(text, font=f, direction="rtl", language="ar"); cx, cy = W - int(W * 0.12), int(H * 0.09)
    d.text((cx + 4, cy + 4), text, font=f, fill=(0, 0, 0, 160), direction="rtl", language="ar", anchor="mm"); d.text((cx, cy), text, font=f, fill="white", direction="rtl", language="ar", anchor="mm")
    a = int(H * 0.025); gap = int(H * 0.045)
    for k in (0, 1):                                                     # سهمين: ◀◀ للترجيع، ▶▶ للتقديم
        x0 = cx - tw / 2 - int(H * 0.09) - k * gap if wind == "rewind" else cx + tw / 2 + int(H * 0.04) + k * gap
        pts = [(x0, cy - a), (x0, cy + a), (x0 - a * 1.6, cy)] if wind == "rewind" else [(x0, cy - a), (x0, cy + a), (x0 + a * 1.6, cy)]
        d.polygon(pts, fill="white")
    for y in range(0, H, 4): d.line([(0, y), (W, y)], fill=(0, 0, 0, 50))   # خطوط شاشة قديمة
    im.save(path)

def main():
    ap = argparse.ArgumentParser(description="ترجيع/تقديم شريط بصوت مسموع")
    ap.add_argument("mode", choices=["rewind", "ff"]); ap.add_argument("clips", nargs="+"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--speed", type=float, default=7.0); ap.add_argument("--size", default="1920x1080"); ap.add_argument("--text"); ap.add_argument("--font")
    ap.add_argument("--level", type=float, default=1.1)
    a = ap.parse_args(); W, H = (int(x) for x in a.size.lower().split("x")); n = len(a.clips)
    font = Path(a.font) if a.font else ROOT / "motion" / "fonts" / "Tajawal-Bold.ttf"
    if not font.exists(): sys.exit(f"⛔ الخط ما انلقى: {font} — مرّر --font <ttf> (الخطوط بـmotion/fonts)")
    text = a.text or ("ترجيع" if a.mode == "rewind" else "تقديم"); tot = sum(dur(c) for c in a.clips); D = round(tot / a.speed * 30) / 30
    png = Path(tempfile.mkdtemp()) / "hud.png"; hud(png, text, (W, H), font, a.mode)
    cat = "".join(f"[{i}:v][{i}:a]" for i in range(n)); rev_v, rev_a = ("reverse,", "areverse,") if a.mode == "rewind" else ("", "")
    fc = (f"{cat}concat=n={n}:v=1:a=1[cv][ca];"
          f"[cv]scale={W // 2}:{H // 2},{rev_v}setpts=PTS/{a.speed},fps=30,rgbashift=rh=6:bh=-6,noise=alls=20:allf=t,eq=saturation=0.6:contrast=1.15,scale={W}:{H}:flags=bicubic[r];"
          f"[r][{n}:v]overlay=0:0,drawbox=x=0:y='mod(t*{int(H * 1.4)},{H})':w={W}:h={int(H * 0.037)}:color=white@0.22:t=fill,format=yuv420p[vout];"
          f"[ca]{rev_a}{tempo_chain(a.speed)},highpass=f=150,volume={a.level},atrim=0:{D:.3f},apad,atrim=0:{D:.3f}[va];"
          f"anoisesrc=d={D:.3f}:c=pink:r=48000:a=0.5,bandpass=f=1100:width_type=h:w=900,tremolo=f=27:d=0.7,volume=0.07[wh];"
          f"[va][wh]amix=inputs=2:normalize=0,aformat=channel_layouts=stereo[aout]")
    cmd = ["ffmpeg", "-v", "error", "-y"] + sum((["-i", c] for c in a.clips), []) + ["-i", str(png), "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]", "-t", f"{D:.3f}",
           "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit("⛔ ffmpeg:\n" + r.stderr[-1200:])
    print(f"✓ {a.out} — {D:.2f} ث ({tot:.1f} ث ÷ {a.speed:g})")

if __name__ == "__main__": main()
