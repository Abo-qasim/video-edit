# -*- coding: utf-8 -*-
"""🔔 مكتبة المؤثرات الحلال (halal-sfx) — مؤثرات حقيقية بلا موسيقى (فرز YAMNet + مراجعة بالأذن).

  python 44_sfx_lib.py list [--cat whoosh]     ← التصنيفات والأصوات
  python 44_sfx_lib.py where                   ← وين المكتبة
  python 44_sfx_lib.py play <work> <id|تصنيف>  ← ينسخ الصوت لـ<work>/sfx-preview.mp3 عشان يسمعه

  من سكربتات المؤثرات (05_sfx.py و motion/audio.py) — بلا ما تنادي هالملف مباشرة:
    load("whoosh")      ← صوت من التصنيف (ثابت بالبذرة)     load("whoosh-04") ← صوت بعينه
    يرجع (عينات mono 48kHz ذروتها 1.0، نقطة الربط بالثواني، المعلومات)

  نقطة الربط (anchor): الووش والتوتر = الذروة، والباقي = البداية — حطّه على اللحظة وهي تضبط.
التصنيفات: whoosh ووش/انتقال · voice صوت ميمز · ui نقرة/تنبيه · camera كاميرا/فلاش ·
           suspense مفاجأة/توتر · hit ضربة/كسر · game لعبة/نتيجة · awkward صمت محرج
"""
# ── توافق ويندوز/UTF-8 ─────────────────────────────────────────────
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
# ──────────────────────────────────────────────────────────────────
import argparse, glob, json, os, random, shutil, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.abspath(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude"))
SR = 48000
_CACHE = {}


def is_lib(p):
    try:
        with open(os.path.join(p, "catalog.json"), encoding="utf-8") as f: d = json.load(f)
        return isinstance(d, dict) and d.get("kind") == "sfx" and "sounds" in d
    except (OSError, ValueError):
        return False


def find_lib():
    """(المسار، من وين) — نفس ترتيب مكتبة الخلفيات: BG/SFX_LIB ← المستودع ← المشروع ← البلقن جنبنا ← نسخة المتجر."""
    if os.environ.get("SFX_LIB"): return os.path.abspath(os.path.expanduser(os.environ["SFX_LIB"])), "SFX_LIB"
    def cands():
        yield os.path.join(HERE, "..", "..", "..", "..", "halal-sfx"), "المستودع"
        for d in (os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
            if d: yield os.path.join(d, "halal-sfx"), "مجلد المشروع"
        root, up = os.path.dirname(os.path.dirname(HERE)), None
        up = root
        for _ in range(2):                                           # بلقن halal-sfx جنبنا (الديسكتوب / الكاش / المزامنة)
            up = os.path.dirname(up)
            for pat in ("*/catalog.json", "*/*/catalog.json"):
                for p in sorted(glob.glob(os.path.join(up, pat)), key=os.path.getmtime, reverse=True): yield os.path.dirname(p), "بلقن halal-sfx"
        for p in glob.glob(os.path.join(CONF, "plugins", "synced", "**", "catalog.json"), recursive=True): yield os.path.dirname(p), "بلقن halal-sfx"
        for p in glob.glob(os.path.join(CONF, "plugins", "marketplaces", "*", "halal-sfx")): yield p, "نسخة المتجر"
    for p, why in cands():
        if is_lib(p): return os.path.realpath(p), why
    return None, "ما لقيتها"


LIB, LIB_FROM = find_lib()


def catalog():
    if not LIB: raise SystemExit("❌ ما لقيت مكتبة المؤثرات (halal-sfx) — فعّل بلقن «Halal sound effects» من Customize ← Plugins، أو SFX_LIB=مسار")
    with open(os.path.join(LIB, "catalog.json"), encoding="utf-8") as f: return json.load(f)


def resolve(key, seed=7):
    """id بعينه (whoosh-04) أو تصنيف (whoosh) ← صوت ثابت بالبذرة عشان نفس الفيديو يطلع نفس الصوت."""
    cat = catalog(); key = str(key).strip()
    hit = next((s for s in cat["sounds"] if s["id"] == key), None)
    if hit: return hit
    pool = [s for s in cat["sounds"] if s["cat"] == key]
    if not pool: raise SystemExit(f"❌ ما فيه صوت أو تصنيف «{key}» — شوف: python scripts/44_sfx_lib.py list")
    return random.Random(f"{seed}:{key}").choice(pool)


def load(key, seed=7, sr=SR):
    """(عينات mono ذروتها 1.0، نقطة الربط بالثواني، المعلومات)"""
    s = resolve(key, seed)
    ck = (s["id"], sr)
    if ck not in _CACHE:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(LIB, s["file"]), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
        x = np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)
        if not len(x): raise SystemExit(f"❌ ما قدرت أقرا {s['file']}")
        _CACHE[ck] = x / (np.max(np.abs(x)) + 1e-12)
    return _CACHE[ck], float(s.get("anchor", 0)), s


def cmd_list(a):
    cat = catalog()
    print(f"🔔 {len(cat['sounds'])} مؤثر · {LIB} ({LIB_FROM})")
    for c, ar in cat["categories"].items():
        if a.cat and c != a.cat: continue
        rows = [s for s in cat["sounds"] if s["cat"] == c]
        print(f"\n{c} — {ar} ({len(rows)})")
        for s in rows: print(f"   {s['id']:<12} {s['dur']:5.2f} ث  {s['title'][:44]}")


def cmd_where(a):
    print(f"🔔 المكتبة: {LIB or '—'}  ({LIB_FROM})")


def cmd_play(a):
    s = resolve(a.key); os.makedirs(a.work, exist_ok=True)
    dst = os.path.join(a.work, "sfx-preview.mp3"); shutil.copyfile(os.path.join(LIB, s["file"]), dst)
    print(f"🔈 {dst}  ← #{s['id']} {s['title']} ({s['dur']} ث)")


def main():
    ap = argparse.ArgumentParser(description="مكتبة المؤثرات الحلال")
    sp = ap.add_subparsers(dest="cmd", required=True)
    l = sp.add_parser("list"); l.add_argument("--cat")
    sp.add_parser("where")
    p = sp.add_parser("play"); p.add_argument("work"); p.add_argument("key")
    a = ap.parse_args()
    {"list": cmd_list, "where": cmd_where, "play": cmd_play}[a.cmd](a)


if __name__ == "__main__":
    main()
