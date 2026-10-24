# -*- coding: utf-8 -*-
"""🎧 مكتبة الخلفيات الصوتية الحلال — أصوات بشرية بلا موسيقى، جاهزة للريل والمونتاج والموشن والبودكاست.

  python 42_bg_audio.py build <مجلد_الملفات> [--lufs -16] [--jobs 4] [--force]
        ← يجهّز المكتبة: يقص الصمت من الطرفين، يوحّد العلو، يسمّي، يقيس الإيقاع → catalog.json
          (الملفات اللي ما تغيّرت ما تنعاد — ضيف ملفات جديدة للمجلد وأعد build)
  python 42_bg_audio.py list [--use montage] [--mood calm]
  python 42_bg_audio.py suggest <work> [--use reel|montage|motion|podcast] [--mood calm] [--dur 30] [--n 3]
        ← أفضل 3 + معاينة 20 ث لكل وحدة بـ<work>/bg-previews/ (A · B · C) — خلّه يسمع ويختار
  python 42_bg_audio.py pick <work> <A|B|C|07> [--dur 30] [--from 0]
        ← يكتب <work>/bg-audio.mp3 (يبدأ على نبضة، ويلف بتلاشٍ لو الفيديو أطول) + bg-audio.json (المصدر)
          06b_master.sh و beat.py يقرونه كما هو — بلا أي تعديل عليهم
  python 42_bg_audio.py page [--port 8793] [--no-open]
        ← صفحة استماع وتصنيف (هادئ · ملهم · حماسي · تأملي · ملحمي) تحفظ مباشرة، وفيها زر «مزامنة»
  python 42_bg_audio.py sync [--pull]
        ← يزامن التصنيف مع قت هب (يجيب تصنيف أجهزتك الثانية ويرفع تصنيف هالجهاز) · --pull يجيب بس
  python 42_bg_audio.py where     ← وين المكتبة اللي ينقرا منها

المكتبة تنلقى وحدها (الأول يفوز): BG_LIB ← halal-audio/ بالمستودع اللي فيه السكل (السحابة، أو نسخة قت هب)
← halal-audio/ بمجلد المشروع ← نسخة البلقن من قت هب (~/.claude/plugins/marketplaces/*/halal-audio) ← ~/.claude/halal-audio.
تصنيف كل جهاز ينحفظ احتياطياً بـ~/.claude/halal-audio-tags.json — ما يضيع لو انعادت نسخة البلقن قبل المزامنة.
الملفات الأصلية ما تنلمس — المكتبة نسخة معالجة. التفاصيل → references/bg-library.md
"""
# ── توافق ويندوز/UTF-8 ─────────────────────────────────────────────
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
# ──────────────────────────────────────────────────────────────────
import argparse, glob, json, math, os, random, re, shutil, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.abspath(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude"))


def find_lib():
    """(المسار، من وين) — أول مكان فيه catalog.json يفوز. لو ما فيه شي: المسار الافتراضي لـbuild."""
    if os.environ.get("BG_LIB"):
        return os.path.abspath(os.path.expanduser(os.environ["BG_LIB"])), "BG_LIB"
    c = [(os.path.join(HERE, "..", "..", "..", "..", "halal-audio"), "المستودع")]   # <repo>/.claude/skills/video-ad-editor/scripts
    for d in (os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
        if d: c.append((os.path.join(d, "halal-audio"), "مجلد المشروع"))
    c += [(p, "نسخة البلقن من قت هب") for p in sorted(glob.glob(os.path.join(CONF, "plugins", "marketplaces", "*", "halal-audio")))]
    c.append((os.path.join(CONF, "halal-audio"), "~/.claude/halal-audio"))
    for p, why in c:
        if os.path.isfile(os.path.join(p, "catalog.json")):
            return os.path.realpath(p), why                          # realpath: ويندوز يخلط 9649~1 بالاسم الطويل
    return os.path.realpath(os.path.join(CONF, "halal-audio")), "جديد"


LIB, LIB_FROM = find_lib()
CAT = os.path.join(LIB, "catalog.json")
TAGS = os.path.join(CONF, "halal-audio-tags.json")          # تصنيف هالجهاز + عدّاد الاستخدام — احتياط ما يتأثر بتحديث البلقن
AUD_EXT = (".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus")
MOODS = {"calm": "هادئ", "inspiring": "ملهم", "energetic": "حماسي", "reflective": "تأملي", "epic": "ملحمي"}
USES = {"reel": "ريل كلام", "montage": "مونتاج", "motion": "موشن", "podcast": "بودكاست"}
USER = {"mood": None, "name": None, "rating": 0, "beat_user": None, "hidden": False, "notes": "", "tagged_at": 0}
LOCK = threading.Lock()


# ───────────────────────── أدوات ─────────────────────────
def die(m):
    print("❌ " + m)
    sys.exit(2)


ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")    # beat.py يطبع عربي — بدونها ويندوز يطيّحه


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, env=ENV)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    if r.returncode != 0:
        tail = [x for x in out.strip().splitlines() if x.strip()][-1:] or ["?"]
        raise RuntimeError(f"{os.path.basename(str(cmd[0]))} {os.path.basename(str(cmd[1]))}: {tail[0]}")
    return out


def last_json(out):
    return json.loads(out[out.rindex("{"):out.rindex("}") + 1])


def probe(p):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags=title,artist", "-of", "json", p])
    f = json.loads(out).get("format", {})
    tags = {k.lower(): v.replace("﻿", "").strip() for k, v in (f.get("tags") or {}).items()}
    return float(f.get("duration", 0) or 0), tags


def pcm(p, sr, start=0.0, dur=None, ch=1):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}"] + (["-t", f"{dur:.3f}"] if dur else []) + \
          ["-i", p, "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(r.stdout, dtype="<f4")


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def read_json(p, default):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:     # LF: بدونها ويندوز يكتب CRLF وgit يحسبه تعديل
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def local_tags():
    d = read_json(TAGS, {})
    return {"tags": d.get("tags", {}), "used": d.get("used", {})}


def overlay(cat, loc):
    """تصنيف هالجهاز فوق الفهرس — الأحدث (tagged_at) يفوز، وعدّاد الاستخدام محلي."""
    for t in cat.get("tracks", []):
        for k, v in USER.items(): t.setdefault(k, v)
        mine = loc["tags"].get(t["id"])
        if mine and mine.get("tagged_at", 0) > (t.get("tagged_at") or 0):
            t.update({k: mine.get(k, USER[k]) for k in USER})
        t["used"] = loc["used"].get(t["id"], 0)
    return cat


def load_cat(required=True):
    if not os.path.exists(CAT):
        if required:
            die(f"ما فيه مكتبة ({LIB}) — جهّزها أول:  python 42_bg_audio.py build <مجلد_الملفات>")
        return None
    return overlay(read_json(CAT, {"tracks": []}), local_tags())


def save_cat(cat):
    out = dict(cat, tracks=[{k: v for k, v in t.items() if k != "used"} for t in cat.get("tracks", [])])
    write_json(CAT, out)


def label(t):
    """الاسم اللي يشوفه المستخدم: اسمه هو ← العنوان من الملف ← الرقم."""
    base = t.get("name") or t.get("title") or "بلا اسم"
    return base + (f" ({t['variant']})" if t.get("variant") and not t.get("name") else "")


def beat_ok(t):
    return t["beat_user"] if t.get("beat_user") is not None else t.get("beat_auto", False)


def energy_word(e):
    return "هادئ" if e < 0.35 else ("متوسط" if e < 0.65 else "قوي")


# ───────────────────────── build ─────────────────────────
def clean_title(raw):
    """«'Hopeful' (Nasheed Background) *Vocals only* Soundtrack #halalbeats» ← Hopeful"""
    t = raw.replace("﻿", "").strip()
    var = []
    for g in re.findall(r"[\(\[]([^\)\]]*)[\)\]]", t):
        low = g.lower()
        if "slowed" in low: var.append("slowed" + (" + reverb" if "reverb" in low else ""))
        elif "drum" in low: var.append("vocal & drum")
    t = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", t)
    t = re.sub(r"\*[^*]*\*", " ", t)
    t = re.sub(r"#\S+", " ", t)
    t = re.sub(r"\b(soundtrack|nasheed|background|instrumental|vocals? only)\b", " ", t, flags=re.I)
    t = re.sub(r"[\"'‘’“”]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -–")
    if t.isupper(): t = t.title()
    return t, ", ".join(dict.fromkeys(var))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def track_id(stem, taken):
    tid = f"{int(stem):02d}" if stem.isdigit() else (slug(stem) or "track")
    base, i = tid, 2
    while tid in taken:
        tid = f"{base}-{i}"; i += 1
    taken.add(tid)
    return tid


def silences(out, dur):
    st = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", out)]
    pairs = [(s, en[i] if i < len(en) else dur) for i, s in enumerate(st)]
    lead = next((e for s, e in pairs if s <= 0.05), 0.0)
    tail = next((s for s, e in pairs if e >= dur - 0.15 and s > lead), dur)
    return max(0.0, lead - 0.05), min(dur, tail + 0.3)          # نخلي ذيل الصدى


def features(path, dur):
    x = pcm(path, 8000)
    if len(x) < 8000: return [0] * 160, 0.0
    n = 160; k = len(x) // n
    pk = np.array([np.max(np.abs(x[i * k:(i + 1) * k])) for i in range(n)])
    pk = np.sqrt(pk / (pk.max() + 1e-9))                         # جذر = الهادي يبان بالموجة
    w = 2048; S = np.zeros(w // 2 + 1)
    for i in range(0, len(x) - w, w * 4):
        S += np.abs(np.fft.rfft(x[i:i + w] * np.hanning(w))) ** 2
    f = np.fft.rfftfreq(w, 1 / 8000)
    low = float(S[f < 150].sum() / (S.sum() + 1e-12))
    return [int(round(v * 100)) for v in pk], round(low, 3)


def pick_start(b, dur):
    """أول بداية مازورة بطاقة ≥ 0.6 من أعلى قسم — يتخطّى المقدمة الطويلة الخافتة، ويبقى على النبضة."""
    beats, en, downs = b.get("beats", []), b.get("energy", []), b.get("downbeats", [])
    if not downs: return 0.0
    for d in downs:
        if d > dur * 0.3: break
        i = int(np.argmin(np.abs(np.array(beats) - d))) if beats else 0
        if i < len(en) and en[i] >= 0.6:
            return round(float(d), 3)
    return round(float(downs[0]), 3) if downs[0] < dur * 0.3 else 0.0


def process(src, tid, lufs, old, force):
    st = os.stat(src)
    srcinfo = {"file": os.path.basename(src), "size": st.st_size, "mtime": int(st.st_mtime)}
    if old and not force and old.get("source") == srcinfo and old.get("lufs") == lufs and os.path.exists(os.path.join(LIB, old["file"])):
        return old, "⏭"
    dur, tags = probe(src)
    title, var = clean_title(tags.get("title", ""))
    artist = tags.get("artist") or None
    fname = f"{tid}-{slug(title)}{('-' + slug(var)) if var else ''}.mp3" if title else f"{tid}.mp3"
    # المرور الأول: الصمت + قياس العلو بقراءة وحدة
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
               f"silencedetect=n=-50dB:d=0.4,loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    js = last_json(out)
    if js["input_i"] in ("-inf", "inf") or float(js["input_i"]) < -70:
        return None, "🔇 صامت — تخطّيته"
    lead, tail = silences(out, dur)
    # المرور الثاني: قص + توحيد العلو + mp3 بنفس الوسوم النظيفة
    af = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}"
          f":measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}"
          f":linear=true:print_format=json")
    dst = os.path.join(LIB, fname); tmp = dst + ".part.mp3"
    meta = ["-metadata", f"title={label({'id': tid, 'title': title, 'variant': var})}"] + (["-metadata", f"artist={artist}"] if artist else [])
    out2 = run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{lead:.3f}", "-to", f"{tail:.3f}", "-i", src, "-vn",
                "-map_metadata", "-1", "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "libmp3lame", "-q:a", "4",
                "-id3v2_version", "3"] + meta + [tmp])
    js2 = last_json(out2)
    os.replace(tmp, dst)
    if old and old["file"] != fname and os.path.exists(os.path.join(LIB, old["file"])):
        os.remove(os.path.join(LIB, old["file"]))
    # الإيقاع: beat.py نفسه اللي يستخدمه المونتاج
    bdir = os.path.join(LIB, ".beats"); os.makedirs(bdir, exist_ok=True)
    bj = os.path.join(bdir, f"{tid}.json")
    run([sys.executable, os.path.join(HERE, "beat.py"), dst, "--out", bj])
    with open(bj, encoding="utf-8") as f: b = json.load(f)
    d_out = tail - lead
    peaks, low = features(dst, d_out)
    bpm = float(b.get("bpm", 0)); dens = len(b.get("onsets", [])) / max(1.0, d_out)
    energy = 0.5 * min(1, max(0, (bpm - 70) / 60)) + 0.5 * min(1, max(0, (dens - 1) / 7))
    rec = {"id": tid, "file": fname, "title": title or None, "variant": var or None, "artist": artist, "source": srcinfo,
           "lufs": lufs, "lufs_in": round(float(js["input_i"]), 1), "mode": js2.get("normalization_type"),
           "trim": [round(lead, 2), round(dur - tail, 2)], "duration": round(d_out, 2),
           "start": pick_start(b, d_out), "bpm": round(bpm, 1), "density": round(dens, 2), "low": low,
           "energy": round(energy, 2), "beat_auto": bool(low >= 0.3 and dens >= 1.5),
           "drops": [round(float(x), 2) for x in b.get("drops", [])[:8]], "peaks": peaks}
    for k, v in USER.items():
        rec[k] = old.get(k, v) if old else v
    return rec, "✅"


def cmd_build(a):
    src_dir = os.path.abspath(a.src)
    if not os.path.isdir(src_dir): die(f"ما لقيت المجلد {src_dir}")
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(AUD_EXT)]
    if not files: die("ما فيه ملفات صوت بالمجلد")
    files.sort(key=lambda s: (0, int(os.path.splitext(s)[0])) if os.path.splitext(s)[0].isdigit() else (1, s.lower()))
    os.makedirs(LIB, exist_ok=True)
    cat = load_cat(required=False) or {}
    old = {t["source"]["file"]: t for t in cat.get("tracks", [])}
    taken = set()
    jobs = []
    for f in files:
        prev = old.get(f)
        tid = prev["id"] if prev else None
        if tid: taken.add(tid)
        jobs.append([f, tid, prev])
    for j in jobs:
        if not j[1]: j[1] = track_id(os.path.splitext(j[0])[0], taken)
    print(f"🎧 {len(jobs)} ملف ← {LIB}  (العلو {a.lufs} LUFS · {a.jobs} بالتوازي)")
    t0 = time.time(); done = [0]; results = {}

    def one(j):
        f, tid, prev = j
        try:
            rec, msg = process(os.path.join(src_dir, f), tid, a.lufs, prev, a.force)
        except Exception as e:
            rec, msg = prev, "⚠️ " + str(e).splitlines()[0][:120]
        with LOCK:
            done[0] += 1; results[f] = rec
            extra = f"{rec['file']} · {mmss(rec['duration'])} · {rec['bpm']:.0f} BPM" if rec else ""
            print(f"  [{done[0]:>2}/{len(jobs)}] {msg} {f} → {extra}", flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(one, jobs))
    tracks = [results[j[0]] for j in jobs if results.get(j[0])]
    keep = {t["file"] for t in tracks}
    for t in cat.get("tracks", []):                               # ملف انشال من المصدر؟ نبقيه بالمكتبة بس ننبّه
        if t["source"]["file"] not in results and t["file"] not in keep and os.path.exists(os.path.join(LIB, t["file"])):
            tracks.append(t); print(f"  ℹ️ {t['source']['file']} مو بالمجلد الحين — بقّيته بالمكتبة")
    cat = {"version": 1, "lufs": a.lufs, "built": time.strftime("%Y-%m-%d"), "source_dir": src_dir,
           "moods": MOODS, "uses": USES, "tracks": tracks}
    save_cat(cat)
    mins = sum(t["duration"] for t in tracks) / 60
    print(f"✅ المكتبة جاهزة: {len(tracks)} ملف · {mins:.0f} دقيقة · {time.time() - t0:.0f} ث\n"
          f"   التالي: صنّفها بأذنك ← python {os.path.basename(__file__)} page")


# ───────────────────────── اختيار ─────────────────────────
def score(t, use, mood, dur, rng):
    if t.get("hidden"): return None
    if t["duration"] < 15: return None                            # مقطع قصير (لمحة/ختام) — لفّه يبان، ما يصلح خلفية
    s = 0.0
    if mood:
        if t.get("mood") == mood: s += 3
        elif t.get("mood"): return None                           # مصنّف بطابع ثاني
        else: s -= 1                                              # ما تصنّف بعد — يدخل بس بعد المصنّف
    e = t.get("energy", 0.5)
    if use == "montage":
        s += (2 if beat_ok(t) else -2) + 1 - abs(e - 0.7)
    elif use == "motion":
        s += (1 if beat_ok(t) else 0) + 1 - abs(e - 0.55)
    elif use == "podcast":
        s += 1.2 - abs(e - 0.3) * 1.5 + (0.4 if t["duration"] >= 180 else 0)
    else:                                                         # reel: تحت الكلام = هادئ ما يزاحم
        s += 1.2 - abs(e - 0.35) * 1.5
    if dur:
        s += 0.5 if t["duration"] - t.get("start", 0) >= dur + 1 else -0.5
    s += 0.6 * (t.get("rating") or 0) - 0.3 * min(t.get("used") or 0, 5)
    return s + rng.uniform(0, 0.4)                                # تنويع: ما يطلع نفس الثلاثة كل مرة


def video_dur(work):
    for n in ("ad-final.mp4", "ad-master.mp4", "montage.mp4", "episode-wide.mp4", os.path.join("renders", "video.mp4")):
        p = os.path.join(work, n)
        if os.path.exists(p):
            try: return probe(p)[0]
            except Exception: pass
    c = os.path.join(work, "caps.json")
    if os.path.exists(c):
        try:
            with open(c, encoding="utf-8") as f: return float(json.load(f).get("total") or 0) or None
        except Exception: pass
    return None


def find_track(cat, key, work=None):
    """يرجع (الملف، مدة الفيديو من suggest لو الاختيار بحرف)."""
    k, dur = key.strip(), None
    if work and len(k) == 1 and k.isalpha():
        sj = os.path.join(work, "bg-suggest.json")
        if not os.path.exists(sj): die("ما فيه bg-suggest.json — شغّل suggest أول أو اكتب رقم الملف")
        with open(sj, encoding="utf-8") as f: sug = json.load(f)
        k, dur = sug["letters"].get(k.upper()) or die(f"ما فيه خيار {k}"), sug.get("dur")
    if k.isdigit(): k = f"{int(k):02d}"
    t = next((x for x in cat["tracks"] if x["id"] == k), None)
    return (t or die(f"ما لقيت {key} بالمكتبة")), dur


def cmd_list(a):
    cat = load_cat(); rng = random.Random(0)
    rows = cat["tracks"]
    if a.use or a.mood:
        sc = [(score(t, a.use or "reel", a.mood, None, rng), t) for t in rows]
        rows = [t for s, t in sorted([x for x in sc if x[0] is not None], key=lambda x: -x[0])]
    tagged = sum(1 for t in cat["tracks"] if t.get("mood"))
    print(f"🎧 {len(cat['tracks'])} ملف · صنّفت {tagged} · {LIB}")
    for t in rows:
        mood = MOODS.get(t.get("mood"), "—")
        print(f"  {t['id']:>3}  {label(t)[:34]:<34} {mmss(t['duration']):>6}  {t['bpm']:>5.0f} BPM  "
              f"{energy_word(t['energy']):<5} {'🥁' if beat_ok(t) else '  '}  {mood:<6} {'★' * (t.get('rating') or 0):<3}"
              f"{'  (مخفي)' if t.get('hidden') else ''}{'  (لمحة قصيرة — ما تنقترح خلفية)' if t['duration'] < 15 else ''}")


def cmd_suggest(a):
    cat = load_cat(); work = os.path.abspath(a.work); os.makedirs(work, exist_ok=True)
    dur = a.dur or video_dur(work)
    rng = random.Random(a.seed if a.seed is not None else time.time())
    sc = [(score(t, a.use, a.mood, dur, rng), t) for t in cat["tracks"]]
    best = [t for s, t in sorted([x for x in sc if x[0] is not None], key=lambda x: -x[0])][:a.n]
    if not best: die("ما لقيت شي يناسب — جرّب بلا --mood أو صنّف ملفات أكثر بالصفحة")
    if a.mood and not any(t.get("mood") for t in cat["tracks"]):
        print("ℹ️ ما فيه ملفات مصنّفة بعد — الاختيار بالإيقاع والطاقة بس (صنّفها بـpage)")
    pv = os.path.join(work, "bg-previews"); os.makedirs(pv, exist_ok=True)
    for f in os.listdir(pv):
        if re.match(r"^[A-Z]-.*\.mp3$", f): os.remove(os.path.join(pv, f))
    letters = {}
    print(f"🎧 خلفيات مقترحة لـ{USES[a.use]}" + (f" · {MOODS[a.mood]}" if a.mood else "") + (f" · الفيديو {mmss(dur)}" if dur else ""))
    for i, t in enumerate(best):
        L = chr(65 + i); letters[L] = t["id"]
        out = os.path.join(pv, f"{L}-{os.path.splitext(t['file'])[0]}.mp3")
        s0 = t.get("start", 0); ln = min(20.0, max(4.0, t["duration"] - s0))
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{ln:.2f}", "-i", os.path.join(LIB, t["file"]),
             "-af", f"afade=t=in:d=0.3,afade=t=out:st={max(0, ln - 1.5):.2f}:d=1.5", "-c:a", "libmp3lame", "-q:a", "5", out])
        loop = " · يلف بتلاشٍ" if dur and t["duration"] - s0 < dur + 1 else ""
        print(f"  {L}) #{t['id']} {label(t)} — {mmss(t['duration'])} · {t['bpm']:.0f} BPM · طاقة {energy_word(t['energy'])}"
              f"{' · إيقاع واضح' if beat_ok(t) else ''}{' · ' + MOODS[t['mood']] if t.get('mood') else ''}{loop}")
        print(f"     🔈 {out}")
    with open(os.path.join(work, "bg-suggest.json"), "w", encoding="utf-8") as f:
        json.dump({"use": a.use, "mood": a.mood, "dur": dur, "letters": letters}, f, ensure_ascii=False, indent=1)
    print(f"   اختار:  python {os.path.basename(__file__)} pick {work} A")


def cmd_pick(a):
    cat = load_cat(); work = os.path.abspath(a.work); os.makedirs(work, exist_ok=True)
    t, sug_dur = find_track(cat, a.key, work)
    src = os.path.join(LIB, t["file"])
    if not os.path.exists(src): die(f"الملف {t['file']} مو موجود بالمكتبة — أعد build")
    s0 = t.get("start", 0.0) if a.start is None else float(a.start)
    need = a.dur or video_dur(work) or sug_dur
    seg = t["duration"] - s0
    out = os.path.join(work, "bg-audio.mp3"); tmp = out + ".part.mp3"
    enc = ["-c:a", "libmp3lame", "-q:a", "2", "-ar", "48000", "-ac", "2"]
    if need and need + 1.0 > seg and seg > 6:
        xf = 2.0                                                  # الفيديو أطول من الملف: نلفّه بتلاشٍ متقاطع بدل قفزة
        k = 1 + math.ceil((need + 1.0 - seg) / (seg - xf))
        ins = sum([["-ss", f"{s0:.3f}", "-i", src] for _ in range(k)], [])
        ch, last = [], "[0:a]"
        for i in range(1, k):
            ch.append(f"{last}[{i}:a]acrossfade=d={xf}:c1=qsin:c2=qsin[x{i}]"); last = f"[x{i}]"
        ch.append(f"{last}atrim=0:{need + 1.0:.3f}[o]")
        run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(ch), "-map", "[o]"] + enc + [tmp])
        how = f"لفّيته {k} مرات بتلاشٍ {xf:.0f} ث"
    else:
        lim = ["-t", f"{need + 3.0:.3f}"] if need else []
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}"] + lim + ["-i", src, "-vn"] + enc + [tmp])
        how = "مقطع واحد بلا لف"
    os.replace(tmp, out)
    info = {"id": t["id"], "title": label(t), "artist": t.get("artist"), "library_file": t["file"],
            "source_file": t["source"]["file"], "start": s0, "duration": round(probe(out)[0], 2),
            "picked": time.strftime("%Y-%m-%d %H:%M"), "library": LIB}
    with open(os.path.join(work, "bg-audio.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    with LOCK:                                                    # عدّاد الاستخدام محلي — ما يدخل المزامنة
        loc = local_tags(); loc["used"][t["id"]] = loc["used"].get(t["id"], 0) + 1; write_json(TAGS, loc)
    print(f"✅ {out}\n   #{t['id']} {label(t)} · يبدأ من {s0:.2f} ث · {mmss(info['duration'])} · {how}")
    print("   التالي: المونتاج ← beat.py على هالملف · الريل/البودكاست ← 06b_master.sh يقراه وحده")


# ───────────────────────── المزامنة مع قت هب ─────────────────────────
def git(args, cwd=None, timeout=180):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, timeout=timeout, env=dict(ENV, GIT_TERMINAL_PROMPT="0"))
    out = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
    if r.returncode:
        raise RuntimeError((out.splitlines() or [f"git {args[0]} فشل"])[-1])
    return out


@lru_cache(maxsize=1)
def worktree():
    """جذر المستودع لو المكتبة نفسها نسخة git لها origin (مستودعك على الجهاز، أو جلسة السحابة)."""
    try:
        top = git(["rev-parse", "--show-toplevel"], cwd=LIB, timeout=15)
        git(["remote", "get-url", "origin"], cwd=top, timeout=15)
        return os.path.realpath(top)
    except Exception:
        return None


def sync_target():
    return worktree() or read_json(CAT, {}).get("repo")


def pick_user(*cands):
    best = max((c for c in cands if c), key=lambda c: c.get("tagged_at") or 0, default={})
    return {k: best.get(k, USER[k]) for k in USER}


def merge_cat(base, others, tags):
    """base يحدد الملفات وبياناتها؛ التصنيف من أحدث مصدر (tagged_at) بين الكل + احتياط هالجهاز."""
    idx = [{t["id"]: t for t in o.get("tracks", [])} for o in others if o]
    seen, out = set(), []
    for t in base.get("tracks", []) + [t for i in idx for t in i.values()]:
        if t["id"] in seen: continue
        seen.add(t["id"])
        nt = {k: v for k, v in t.items() if k != "used"}
        nt.update(pick_user(t, *[i.get(t["id"]) for i in idx], tags.get(t["id"])))
        out.append(nt)
    return dict(base, tracks=out)


def ident():
    name = email = ""
    try: name = git(["config", "user.name"], timeout=10)
    except Exception: pass
    try: email = git(["config", "user.email"], timeout=10)
    except Exception: pass
    return ["-c", f"user.name={name or 'halal-audio sync'}", "-c", f"user.email={email or 'halal-audio@users.noreply.github.com'}"]


def do_sync(push=True):
    """(نجح؟، رسالة). مستودع على الجهاز: يدمج ويرفع halal-audio/ كله. نسخة بلقن: نسخة مؤقتة فيها catalog.json بس."""
    tmp = None
    try:
        with LOCK:
            loc, local = local_tags(), read_json(CAT, {"tracks": []})
            top = worktree()
            if top:
                rel = os.path.relpath(CAT, top).replace("\\", "/")
                remote = None
                try:
                    up = git(["rev-parse", "--abbrev-ref", "@{u}"], cwd=top, timeout=15)
                    git(["fetch", "-q"], cwd=top)
                    remote = json.loads(git(["show", f"{up}:{rel}"], cwd=top))
                except Exception:
                    up = None
                merged = merge_cat(local, [remote], loc["tags"])          # الملفات من هالنسخة (هني ينبني الجديد)
                if up:
                    git(["checkout", "--", rel], cwd=top)
                    git(ident() + ["pull", "--rebase", "--autostash", "-q"], cwd=top)
                write_json(CAT, merged)
                files = ["add", "-A", os.path.relpath(LIB, top).replace("\\", "/")]
                work, gtop = CAT, top
            else:
                repo = local.get("repo")
                if not repo: return False, "ما أعرف رابط المستودع — catalog.json ← repo"
                tmp = tempfile.mkdtemp(prefix="halal-sync-")
                git(["clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", repo, tmp])
                git(["sparse-checkout", "set", "--no-cone", "/halal-audio/catalog.json"], cwd=tmp)
                git(["checkout", "-q"], cwd=tmp)
                work, gtop = os.path.join(tmp, "halal-audio", "catalog.json"), tmp
                merged = merge_cat(read_json(work, {"tracks": []}), [local], loc["tags"])   # الملفات من قت هب
                write_json(work, merged)
                files = ["add", "halal-audio/catalog.json"]
            pushed = False
            if push:
                git(ident() + files, cwd=gtop)
                if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=gtop).returncode:
                    host = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "جهاز"
                    git(ident() + ["commit", "-q", "-m", f"halal-audio: مزامنة التصنيف من {host}"], cwd=gtop)
                    try: git(["push", "-q"], cwd=gtop)
                    except RuntimeError:
                        git(ident() + ["pull", "--rebase", "-q"], cwd=gtop); git(["push", "-q"], cwd=gtop)
                    pushed = True
            if work != CAT:
                try: write_json(CAT, merged)
                except OSError: pass
            loc["tags"] = {t["id"]: {k: t.get(k) for k in USER} for t in merged["tracks"] if t.get("tagged_at")}
            write_json(TAGS, loc)
        n = len(loc["tags"])
        return True, (f"تزامن ✓ — {n} ملف مصنّف" + (" · رفعت تصنيف هالجهاز" if pushed else ""))
    except Exception as e:
        return False, f"ما قدرت أزامن: {e}"
    finally:
        if tmp: shutil.rmtree(tmp, ignore_errors=True)


def cmd_sync(a):
    if not os.path.exists(CAT): die(f"ما فيه مكتبة ({LIB})")
    ok, msg = do_sync(push=not a.pull)
    print(("✅ " if ok else "❌ ") + msg)
    sys.exit(0 if ok else 1)


def cmd_where(a):
    cat = read_json(CAT, None)
    print(f"🎧 المكتبة: {LIB}  ({LIB_FROM}{'' if cat else ' — ما فيها catalog.json'})")
    if cat:
        loc = local_tags()
        print(f"   {len(cat.get('tracks', []))} ملف · مصنّف بهالجهاز {len(loc['tags'])} · "
              f"المزامنة: {'نسخة git' if worktree() else (cat.get('repo') or 'غير مضبوطة')}")


# ───────────────────────── صفحة التصنيف ─────────────────────────
def cmd_page(a):
    import http.server, webbrowser
    load_cat()
    page = os.path.join(HERE, "bg-library.html")
    font = os.path.join(os.path.dirname(HERE), "motion", "fonts", "Cairo-VF.ttf")

    def clean(k, v):
        if k == "mood": return v if v in MOODS else None
        if k == "name": return (str(v).strip()[:80] or None) if v else None
        if k == "rating": return max(0, min(3, int(v or 0)))
        if k == "beat_user": return None if v is None else bool(v)
        if k == "hidden": return bool(v)
        if k == "notes": return str(v or "")[:300]
        raise KeyError(k)

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *x): pass

        def _send(self, code, body, ctype, extra=None):
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _file(self, path, ctype):
            size = os.path.getsize(path); rg = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            a0 = int(rg.group(1)) if rg and rg.group(1) else 0
            b0 = min(int(rg.group(2)) if rg and rg.group(2) else size - 1, size - 1)
            if a0 > b0: return self.send_error(416)
            self.send_response(206 if rg else 200); self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes")
            if rg: self.send_header("Content-Range", f"bytes {a0}-{b0}/{size}")
            self.send_header("Content-Length", str(b0 - a0 + 1)); self.end_headers()
            with open(path, "rb") as f:
                f.seek(a0); left = b0 - a0 + 1
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk: break
                    try: self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError): break
                    left -= len(chunk)

        def do_GET(self):
            p = self.path.split("?")[0]
            if p in ("/", "/index.html"):
                with open(page, "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if p == "/catalog.json":
                with LOCK: return self._json(200, dict(load_cat(), _sync=bool(sync_target())))
            if p == "/fonts/Cairo-VF.ttf" and os.path.exists(font): return self._file(font, "font/ttf")
            if p.startswith("/a/"):
                from urllib.parse import unquote
                name = os.path.basename(unquote(p[3:]))
                f = os.path.join(LIB, name)
                if name.lower().endswith(".mp3") and os.path.isfile(f): return self._file(f, "audio/mpeg")
            self.send_error(404)

        def do_POST(self):
            p = self.path.split("?")[0]
            if p == "/api/sync":
                ok, msg = do_sync(push=True)
                return self._json(200 if ok else 500, {"ok": ok, "message": msg})
            if p != "/api/save": return self.send_error(404)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
                with LOCK:
                    cat = load_cat()
                    t = next((x for x in cat["tracks"] if x["id"] == body.get("id")), None)
                    if not t: return self._json(404, {"error": "ما لقيت الملف"})
                    for k, v in body.items():
                        if k not in ("id", "tagged_at", "used"): t[k] = clean(k, v)
                    t["tagged_at"] = time.time()
                    loc = local_tags(); loc["tags"][t["id"]] = {k: t.get(k) for k in USER}; write_json(TAGS, loc)
                    try: save_cat(cat)
                    except OSError: pass                              # نسخة للقراءة بس؟ التصنيف محفوظ بالاحتياط
                return self._json(200, {k: t.get(k) for k in USER})
            except (KeyError, ValueError, TypeError) as e:
                return self._json(400, {"error": f"قيمة غير صالحة: {e}"})

    if sync_target():                                             # يجيب تصنيف أجهزتك الثانية قبل ما تفتح الصفحة
        ok, msg = do_sync(push=False); print(("🔄 " if ok else "⚠️ ") + msg)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H)      # الجهاز بس — ما ينفتح على الشبكة
    url = f"http://127.0.0.1:{a.port}/"
    print(f"🎧 صفحة المكتبة شغّالة: {url}\n   المكتبة: {LIB} ({LIB_FROM}) · Ctrl+C للإيقاف")
    if not a.no_open: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n👋 وقّفت الصفحة")


def main():
    ap = argparse.ArgumentParser(description="مكتبة الخلفيات الصوتية الحلال")
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build"); b.add_argument("src"); b.add_argument("--lufs", type=float, default=-16.0)
    b.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 2)); b.add_argument("--force", action="store_true")
    l = sp.add_parser("list"); l.add_argument("--use", choices=list(USES)); l.add_argument("--mood", choices=list(MOODS))
    s = sp.add_parser("suggest"); s.add_argument("work"); s.add_argument("--use", choices=list(USES), default="reel")
    s.add_argument("--mood", choices=list(MOODS)); s.add_argument("--dur", type=float); s.add_argument("--n", type=int, default=3)
    s.add_argument("--seed", type=int)
    p = sp.add_parser("pick"); p.add_argument("work"); p.add_argument("key"); p.add_argument("--dur", type=float)
    p.add_argument("--from", dest="start", type=float)
    g = sp.add_parser("page"); g.add_argument("--port", type=int, default=8793); g.add_argument("--no-open", action="store_true")
    y = sp.add_parser("sync"); y.add_argument("--pull", action="store_true")
    sp.add_parser("where")
    a = ap.parse_args()
    {"build": cmd_build, "list": cmd_list, "suggest": cmd_suggest, "pick": cmd_pick, "page": cmd_page,
     "sync": cmd_sync, "where": cmd_where}[a.cmd](a)


if __name__ == "__main__":
    main()
