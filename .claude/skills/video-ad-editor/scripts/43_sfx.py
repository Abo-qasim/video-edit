# -*- coding: utf-8 -*-
"""🔔 مؤثرات صوتية حقيقية من حزم Sonniss المجانية — بلا تنزيل الحزم الكبيرة.

  python 43_sfx.py fetch <batch.json> <مجلد> --listings zip_listings.json [--cap 12] [--budget-mb 60]
        ← ينزّل الأصوات المختارة بس: يقرا بايتات كل ملف من داخل الـzip على سيرفر Sonniss (Range)،
          ويوقف عند أول --cap ثانية، ويحوّلها MP3 (ذروة ‎-3 dBFS) → <مجلد>/audio/NN.mp3 + list.json
          يتوقف فوراً لو السيرفر ما قبل التنزيل الجزئي (ما ينزّل zip كامل أبداً) أو تعدّى --budget-mb
  python 43_sfx.py review <مجلد> [--port 8794] [--no-open]
        ← صفحة «مقبول / مرفوض»: صوت صوت، والقرار ينحفظ بـ<مجلد>/decisions.json

batch.json = [{cat, lib, file, year, part, zip}] — من فهرس GDC Bundle Finder (أسماء الملفات بس، الصوت من Sonniss).
الترخيص: #GameAudioGDC — استخدام بإنتاجك بلا ذكر مصدر، ⛔ بلا إعادة رفع الملفات لمكان ثاني.
"""
# ── توافق ويندوز/UTF-8 ─────────────────────────────────────────────
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
# ──────────────────────────────────────────────────────────────────
import argparse, json, os, re, struct, subprocess, sys, tempfile, threading, time, urllib.request, zlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
LOCK = threading.Lock()
BYTES = [0]                                                     # كل اللي نزل من الشبكة (للميزانية)


def die(m):
    print("❌ " + m)
    sys.exit(2)


def write_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def read_json(p, default):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError):
        return default


# ───────────────────────── التنزيل الجزئي ─────────────────────────
class Budget(Exception): pass


CHUNK = 131072                                                  # قطع صغيرة: Cloudflare أحياناً يتجاهل Range الكبير ويرسل الـzip كامل


def read_range(url, a, b):
    """بايتات a..b بالضبط. رد 200 (= الـzip كامل) نقفله قبل ما نقرا منه، وننتظر ونعيد."""
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://downloads.sonniss.com/", "Range": f"bytes={a}-{b}"})
        r = urllib.request.urlopen(req, timeout=60)
        if r.status == 206:
            try: return r.read()
            finally: r.close()
        r.close(); time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("السيرفر ما قبل التنزيل الجزئي — وقفت قبل ما أنزّل شي")


def wav_target(buf, cap):
    """لو وصلنا ترويسة WAV كاملة: (بداية data، حجم fmt، بايتات cap ثانية، block_align) — وإلا None."""
    if len(buf) < 12 or buf[:4] != b"RIFF" or buf[8:12] != b"WAVE": return None
    i, fmt = 12, None
    while i + 8 <= len(buf):
        cid, size = buf[i:i + 4], struct.unpack("<I", buf[i + 4:i + 8])[0]
        if cid == b"fmt ":
            if i + 8 + size > len(buf): return None
            fmt = buf[i + 8:i + 8 + size]
        elif cid == b"data":
            if not fmt: return None
            byte_rate, align = struct.unpack("<I", fmt[8:12])[0], struct.unpack("<H", fmt[12:14])[0]
            return i + 8, fmt, min(size, byte_rate * cap), align
        i += 8 + size + (size & 1)
    return None


def fetch_one(it, listing, cap, budget):
    """يرجع بايتات WAV صالحة (أول cap ثانية) + هل انقصّ."""
    key = ("2023" if it["year"].startswith("2021") else it["year"]) + "/" + it["part"]
    ent = next((f for f in listing[key]["files"] if "__MACOSX" not in f[0] and f[0].split("/")[-1] == it["file"]), None)
    if not ent: raise RuntimeError("ما لقيت الملف بالفهرس")
    path, usize, method, csize, off = ent
    it.update(path=path, offset=off, csize=csize, method=method)
    pos, end = off, off + 30 + 65535 + csize                    # الترويسة المحلية + البيانات (والزيادة نتجاهلها)
    raw, out, start, tgt = b"", b"", None, None
    dec = zlib.decompressobj(-15) if method == 8 else None
    while pos < end:
        chunk = read_range(it["zip"], pos, min(pos + CHUNK, end) - 1)
        if not chunk: break
        pos += len(chunk)
        with LOCK:
            BYTES[0] += len(chunk)
            if BYTES[0] > budget: raise Budget()
        raw += chunk
        if start is None:
            if len(raw) < 30: continue
            if raw[:4] != b"PK\x03\x04": raise RuntimeError("ترويسة zip غلط")
            n, e = struct.unpack("<HH", raw[26:30])
            if len(raw) < 30 + n + e: continue
            raw = raw[30 + n + e:]; start = 0
            end = min(end, off + 30 + n + e + csize)              # نعرف الحين وين تخلص بيانات الملف بالضبط
        data = raw if dec else raw[:csize - len(out)]
        out += dec.decompress(data) if dec else data
        raw = b""
        if tgt is None: tgt = wav_target(out, cap)
        if tgt and len(out) >= tgt[0] + tgt[2]: break
        if dec and dec.eof: break
        if not dec and len(out) >= csize: break
    if not tgt: tgt = wav_target(out, cap)
    if not tgt: raise RuntimeError("مو WAV مفهوم")
    ds, fmt, need, align = tgt
    pcm = out[ds:ds + need]; pcm = pcm[:len(pcm) - len(pcm) % max(1, align)]
    truncated = need < struct.unpack("<I", out[ds - 4:ds])[0]
    hdr = b"fmt " + struct.pack("<I", len(fmt)) + fmt + (b"\0" if len(fmt) & 1 else b"")
    wav = b"RIFF" + struct.pack("<I", 4 + len(hdr) + 8 + len(pcm)) + b"WAVE" + hdr + b"data" + struct.pack("<I", len(pcm)) + pcm
    return wav, truncated


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    if r.returncode: raise RuntimeError((out.strip().splitlines() or ["ffmpeg"])[-1])
    return out


def to_mp3(wav, dst, truncated):
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.wav")
        with open(src, "wb") as f: f.write(wav)
        m = re.search(r"max_volume:\s*(-?[\d.]+) dB", run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", "volumedetect", "-f", "null", "-"]))
        gain = -3.0 - float(m.group(1)) if m else 0.0
        dur = float(json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", src]))["format"]["duration"])
        af = f"volume={gain:.2f}dB" + (f",afade=t=out:st={max(0, dur - 0.35):.2f}:d=0.35" if truncated else "")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ac", "2", "-ar", "48000", "-c:a", "libmp3lame", "-q:a", "2", dst])
        return round(dur, 2), round(gain, 1)


def clean_title(fn):
    t = os.path.splitext(fn)[0]
    t = re.sub(r"^(EFX (INT|EXT|SD) |GAF SFX\d+ - [A-Z]+ - |SW\d+_|CSFX-\d+_|Bluezone_BC\d+_)", "", t)
    t = re.sub(r"[_]+", " ", t).strip(" -.")
    return t


def cmd_fetch(a):
    batch = read_json(a.batch, None) or die("ما قدرت أقرا " + a.batch)
    listing = read_json(a.listings, None) or die("ما قدرت أقرا " + a.listings)
    out = os.path.abspath(a.out); os.makedirs(os.path.join(out, "audio"), exist_ok=True)
    budget = int(a.budget_mb * 1048576)
    items = [dict(it, id=f"{i + 1:02d}") for i, it in enumerate(batch)]
    t0 = time.time(); done = [0]

    def one(it):
        try:
            wav, trunc = fetch_one(it, listing, a.cap, budget)
            mp3 = f"{it['id']}.mp3"
            it["dur"], it["gain"] = to_mp3(wav, os.path.join(out, "audio", mp3), trunc)
            it.update(mp3=mp3, truncated=trunc, title=clean_title(it["file"]), ok=True)
            msg = f"✅ {it['dur']:.1f} ث{' (أول ' + str(a.cap) + ' ث)' if trunc else ''}"
        except Budget:
            it["ok"] = False; msg = "⛔ وقفت: تعدّى الميزانية"
        except Exception as e:
            it["ok"] = False; it["error"] = str(e)[:160]; msg = "⚠️ " + str(e)[:90]
        with LOCK:
            done[0] += 1
            print(f"  [{done[0]:>2}/{len(items)}] {it['id']} {it['cat']} · {it['file'][:48]:<48} {msg} · نزل {BYTES[0] / 1048576:.1f} MB", flush=True)

    print(f"🔔 {len(items)} صوت ← {out}  (أقصى {a.cap} ث للصوت · ميزانية {a.budget_mb:.0f} MB)")
    with ThreadPoolExecutor(max_workers=4) as ex: list(ex.map(one, items))
    good = [it for it in items if it.get("ok")]
    write_json(os.path.join(out, "list.json"), {"source": "Sonniss #GameAudioGDC bundles (2015–2026)", "license": "#GameAudioGDC — use in your productions, no attribution, no re-uploading",
                                                 "cap_seconds": a.cap, "downloaded_mb": round(BYTES[0] / 1048576, 1), "items": good})
    size = sum(os.path.getsize(os.path.join(out, "audio", it["mp3"])) for it in good) / 1048576
    print(f"✅ {len(good)}/{len(items)} جاهزة · نزل من الشبكة {BYTES[0] / 1048576:.1f} MB · على الجهاز {size:.1f} MB · {time.time() - t0:.0f} ث")
    bad = [it for it in items if not it.get("ok")]
    if bad: print("   ما نزل:", ", ".join(f"{it['id']} ({it.get('error', 'ميزانية')[:40]})" for it in bad))


# ───────────────────────── صفحة المراجعة ─────────────────────────
def cmd_review(a):
    import http.server, webbrowser
    out = os.path.abspath(a.dir)
    lst, dpath = os.path.join(out, "list.json"), os.path.join(out, "decisions.json")
    if not os.path.exists(lst): die("ما فيه list.json — شغّل fetch أول")
    page = os.path.join(HERE, "sfx-review.html")
    font = os.path.join(os.path.dirname(HERE), "motion", "fonts", "Cairo-VF.ttf")

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *x): pass

        def _send(self, code, body, ctype):
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def _json(self, code, obj): self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _file(self, path, ctype):
            size = os.path.getsize(path); rg = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            a0 = int(rg.group(1)) if rg and rg.group(1) else 0
            b0 = min(int(rg.group(2)) if rg and rg.group(2) else size - 1, size - 1)
            self.send_response(206 if rg else 200); self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes")
            if rg: self.send_header("Content-Range", f"bytes {a0}-{b0}/{size}")
            self.send_header("Content-Length", str(b0 - a0 + 1)); self.end_headers()
            with open(path, "rb") as f:
                f.seek(a0)
                try: self.wfile.write(f.read(b0 - a0 + 1))
                except (BrokenPipeError, ConnectionResetError): pass

        def do_GET(self):
            p = self.path.split("?")[0]
            if p in ("/", "/index.html"):
                with open(page, "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if p == "/list.json":
                with LOCK: return self._json(200, dict(read_json(lst, {}), decisions=read_json(dpath, {})))
            if p == "/fonts/Cairo-VF.ttf" and os.path.exists(font): return self._file(font, "font/ttf")
            if p.startswith("/a/"):
                name = os.path.basename(p[3:])
                f = os.path.join(out, "audio", name)
                if re.fullmatch(r"\d+\.mp3", name) and os.path.isfile(f): return self._file(f, "audio/mpeg")
            self.send_error(404)

        def do_POST(self):
            if self.path.split("?")[0] != "/api/decide": return self.send_error(404)
            try:
                b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
                if not re.fullmatch(r"\d+", str(b.get("id", ""))) or b.get("d") not in ("ok", "no", None): raise ValueError
                with LOCK:
                    d = read_json(dpath, {})
                    if b["d"] is None: d.pop(b["id"], None)
                    else: d[b["id"]] = b["d"]
                    write_json(dpath, d)
                return self._json(200, {"ok": True, "decisions": d})
            except (ValueError, TypeError):
                return self._json(400, {"error": "قرار غير صالح"})

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H)      # الجهاز بس
    url = f"http://127.0.0.1:{a.port}/"
    print(f"🔔 صفحة المراجعة شغّالة: {url}\n   القرارات تنحفظ بـ{dpath} · Ctrl+C للإيقاف", flush=True)
    if not a.no_open: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n👋 وقّفت الصفحة")


def main():
    ap = argparse.ArgumentParser(description="مؤثرات Sonniss — تنزيل جزئي ومراجعة")
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fetch"); f.add_argument("batch"); f.add_argument("out"); f.add_argument("--listings", required=True)
    f.add_argument("--cap", type=int, default=12); f.add_argument("--budget-mb", type=float, default=60)
    r = sp.add_parser("review"); r.add_argument("dir"); r.add_argument("--port", type=int, default=8794); r.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    {"fetch": cmd_fetch, "review": cmd_review}[a.cmd](a)


if __name__ == "__main__":
    main()
