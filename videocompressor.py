"""
Compressor  -  Professional Video & Text Compressor
Blue / Black theme  |  Animated progress bar  |  Auto-installs FFmpeg
Python 3.8+  (only stdlib + tkinter needed)
"""

import os, re, gzip, zlib, bz2, lzma, json, shutil, platform, math
import threading, subprocess, urllib.request, zipfile, tarfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# ─────────────────────────────────────────────────────────────
#  FFMPEG AUTO-INSTALL
# ─────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
FFMPEG_DIR = SCRIPT_DIR / "ffmpeg_bin"
SYSTEM     = platform.system()
FFMPEG_URLS = {
    "Windows": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "Darwin":  "https://evermeet.cx/ffmpeg/getrelease/zip",
    "Linux":   "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
}

def _local_bin(name):
    pat = name + (".exe" if SYSTEM == "Windows" else "")
    for c in FFMPEG_DIR.rglob(pat):
        if c.is_file() and os.access(str(c), os.X_OK):
            return str(c)
    return None

def ffmpeg_exe():  return shutil.which("ffmpeg")  or _local_bin("ffmpeg")
def ffprobe_exe(): return shutil.which("ffprobe") or _local_bin("ffprobe")

def install_ffmpeg_auto(log_cb=None, prog_cb=None):
    if SYSTEM not in FFMPEG_URLS:
        raise RuntimeError("Auto-install unavailable.\nhttps://ffmpeg.org/download.html")
    url = FFMPEG_URLS[SYSTEM]
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
    arc = FFMPEG_DIR / ("dl" + (".zip" if url.endswith(".zip") else ".tar.xz"))
    if log_cb: log_cb("Downloading FFmpeg…")
    def hook(b, bs, tot):
        if tot > 0 and prog_cb: prog_cb(min(78, int(b * bs / tot * 78)))
    try:
        urllib.request.urlretrieve(url, str(arc), reporthook=hook)
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}")
    if log_cb: log_cb("Extracting…")
    if prog_cb: prog_cb(82)
    try:
        if str(arc).endswith(".zip"):
            with zipfile.ZipFile(arc) as z: z.extractall(FFMPEG_DIR)
        else:
            with tarfile.open(arc, "r:xz") as t: t.extractall(FFMPEG_DIR)
    except Exception as e:
        raise RuntimeError(f"Extract failed: {e}")
    arc.unlink(missing_ok=True)
    for f in list(FFMPEG_DIR.rglob("ffmpeg*")) + list(FFMPEG_DIR.rglob("ffprobe*")):
        if f.is_file() and not f.suffix:
            f.chmod(0o755)
    p = _local_bin("ffmpeg")
    if not p:
        raise RuntimeError("Binary not found after extract.\nhttps://ffmpeg.org/download.html")
    if log_cb: log_cb(f"Done! {p}")
    if prog_cb: prog_cb(100)
    return p

# ─────────────────────────────────────────────────────────────
#  FORMAT TABLES
# ─────────────────────────────────────────────────────────────
TEXT_ALGORITHMS = {
    "gzip  (balanced)":   "gzip",
    "bz2   (high ratio)": "bz2",
    "lzma  (maximum)":    "lzma",
    "zlib  (fast)":       "zlib",
}
TEXT_EXT = {".txt",".csv",".json",".xml",".html",".htm",".md",
            ".log",".py",".js",".css",".ts",".yaml",".yml",
            ".toml",".ini",".cfg",".sql"}
VIDEO_FORMATS = {
    ".mp4":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=["-movflags","+faststart"], ea=[], fmt=None),
    ".mkv":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt=None),
    ".avi":  dict(codec="libxvid",    acodec="libmp3lame", two_pass=True,
                  ev=[], ea=[], fmt="avi"),
    ".mov":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=["-movflags","+faststart"], ea=[], fmt=None),
    ".webm": dict(codec="libvpx",     acodec="libvorbis",  two_pass=True,
                  ev=["-deadline","good","-cpu-used","2"], ea=[], fmt="webm"),
    ".flv":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt="flv"),
    ".wmv":  dict(codec="wmv2",       acodec="wmav2",      two_pass=False,
                  ev=[], ea=[], fmt="asf"),
    ".m4v":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=["-movflags","+faststart"], ea=[], fmt=None),
    ".3gp":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=["-profile:v","baseline","-level","3.0"],
                  ea=["-ac","1"], fmt="3gp"),
    ".ts":   dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt="mpegts"),
    ".mpeg": dict(codec="mpeg2video", acodec="mp2",        two_pass=True,
                  ev=[], ea=[], fmt="mpeg"),
    ".mpg":  dict(codec="mpeg2video", acodec="mp2",        two_pass=True,
                  ev=[], ea=[], fmt="mpeg"),
    ".ogv":  dict(codec="libtheora",  acodec="libvorbis",  two_pass=False,
                  ev=[], ea=[], fmt="ogg"),
    ".vob":  dict(codec="mpeg2video", acodec="ac3",        two_pass=True,
                  ev=[], ea=[], fmt="vob"),
    ".f4v":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt="flv"),
    ".mts":  dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt="mpegts"),
    ".m2ts": dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt="mpegts"),
    ".divx": dict(codec="libxvid",    acodec="libmp3lame", two_pass=True,
                  ev=[], ea=[], fmt="avi"),
    ".rmvb": dict(codec="libx264",    acodec="aac",        two_pass=True,
                  ev=[], ea=[], fmt=None),
}
VIDEO_EXT = set(VIDEO_FORMATS.keys())
ALL_EXT   = TEXT_EXT | VIDEO_EXT

SIZE_PRESETS = [
    ("10 KB",   10),     ("50 KB",   50),     ("100 KB",  100),
    ("500 KB",  500),    ("1 MB",    1024),    ("5 MB",    5120),
    ("10 MB",   10240),  ("25 MB",   25600),   ("50 MB",   51200),
    ("100 MB",  102400), ("250 MB",  256000),  ("500 MB",  512000),
    ("1 GB",    1048576),
]

# ─────────────────────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────────────────────
def human_size(b):
    b = float(b)
    if b < 1024: return f"{b:.0f} B"
    for u in ("KB", "MB", "GB"):
        b /= 1024
        if b < 1024: return f"{b:.2f} {u}"
    return f"{b:.2f} TB"

def get_file_size(p): return os.path.getsize(p)

def lerp_color(c1, c2, t):
    """Interpolate between two #rrggbb hex colors."""
    t = max(0.0, min(1.0, t))
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"

# ─────────────────────────────────────────────────────────────
#  TEXT COMPRESSION
# ─────────────────────────────────────────────────────────────
def compress_text(src, dst, algo, target_kb, cb=None):
    tb   = int(target_kb * 1024)
    orig = get_file_size(src)
    if cb: cb(8, "Reading file…")
    with open(src, "rb") as f: data = f.read()
    EXT = {"gzip":".gz","bz2":".bz2","lzma":".xz","zlib":".zlib"}
    if not dst.endswith(EXT[algo]): dst += EXT[algo]
    best, bd = None, float("inf")
    if algo == "gzip":
        for lv in range(1, 10):
            c = gzip.compress(data, compresslevel=lv)
            d = abs(len(c) - tb)
            if d < bd: bd, best = d, c
            if cb: cb(10+lv*8, f"gzip level {lv}  →  {human_size(len(c))}")
    elif algo == "bz2":
        for lv in range(1, 10):
            c = bz2.compress(data, compresslevel=lv)
            d = abs(len(c) - tb)
            if d < bd: bd, best = d, c
            if cb: cb(10+lv*8, f"bz2 level {lv}  →  {human_size(len(c))}")
    elif algo == "lzma":
        for i, pr in enumerate(range(10)):
            try: c = lzma.compress(data, preset=pr)
            except: continue
            d = abs(len(c) - tb)
            if d < bd: bd, best = d, c
            if cb: cb(10+i*8, f"lzma preset {pr}  →  {human_size(len(c))}")
    else:
        for lv in range(0, 10):
            c = zlib.compress(data, level=lv)
            d = abs(len(c) - tb)
            if d < bd: bd, best = d, c
            if cb: cb(10+lv*8, f"zlib level {lv}  →  {human_size(len(c))}")
    if cb: cb(93, "Writing output…")
    with open(dst, "wb") as f: f.write(best)
    cs = get_file_size(dst)
    if cb: cb(100, "Done!")
    return dict(original_size=orig, compressed_size=cs,
                ratio=(1-cs/orig)*100 if orig else 0,
                output_path=dst, target_bytes=tb,
                accuracy_pct=abs(cs-tb)/tb*100)

# ─────────────────────────────────────────────────────────────
#  VIDEO COMPRESSION
# ─────────────────────────────────────────────────────────────
def get_video_info(src):
    fp = ffprobe_exe()
    if not fp: return 0.0, 0, 0, False
    try:
        r = subprocess.run(
            [fp,"-v","quiet","-print_format","json",
             "-show_streams","-show_format", src],
            capture_output=True, text=True, timeout=30)
        inf = json.loads(r.stdout)
        dur = float(inf.get("format",{}).get("duration", 0))
        w = h = 0; ha = False
        for s in inf.get("streams", []):
            if s.get("codec_type") == "video": w, h = s.get("width",0), s.get("height",0)
            if s.get("codec_type") == "audio": ha = True
        return dur, w, h, ha
    except: return 0.0, 0, 0, False

def _stream_ff(proc, dur, cb, sp, ep, lbl):
    tr = re.compile(r"time=(\d+):(\d+):([\d.]+)")
    for line in proc.stderr:
        m = tr.search(line)
        if m and dur > 0:
            cur = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
            if cb: cb(sp + (ep-sp)*min(cur/dur, 1.0),
                      f"{lbl}  {cur:.0f}s / {dur:.0f}s")

def compress_video(src, dst, target_kb, cb=None):
    ff = ffmpeg_exe()
    if not ff: raise RuntimeError("__FFMPEG_MISSING__")
    ox = Path(dst).suffix.lower()
    if ox not in VIDEO_FORMATS:
        raise ValueError(f"Output format '{ox}' not supported.\n"
                         f"Supported: {', '.join(sorted(VIDEO_FORMATS))}")
    cfg  = VIDEO_FORMATS[ox]
    tb   = int(target_kb * 1024)
    orig = get_file_size(src)
    dur, w, h, ha = get_video_info(src)
    if dur <= 0: raise ValueError("Cannot read video duration.")
    ak  = 64 if ha else 0
    tk2 = max(10, (target_kb * 8) / dur)
    vk  = max(10, tk2 - ak)
    ak  = min(ak, tk2)
    if cb: cb(4, f"Duration {dur:.0f}s  |  {w}x{h}  |  {tk2:.0f} kbps  |  {ox}")
    plog = str(Path(dst).parent / (Path(dst).stem + "_ffpass"))

    def run(args, lbl, sp, ep):
        proc = subprocess.Popen([ff, "-y"] + args,
                                stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                text=True, bufsize=1)
        _stream_ff(proc, dur, cb, sp, ep, lbl)
        proc.wait()
        return proc.returncode

    vf = ["-c:v", cfg["codec"], "-b:v", f"{vk:.0f}k"] + cfg["ev"]
    af = (["-c:a", cfg["acodec"], "-b:a", f"{ak:.0f}k"] + cfg["ea"]
          if ha else ["-an"])
    ff2 = (["-f", cfg["fmt"]] if cfg["fmt"] else [])

    if cfg["two_pass"]:
        if cb: cb(8, "Pass 1/2 — analysing…")
        if run(["-i",src]+vf+["-pass","1","-passlogfile",plog,
                               "-an","-f","null",os.devnull],
               "Pass 1", 8, 48) != 0:
            raise RuntimeError("FFmpeg pass-1 failed. Check source file & output format.")
        if cb: cb(50, "Pass 2/2 — encoding…")
        if run(["-i",src]+vf+["-pass","2","-passlogfile",plog]+af+ff2+[dst],
               "Pass 2", 50, 95) != 0:
            raise RuntimeError("FFmpeg pass-2 failed.")
        for f in Path(dst).parent.glob(Path(plog).name + "*"):
            try: f.unlink()
            except: pass
    else:
        if cb: cb(10, "Encoding (single pass)…")
        if run(["-i",src]+vf+af+ff2+[dst], "Encoding", 10, 95) != 0:
            raise RuntimeError("FFmpeg encoding failed.")

    cs = get_file_size(dst)
    if cb: cb(100, "Done!")
    return dict(original_size=orig, compressed_size=cs,
                ratio=(1-cs/orig)*100 if orig else 0,
                output_path=dst, target_bytes=tb,
                accuracy_pct=abs(cs-tb)/tb*100)

# ─────────────────────────────────────────────────────────────
#  ANIMATED CANVAS PROGRESS BAR
# ─────────────────────────────────────────────────────────────
class AnimatedProgress(tk.Canvas):
    """Smooth animated progress bar drawn on a Canvas."""
    HEIGHT  = 24
    CLR_BG  = "#060e1f"   # trough background
    CLR_TRK = "#0d1f40"   # track fill
    CLR_A   = "#1a56db"   # bar left colour
    CLR_B   = "#60a5fa"   # bar right colour
    CLR_GLW = "#93c5fd"   # glow highlight

    def __init__(self, parent, width=640, **kw):
        super().__init__(parent,
                         width=width, height=self.HEIGHT,
                         bg=self.CLR_BG,
                         highlightthickness=0, bd=0, **kw)
        self._bar_w    = width
        self._pct      = 0.0
        self._target   = 0.0
        self._shimmer  = 0.0
        self._running  = False
        # Draw only after the widget is actually mapped
        self.after(50, self._safe_draw)

    # public API
    def set_value(self, pct):
        self._target = max(0.0, min(100.0, float(pct)))
        if not self._running:
            self._running = True
            self.after(16, self._tick)

    def reset(self):
        self._pct = 0.0
        self._target = 0.0
        self._shimmer = 0.0
        self._running = False
        self.after(50, self._safe_draw)

    # internal
    def _safe_draw(self):
        try:
            self._draw()
        except tk.TclError:
            pass

    def _tick(self):
        diff = self._target - self._pct
        self._pct += diff * 0.14
        if abs(diff) < 0.05:
            self._pct = self._target

        if self._pct > 2:
            self._shimmer = (self._shimmer + 0.02) % 1.0

        self._safe_draw()

        if abs(self._target - self._pct) > 0.05 or (self._pct > 2 and self._running):
            self.after(16, self._tick)
        else:
            self._running = False

    def _draw(self):
        self.delete("all")
        W = self._bar_w
        H = self.HEIGHT
        R = H // 2   # radius for rounded ends

        # --- track ---
        self._rrect(0, 0, W, H, R, self.CLR_TRK)

        if self._pct < 0.5:
            return

        # --- filled bar ---
        fw = max(R, int((self._pct / 100.0) * W))
        fw = min(fw, W)

        # gradient segments
        segs = 40
        for i in range(segs):
            x1 = int(i / segs * fw)
            x2 = int((i+1) / segs * fw)
            col = lerp_color(self.CLR_A, self.CLR_B, i / segs)
            self.create_rectangle(x1, 0, x2+1, H, fill=col, outline="")

        # shimmer sweep
        if self._pct > 4 and fw > 10:
            sx = int(self._shimmer * (fw + 40)) - 20
            for dx in range(-12, 13):
                xi = sx + dx
                if 0 <= xi < fw:
                    alpha = 1.0 - abs(dx) / 13.0
                    col = lerp_color(self.CLR_B, "#ffffff", alpha * 0.4)
                    self.create_line(xi, 0, xi, H, fill=col)

        # top glow line
        self.create_line(R, 1, fw - R, 1, fill=self.CLR_GLW, width=1)

        # mask left/right rounded corners over bar
        self._rrect_mask(0, 0, W, H, R)

        # left cap
        self.create_oval(0, 0, R*2, H, fill=self.CLR_A, outline="")

        # right cap (only if bar doesn't fill full width)
        if fw < W - R:
            self.create_oval(fw - R*2, 0, fw, H, fill=self.CLR_B, outline="")

        # percentage text
        if self._pct >= 5:
            txt = f"{self._pct:.0f}%"
            tx  = min(fw // 2, W - 20)
            self.create_text(tx+1, H//2+1, text=txt,
                             font=("Segoe UI", 8, "bold"), fill="#1a2a4a")
            self.create_text(tx,   H//2,   text=txt,
                             font=("Segoe UI", 8, "bold"), fill="white")

    def _rrect(self, x1, y1, x2, y2, r, fill):
        """Filled rounded rectangle."""
        self.create_arc(x1,    y1,    x1+2*r, y1+2*r, start=90,  extent=90,  fill=fill, outline="")
        self.create_arc(x2-2*r,y1,    x2,     y1+2*r, start=0,   extent=90,  fill=fill, outline="")
        self.create_arc(x1,    y2-2*r,x1+2*r, y2,     start=180, extent=90,  fill=fill, outline="")
        self.create_arc(x2-2*r,y2-2*r,x2,     y2,     start=270, extent=90,  fill=fill, outline="")
        self.create_rectangle(x1+r, y1,   x2-r, y2,   fill=fill, outline="")
        self.create_rectangle(x1,   y1+r, x2,   y2-r, fill=fill, outline="")

    def _rrect_mask(self, x1, y1, x2, y2, r):
        """Draw BG-colour arcs over corners to fake rounding."""
        bg = self.CLR_BG
        self.create_arc(x1,    y1,    x1+2*r, y1+2*r, start=90,  extent=90,  fill=bg, outline="")
        self.create_arc(x2-2*r,y1,    x2,     y1+2*r, start=0,   extent=90,  fill=bg, outline="")
        self.create_arc(x1,    y2-2*r,x1+2*r, y2,     start=180, extent=90,  fill=bg, outline="")
        self.create_arc(x2-2*r,y2-2*r,x2,     y2,     start=270, extent=90,  fill=bg, outline="")

# ─────────────────────────────────────────────────────────────
#  FFMPEG INSTALL DIALOG
# ─────────────────────────────────────────────────────────────
class FFmpegDialog(tk.Toplevel):
    BG     = "#04091a"
    CARD   = "#08112b"
    BORDER = "#1a3a6a"
    ACC    = "#3b82f6"
    TEXT   = "#e2e8f0"
    DIM    = "#64748b"
    YELLOW = "#fbbf24"

    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.title("Install FFmpeg")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.grab_set()
        self._on_success = on_success
        self._build()
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()//2  - self.winfo_width()//2
        py = parent.winfo_y() + parent.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{px}+{py}")

    def _build(self):
        # header
        hdr = tk.Frame(self, bg=self.ACC)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  FFmpeg Required",
                 font=("Segoe UI",13,"bold"),
                 bg=self.ACC, fg="white",
                 pady=14).pack(side="left", padx=10)

        body = tk.Frame(self, bg=self.BG, padx=22, pady=14)
        body.pack(fill="x")
        tk.Label(body,
                 text=f"FFmpeg is needed for video compression.\nDetected OS: {SYSTEM}",
                 font=("Segoe UI",9), bg=self.BG, fg=self.TEXT,
                 justify="left").pack(anchor="w")

        manual = {
            "Windows": "winget install ffmpeg",
            "Darwin":  "brew install ffmpeg",
            "Linux":   "sudo apt install ffmpeg",
        }.get(SYSTEM, "https://ffmpeg.org/download.html")

        mbox = tk.Frame(body, bg=self.CARD,
                        highlightthickness=1, highlightbackground=self.BORDER)
        mbox.pack(fill="x", pady=(10,0))
        tk.Label(mbox, text=f"  Manual:  {manual}  ",
                 font=("Courier New",8), bg=self.CARD, fg=self.DIM,
                 pady=7).pack(anchor="w")

        pf = tk.Frame(self, bg=self.BG, padx=22)
        pf.pack(fill="x", pady=(8,0))
        self._log_var = tk.StringVar(value="Click Auto Install to begin.")
        tk.Label(pf, textvariable=self._log_var,
                 font=("Segoe UI",8), bg=self.BG, fg=self.DIM,
                 anchor="w", wraplength=420).pack(fill="x")
        self._dlprog = AnimatedProgress(pf, width=440)
        self._dlprog.pack(pady=6)

        bf = tk.Frame(self, bg=self.BG, pady=14, padx=22)
        bf.pack(fill="x")
        self._ibtn = tk.Button(
            bf, text="  Auto Install  ",
            font=("Segoe UI",10,"bold"),
            bg=self.ACC, fg="white",
            activebackground="#2563eb", activeforeground="white",
            relief="flat", bd=0, pady=8, cursor="hand2",
            command=self._start_install)
        self._ibtn.pack(side="left", padx=(0,10))
        tk.Button(bf, text="Cancel",
                  font=("Segoe UI",9),
                  bg=self.CARD, fg=self.DIM,
                  activebackground=self.BORDER,
                  relief="flat", bd=0, padx=14, pady=8,
                  cursor="hand2", command=self.destroy).pack(side="left")

    def _start_install(self):
        self._ibtn.config(state="disabled", text="Installing…")
        def worker():
            try:
                path = install_ffmpeg_auto(
                    log_cb=lambda m: self.after(0, lambda: self._log_var.set(m)),
                    prog_cb=lambda v: self.after(0, lambda: self._dlprog.set_value(v)))
                self.after(0, lambda: self._done(path))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._fail(msg))
        threading.Thread(target=worker, daemon=True).start()

    def _done(self, path):
        messagebox.showinfo("Installed!", f"FFmpeg is ready!\n\n{path}", parent=self)
        self.destroy()
        self._on_success()

    def _fail(self, msg):
        self._ibtn.config(state="normal", text="  Retry  ")
        messagebox.showerror("Failed", f"{msg}\n\nTry manual install.", parent=self)

# ─────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────
class App(tk.Tk):
    # ── Palette ──────────────────────────────────────────
    BG      = "#04091a"
    SURFACE = "#070f28"
    CARD    = "#0a1530"
    CARD2   = "#0d1c3d"
    BORDER  = "#162d5c"
    BORDER2 = "#1e3d7a"
    ACC     = "#1a56db"
    ACC2    = "#3b82f6"
    ACC3    = "#60a5fa"
    ACC4    = "#93c5fd"
    GREEN   = "#22c55e"
    RED     = "#ef4444"
    YELLOW  = "#fbbf24"
    TEXT    = "#e2e8f0"
    TEXT2   = "#94a3b8"
    DIM     = "#475569"
    # ── Fonts ────────────────────────────────────────────
    F_TITLE = ("Segoe UI", 20, "bold")
    F_H2    = ("Segoe UI", 10, "bold")
    F_BODY  = ("Segoe UI",  9)
    F_SMALL = ("Segoe UI",  8)
    F_MONO  = ("Courier New", 9)

    WIN_W   = 760
    MIN_KB  = 10

    def __init__(self):
        super().__init__()
        self.title("Compressor")
        self.configure(bg=self.BG)
        self.resizable(False, False)

        # ── All instance variables MUST be set before _build() ──
        self._src_sv         = tk.StringVar()
        self._dst_sv         = tk.StringVar()
        self._algo_var       = tk.StringVar(value=list(TEXT_ALGORITHMS)[0])
        self._out_fmt        = tk.StringVar(value=".mp4")
        self._status_sv      = tk.StringVar(value="Select a file to get started")
        self._target_kb      = 500.0
        self._compress_busy  = False   # renamed to avoid any leftover references
        # Widget refs (assigned during _build)
        self._file_info_lbl  = None
        self._preset_btns    = {}
        self._num_entry      = None
        self._unit           = None
        self._unit_btns      = {}
        self._target_big_lbl = None
        self._target_sub_lbl = None
        self._fmt_btns       = {}
        self._fmt_info_lbl   = None
        self._progbar        = None
        self._pct_lbl        = None
        self._result_canvas  = None
        self._result_text    = None
        self._compress_btn   = None
        self._ff_status_lbl  = None
        self._ff_install_btn = None

        self._build()
        self._check_ffmpeg()

    # ─────────────────────────────────────────────────────
    #  BUILD UI
    # ─────────────────────────────────────────────────────
    def _build(self):
        W = self.WIN_W

        # ── TOP BAR ──────────────────────────────────────
        topbar = tk.Frame(self, bg=self.ACC, height=54)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="  Compressor",
                 font=self.F_TITLE, bg=self.ACC, fg="white"
                 ).pack(side="left", padx=(16,0))

        self._ff_install_btn = tk.Button(
            topbar, text="Install FFmpeg",
            font=("Segoe UI",8,"bold"),
            bg=self.YELLOW, fg="#0d0d0d",
            activebackground="#f59e0b", activeforeground="#0d0d0d",
            relief="flat", bd=0, padx=10, pady=4,
            cursor="hand2", command=self._open_install)
        # packed only when FFmpeg is missing

        self._ff_status_lbl = tk.Label(
            topbar, text="", font=self.F_SMALL,
            bg=self.ACC, fg="#bfdbfe")
        self._ff_status_lbl.pack(side="right", padx=12)

        # ── SCROLLABLE BODY ───────────────────────────────
        wrapper = tk.Frame(self, bg=self.BG)
        wrapper.pack(fill="both", expand=True)

        self._scroll_canvas = tk.Canvas(
            wrapper, bg=self.BG, highlightthickness=0,
            width=W, height=600)
        self._scroll_canvas.pack(side="left", fill="both", expand=True)

        vsb = tk.Scrollbar(wrapper, orient="vertical",
                           command=self._scroll_canvas.yview)
        vsb.pack(side="right", fill="y")
        self._scroll_canvas.configure(yscrollcommand=vsb.set)

        self._inner = tk.Frame(self._scroll_canvas, bg=self.BG, width=W)
        self._win_id = self._scroll_canvas.create_window(
            0, 0, anchor="nw", window=self._inner)

        self._inner.bind("<Configure>", self._on_inner_cfg)
        self._scroll_canvas.bind("<Configure>", self._on_canvas_cfg)
        self._scroll_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(
                -1 if e.delta > 0 else 1, "units"))

        F = self._inner

        # ── STEP 1 : FILE ─────────────────────────────────
        self._section_header(F, "01", "Select File")
        fc = self._card(F)

        row_src = tk.Frame(fc, bg=self.CARD2)
        row_src.pack(fill="x", pady=(0,8))
        tk.Label(row_src, text="INPUT ", font=("Courier New",7,"bold"),
                 bg=self.CARD2, fg=self.DIM).pack(side="left")
        tk.Entry(row_src, textvariable=self._src_sv,
                 font=self.F_BODY, bg=self.SURFACE, fg=self.TEXT,
                 insertbackground=self.ACC3,
                 relief="flat", bd=0,
                 highlightthickness=1,
                 highlightcolor=self.ACC2,
                 highlightbackground=self.BORDER2
                 ).pack(side="left", fill="x", expand=True, padx=(6,8), ipady=6)
        tk.Button(row_src, text="Browse",
                  font=self.F_BODY, bg=self.ACC, fg="white",
                  activebackground=self.ACC3, activeforeground="white",
                  relief="flat", bd=0, padx=14, pady=5,
                  cursor="hand2", command=self._browse_src
                  ).pack(side="left")

        row_dst = tk.Frame(fc, bg=self.CARD2)
        row_dst.pack(fill="x")
        tk.Label(row_dst, text="OUTPUT", font=("Courier New",7,"bold"),
                 bg=self.CARD2, fg=self.DIM).pack(side="left")
        tk.Entry(row_dst, textvariable=self._dst_sv,
                 font=self.F_BODY, bg=self.SURFACE, fg=self.TEXT,
                 insertbackground=self.ACC3,
                 relief="flat", bd=0,
                 highlightthickness=1,
                 highlightcolor=self.ACC2,
                 highlightbackground=self.BORDER2
                 ).pack(side="left", fill="x", expand=True, padx=(6,8), ipady=6)
        tk.Button(row_dst, text="Browse",
                  font=self.F_BODY, bg=self.SURFACE, fg=self.ACC3,
                  activebackground=self.BORDER2, activeforeground=self.ACC3,
                  relief="flat", bd=0, padx=14, pady=5,
                  cursor="hand2", command=self._browse_dst
                  ).pack(side="left")

        self._file_info_lbl = tk.Label(
            fc, text="No file selected",
            font=self.F_SMALL, bg=self.CARD2, fg=self.DIM, anchor="w")
        self._file_info_lbl.pack(fill="x", pady=(8,0))

        # ── STEP 2 : TARGET SIZE ──────────────────────────
        self._section_header(F, "02", "Set Target Size")
        sc = self._card(F)

        # Preset buttons grid
        pg = tk.Frame(sc, bg=self.CARD2)
        pg.pack(fill="x", pady=(0,10))
        COLS = 5
        for idx, (lbl, kb) in enumerate(SIZE_PRESETS):
            rr, cc = divmod(idx, COLS)
            b = tk.Button(pg, text=lbl,
                          font=("Segoe UI",8,"bold"),
                          bg=self.SURFACE, fg=self.TEXT2,
                          activebackground=self.ACC,
                          activeforeground="white",
                          relief="flat", bd=0,
                          width=8, pady=6,
                          cursor="hand2",
                          command=lambda k=kb, l=lbl: self._pick_preset(k, l))
            b.grid(row=rr, column=cc, padx=3, pady=3, sticky="ew")
            self._preset_btns[kb] = b
        for cc in range(COLS):
            pg.columnconfigure(cc, weight=1)

        # Divider line
        div = tk.Frame(sc, bg=self.CARD2)
        div.pack(fill="x", pady=4)
        tk.Frame(div, bg=self.BORDER, height=1).pack(
            side="left", fill="x", expand=True, pady=7)
        tk.Label(div, text="  or enter custom size  ",
                 font=("Segoe UI",8), bg=self.CARD2, fg=self.DIM
                 ).pack(side="left")
        tk.Frame(div, bg=self.BORDER, height=1).pack(
            side="left", fill="x", expand=True, pady=7)

        # Custom size row
        cr = tk.Frame(sc, bg=self.CARD2)
        cr.pack(fill="x", pady=(0,10))

        # Number entry
        nb = tk.Frame(cr, bg=self.SURFACE,
                      highlightthickness=1, highlightbackground=self.BORDER2)
        nb.pack(side="left", padx=(0,10))
        self._num_entry = tk.Entry(
            nb, width=6,
            font=("Segoe UI",18,"bold"),
            bg=self.SURFACE, fg=self.ACC3,
            insertbackground=self.ACC3,
            justify="center", relief="flat", bd=0)
        self._num_entry.insert(0, "500")
        self._num_entry.pack(padx=10, pady=6)
        self._num_entry.bind("<Return>",    self._apply_custom)
        self._num_entry.bind("<FocusOut>",  self._apply_custom)
        self._num_entry.bind("<KeyRelease>",self._apply_custom)

        # Unit buttons (KB / MB / GB)
        uf = tk.Frame(cr, bg=self.CARD2)
        uf.pack(side="left", padx=(0,16))
        self._unit = tk.StringVar(value="KB")
        for u in ("KB", "MB", "GB"):
            b = tk.Button(uf, text=u,
                          font=("Segoe UI",9,"bold"),
                          bg=self.SURFACE, fg=self.TEXT2,
                          activebackground=self.ACC,
                          activeforeground="white",
                          relief="flat", bd=0,
                          width=4, pady=5,
                          cursor="hand2",
                          command=lambda uu=u: self._set_unit(uu))
            b.pack(pady=2)
            self._unit_btns[u] = b

        # Target display box
        tbox_outer = tk.Frame(cr, bg=self.ACC2, padx=2, pady=2)
        tbox_outer.pack(side="left", fill="x", expand=True)
        tbox = tk.Frame(tbox_outer, bg=self.CARD2)
        tbox.pack(fill="both", expand=True)
        tk.Label(tbox, text="Target Size",
                 font=("Segoe UI",8), bg=self.CARD2, fg=self.DIM
                 ).pack(pady=(8,0))
        self._target_big_lbl = tk.Label(
            tbox, text="500.00 KB",
            font=("Segoe UI",20,"bold"), bg=self.CARD2, fg=self.ACC3)
        self._target_big_lbl.pack()
        self._target_sub_lbl = tk.Label(
            tbox, text="500 KB",
            font=("Segoe UI",8), bg=self.CARD2, fg=self.DIM)
        self._target_sub_lbl.pack(pady=(0,8))

        # Initialise unit and preset
        self._set_unit("KB")
        self._pick_preset(500, "500 KB")

        # ── STEP 3 : OPTIONS ─────────────────────────────
        self._section_header(F, "03", "Options")
        oc = self._card(F)

        # Video format selector
        tk.Label(oc, text="Video Output Format",
                 font=self.F_H2, bg=self.CARD2, fg=self.TEXT2
                 ).pack(anchor="w", pady=(0,6))

        fmt_grid = tk.Frame(oc, bg=self.CARD2)
        fmt_grid.pack(fill="x", pady=(0,4))
        FCOLS = 10
        for idx, fmt in enumerate(sorted(VIDEO_FORMATS.keys())):
            rr, cc = divmod(idx, FCOLS)
            b = tk.Button(fmt_grid, text=fmt,
                          font=("Courier New",7,"bold"),
                          bg=self.SURFACE, fg=self.TEXT2,
                          activebackground=self.ACC,
                          activeforeground="white",
                          relief="flat", bd=0,
                          padx=4, pady=4, width=5,
                          cursor="hand2",
                          command=lambda f=fmt: self._pick_fmt(f))
            b.grid(row=rr, column=cc, padx=2, pady=2)
            self._fmt_btns[fmt] = b

        self._fmt_info_lbl = tk.Label(
            oc, text="",
            font=self.F_SMALL, bg=self.CARD2, fg=self.DIM, anchor="w")
        self._fmt_info_lbl.pack(fill="x", pady=(0,8))
        self._pick_fmt(".mp4")   # safe — _fmt_info_lbl exists now

        # Text algorithm selector
        ta_row = tk.Frame(oc, bg=self.CARD2)
        ta_row.pack(fill="x")
        tk.Label(ta_row, text="Text Algorithm",
                 font=self.F_H2, bg=self.CARD2, fg=self.TEXT2
                 ).pack(side="left", padx=(0,12))
        for lab in TEXT_ALGORITHMS:
            tk.Radiobutton(
                ta_row, text=lab, variable=self._algo_var, value=lab,
                font=("Courier New",8), bg=self.CARD2, fg=self.TEXT2,
                selectcolor=self.ACC,
                activebackground=self.CARD2,
                activeforeground=self.ACC3
            ).pack(side="left", padx=5)

        # ── COMPRESS BUTTON ───────────────────────────────
        btn_row = tk.Frame(F, bg=self.BG)
        btn_row.pack(fill="x", padx=24, pady=10)
        self._compress_btn = tk.Button(
            btn_row,
            text="   COMPRESS NOW   ",
            font=("Segoe UI",13,"bold"),
            bg=self.ACC2, fg="white",
            activebackground=self.ACC3,
            activeforeground="white",
            relief="flat", bd=0, pady=12,
            cursor="hand2",
            command=self._start_compress)
        self._compress_btn.pack(fill="x")

        # ── PROGRESS ─────────────────────────────────────
        self._section_header(F, "", "Progress")
        pc = self._card(F)

        top_row = tk.Frame(pc, bg=self.CARD2)
        top_row.pack(fill="x", pady=(0,6))
        tk.Label(top_row, text="Compressing…",
                 font=self.F_H2, bg=self.CARD2, fg=self.TEXT2
                 ).pack(side="left")
        self._pct_lbl = tk.Label(
            top_row, text="0%",
            font=("Segoe UI",10,"bold"), bg=self.CARD2, fg=self.ACC3)
        self._pct_lbl.pack(side="right")

        self._progbar = AnimatedProgress(pc, width=W - 96)
        self._progbar.pack(fill="x", pady=(0,6))

        tk.Label(pc, textvariable=self._status_sv,
                 font=self.F_SMALL, bg=self.CARD2, fg=self.DIM, anchor="w"
                 ).pack(fill="x")

        # ── RESULT ───────────────────────────────────────
        self._section_header(F, "", "Result")
        rc2 = self._card(F)

        self._result_canvas = tk.Canvas(
            rc2, bg=self.CARD2, highlightthickness=0, height=140)
        self._result_canvas.pack(fill="x")
        self._result_canvas.after(100, self._draw_result_idle)

        self._result_text = tk.Text(
            rc2, height=7,
            bg=self.CARD2, fg=self.TEXT,
            font=self.F_MONO, relief="flat", bd=0,
            padx=12, pady=8, state="disabled",
            insertbackground=self.TEXT)
        self._result_text.pack(fill="x", pady=(8,0))
        self._result_text.tag_config("grn", foreground=self.GREEN)
        self._result_text.tag_config("red", foreground=self.RED)
        self._result_text.tag_config("yel", foreground=self.YELLOW)
        self._result_text.tag_config("blu", foreground=self.ACC3)
        self._result_text.tag_config("dim", foreground=self.DIM)

        # bottom padding
        tk.Frame(F, bg=self.BG, height=24).pack()

    # ─────────────────────────────────────────────────────
    #  WIDGET HELPERS
    # ─────────────────────────────────────────────────────
    def _section_header(self, parent, num, title):
        row = tk.Frame(parent, bg=self.BG)
        row.pack(fill="x", padx=24, pady=(14,4))
        if num:
            badge = tk.Canvas(row, width=26, height=26,
                              bg=self.BG, highlightthickness=0)
            badge.pack(side="left", padx=(0,10))
            badge.create_oval(0, 0, 26, 26, fill=self.ACC, outline="")
            badge.create_text(13, 13, text=num,
                              font=("Segoe UI",8,"bold"), fill="white")
        tk.Label(row, text=title,
                 font=("Segoe UI",11,"bold"),
                 bg=self.BG, fg=self.ACC3).pack(side="left")
        tk.Frame(row, bg=self.BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(10,0), pady=6)

    def _card(self, parent):
        c = tk.Frame(parent, bg=self.CARD2,
                     highlightthickness=1, highlightbackground=self.BORDER2,
                     padx=18, pady=14)
        c.pack(fill="x", padx=24, pady=(0,4))
        return c

    # ─────────────────────────────────────────────────────
    #  SCROLL
    # ─────────────────────────────────────────────────────
    def _on_inner_cfg(self, e):
        self._scroll_canvas.configure(
            scrollregion=self._scroll_canvas.bbox("all"))

    def _on_canvas_cfg(self, e):
        self._scroll_canvas.itemconfig(self._win_id, width=e.width)

    # ─────────────────────────────────────────────────────
    #  FFMPEG STATUS
    # ─────────────────────────────────────────────────────
    def _check_ffmpeg(self):
        if ffmpeg_exe():
            self._ff_status_lbl.config(text="FFmpeg ready", fg="#bfdbfe")
            self._ff_install_btn.pack_forget()
        else:
            self._ff_status_lbl.config(text="FFmpeg missing", fg=self.YELLOW)
            self._ff_install_btn.pack(side="right", padx=8)

    def _open_install(self):
        FFmpegDialog(self, on_success=self._check_ffmpeg)

    # ─────────────────────────────────────────────────────
    #  SIZE PICKER
    # ─────────────────────────────────────────────────────
    def _pick_preset(self, kb, label):
        self._target_kb = float(kb)
        for k, b in self._preset_btns.items():
            b.config(bg=self.ACC if k == kb else self.SURFACE,
                     fg="white" if k == kb else self.TEXT2)
        # sync entry + unit
        if kb >= 1048576:
            self._num_entry.delete(0, "end")
            self._num_entry.insert(0, f"{kb/1048576:.0f}")
            self._set_unit("GB")
        elif kb >= 1024:
            self._num_entry.delete(0, "end")
            self._num_entry.insert(0, f"{kb/1024:.0f}")
            self._set_unit("MB")
        else:
            self._num_entry.delete(0, "end")
            self._num_entry.insert(0, str(int(kb)))
            self._set_unit("KB")
        self._refresh_target(kb)

    def _set_unit(self, u):
        self._unit.set(u)
        for k, b in self._unit_btns.items():
            b.config(bg=self.ACC if k == u else self.SURFACE,
                     fg="white" if k == u else self.TEXT2)

    def _apply_custom(self, _=None):
        try:
            v = float(self._num_entry.get())
        except ValueError:
            return
        u = self._unit.get()
        if u == "MB": v *= 1024
        elif u == "GB": v *= 1048576
        v = max(float(self.MIN_KB), v)
        self._target_kb = v
        for k, b in self._preset_btns.items():
            b.config(bg=self.ACC if abs(k - v) < 1 else self.SURFACE,
                     fg="white" if abs(k - v) < 1 else self.TEXT2)
        self._refresh_target(v)

    def _refresh_target(self, kb):
        kb = float(kb)
        txt = human_size(kb * 1024)
        self._target_big_lbl.config(text=txt)
        if kb >= 1048576:
            sub = f"{kb/1048576:.2f} GB  =  {kb:.0f} KB"
        elif kb >= 1024:
            sub = f"{kb/1024:.2f} MB  =  {kb:.0f} KB"
        else:
            sub = f"{kb:.0f} KB"
        self._target_sub_lbl.config(text=sub)

    # ─────────────────────────────────────────────────────
    #  FORMAT PICKER
    # ─────────────────────────────────────────────────────
    def _pick_fmt(self, fmt):
        self._out_fmt.set(fmt)
        for f, b in self._fmt_btns.items():
            b.config(bg=self.ACC if f == fmt else self.SURFACE,
                     fg="white" if f == fmt else self.TEXT2)
        c = VIDEO_FORMATS.get(fmt, {})
        info = (f"  codec: {c.get('codec','?')}   "
                f"audio: {c.get('acodec','?')}   "
                f"{'2-pass' if c.get('two_pass') else '1-pass'}")
        self._fmt_info_lbl.config(text=info)
        dst = self._dst_sv.get()
        if dst:
            self._dst_sv.set(str(Path(dst).with_suffix(fmt)))

    # ─────────────────────────────────────────────────────
    #  FILE BROWSE
    # ─────────────────────────────────────────────────────
    def _browse_src(self):
        vid  = " ".join("*"+e for e in sorted(VIDEO_EXT))
        txt  = " ".join("*"+e for e in sorted(TEXT_EXT))
        all_ = " ".join("*"+e for e in sorted(ALL_EXT))
        path = filedialog.askopenfilename(
            title="Select file to compress",
            filetypes=[("All supported", all_),
                       ("Video files",   vid),
                       ("Text files",    txt),
                       ("All files",     "*.*")])
        if not path: return
        self._src_sv.set(path)
        p   = Path(path)
        ext = p.suffix.lower()
        out_ext = self._out_fmt.get() if ext in VIDEO_EXT else ext
        self._dst_sv.set(str(p.parent / (p.stem + "_compressed" + out_ext)))
        sz = get_file_size(path)
        self._file_info_lbl.config(
            text=f"  {p.name}     Original size: {human_size(sz)}")
        self._status_sv.set(f"File loaded  —  {human_size(sz)}")

    def _browse_dst(self):
        src = self._src_sv.get()
        de  = (self._out_fmt.get()
               if Path(src).suffix.lower() in VIDEO_EXT
               else (Path(src).suffix if src else ".mp4"))
        path = filedialog.asksaveasfilename(
            title="Save output as",
            defaultextension=de,
            filetypes=[("Video", " ".join("*"+e for e in sorted(VIDEO_EXT))),
                       ("Text",  " ".join("*"+e for e in sorted(TEXT_EXT))),
                       ("All files", "*.*")])
        if path: self._dst_sv.set(path)

    # ─────────────────────────────────────────────────────
    #  PROGRESS CALLBACK
    # ─────────────────────────────────────────────────────
    def _set_progress(self, pct, msg=""):
        pct = float(pct)
        self._progbar.set_value(pct)
        self._pct_lbl.config(text=f"{pct:.0f}%")
        if msg: self._status_sv.set(msg)
        self.update_idletasks()

    # ─────────────────────────────────────────────────────
    #  RESULT TEXT HELPERS
    # ─────────────────────────────────────────────────────
    def _rw(self, text, tag=None):
        self._result_text.config(state="normal")
        self._result_text.insert("end", text, tag or "")
        self._result_text.config(state="disabled")

    def _rc(self):
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.config(state="disabled")

    # ─────────────────────────────────────────────────────
    #  RESULT CANVAS
    # ─────────────────────────────────────────────────────
    def _draw_result_idle(self):
        try:
            cv = self._result_canvas
            cv.delete("all")
            W = cv.winfo_width() or 620
            H = cv.winfo_height() or 140
            cv.create_text(W//2, H//2,
                           text="Results will appear here after compression",
                           font=("Segoe UI",10), fill=self.DIM)
        except tk.TclError:
            pass

    def _draw_result_bars(self, orig, comp, tgt):
        try:
            cv = self._result_canvas
            cv.update_idletasks()
            cv.delete("all")
            W = cv.winfo_width() or 620
            H = 140
            if orig <= 0: return

            BAR_H   = 26
            LABEL_W = 88
            PAD     = 10
            bar_w   = W - LABEL_W - PAD * 2
            max_val = max(orig, comp, tgt, 1)

            def bar(y, val, color, label, val_str):
                fw = max(4, int(bar_w * val / max_val))
                # label
                cv.create_text(LABEL_W - 6, y + BAR_H//2,
                               text=label, font=("Segoe UI",8,"bold"),
                               fill=self.DIM, anchor="e")
                # track
                cv.create_rectangle(LABEL_W, y, LABEL_W+bar_w, y+BAR_H,
                                    fill=self.SURFACE, outline="")
                # gradient fill
                for i in range(fw):
                    col = lerp_color(color, "#ffffff", i / max(fw,1) * 0.25)
                    cv.create_line(LABEL_W+i, y, LABEL_W+i, y+BAR_H, fill=col)
                # value label
                cv.create_text(LABEL_W + fw + 6, y + BAR_H//2,
                               text=val_str,
                               font=("Segoe UI",8,"bold"),
                               fill=self.TEXT, anchor="w")

            bar(10,  orig, "#334155", "Original", human_size(orig))
            bar(50,  tgt,  self.ACC,  "Target",   human_size(tgt))
            col = self.GREEN if comp <= tgt * 1.1 else self.YELLOW
            bar(90,  comp, col,       "Result",   human_size(comp))
        except tk.TclError:
            pass

    # ─────────────────────────────────────────────────────
    #  COMPRESSION
    # ─────────────────────────────────────────────────────
    def _start_compress(self):
        if self._compress_busy: return

        src     = self._src_sv.get().strip()
        dst     = self._dst_sv.get().strip()
        in_ext  = Path(src).suffix.lower() if src else ""
        out_ext = Path(dst).suffix.lower() if dst else ""

        if not src or not os.path.isfile(src):
            messagebox.showerror("No File",
                                 "Please select a source file first."); return
        if not dst:
            messagebox.showerror("No Output",
                                 "Please specify an output path."); return
        is_vid = in_ext in VIDEO_EXT
        is_txt = in_ext in TEXT_EXT
        if not is_vid and not is_txt:
            messagebox.showwarning(
                "Unsupported Format",
                f"'{in_ext}' is not supported.\n\n"
                f"Video: {', '.join(sorted(VIDEO_EXT))}\n"
                f"Text : {', '.join(sorted(TEXT_EXT))}"); return
        if is_vid and out_ext not in VIDEO_FORMATS:
            messagebox.showerror(
                "Bad Output Format",
                f"'{out_ext}' is not supported.\n"
                f"Supported: {', '.join(sorted(VIDEO_FORMATS))}"); return

        self._compress_busy = True
        self._compress_btn.config(
            state="disabled", text="   Compressing…   ", bg=self.DIM)
        self._rc()
        self._draw_result_idle()
        self._progbar.reset()
        self._pct_lbl.config(text="0%")
        target = self._target_kb

        def worker():
            try:
                if is_vid:
                    r = compress_video(src, dst, target, self._set_progress)
                else:
                    algo = TEXT_ALGORITHMS[self._algo_var.get()]
                    r    = compress_text(src, dst, algo, target, self._set_progress)
                self.after(0, lambda: self._show_result(r, src, is_vid, out_ext))
            except Exception as exc:
                msg = str(exc)
                if "__FFMPEG_MISSING__" in msg:
                    self.after(0, self._no_ffmpeg)
                else:
                    self.after(0, lambda: self._show_error(msg))
            finally:
                self.after(0, self._compress_done)

        threading.Thread(target=worker, daemon=True).start()

    def _compress_done(self):
        self._compress_busy = False
        self._compress_btn.config(
            state="normal", text="   COMPRESS NOW   ", bg=self.ACC2)

    def _no_ffmpeg(self):
        self._progbar.reset()
        self._pct_lbl.config(text="0%")
        self._rc()
        self._rw("FFmpeg is required for video compression.\n", "yel")
        self._rw("Click  Install FFmpeg  in the top bar.\n", "dim")
        self._open_install()

    # ─────────────────────────────────────────────────────
    #  SHOW RESULTS
    # ─────────────────────────────────────────────────────
    def _show_result(self, r, src, is_vid, out_ext):
        orig  = r["original_size"]
        comp  = r["compressed_size"]
        ratio = r["ratio"]
        acc   = r["accuracy_pct"]
        tgt   = r["target_bytes"]
        out   = r["output_path"]
        saved = orig - comp
        over  = comp > tgt

        self._draw_result_bars(orig, comp, tgt)
        self._rc()

        if acc <= 10:  badge, a_tag = "Excellent", "grn"
        elif acc <= 25: badge, a_tag = "Good",      "yel"
        else:           badge, a_tag = "Off target", "red"

        self._rw("  File        ", "dim"); self._rw(f"{Path(src).name}\n")
        if is_vid:
            c = VIDEO_FORMATS.get(out_ext, {})
            self._rw("  Format      ", "dim")
            self._rw(f"{out_ext}  |  {c.get('codec','?')} / {c.get('acodec','?')}\n", "blu")
        self._rw("  Original    ", "dim"); self._rw(f"{human_size(orig)}\n")
        self._rw("  Target      ", "dim"); self._rw(f"{human_size(tgt)}\n", "blu")
        tag = "grn" if not over else "yel"
        self._rw("  Result      ", "dim")
        self._rw(f"{human_size(comp)}  ", tag)
        self._rw(f"({'over' if over else 'under'} by {human_size(abs(comp-tgt))})\n","dim")
        self._rw("  Reduction   ", "dim")
        self._rw(f"{ratio:.1f}%  (saved {human_size(saved)})\n",
                 "grn" if ratio > 0 else "red")
        self._rw("  Accuracy    ", "dim")
        self._rw(f"{badge}  +-{acc:.1f}% vs target\n", a_tag)
        self._rw("  Saved to    ", "dim"); self._rw(f"{out}\n")
        self._status_sv.set(
            f"Done  —  {human_size(comp)}   target: {human_size(tgt)}   "
            f"accuracy: +-{acc:.1f}%")

    def _show_error(self, msg):
        self._draw_result_idle()
        self._rc()
        self._rw("  Error\n\n", "red")
        self._rw(f"  {msg}\n", "dim")
        self._status_sv.set("Error — see details above.")
        self._progbar.reset()
        self._pct_lbl.config(text="0%")


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()