"""
Compressor Pro  ─  Video & Text Compressor
Redesigned: Fixed layout (no scroll) · Screen Record · Webcam Record
Python 3.8+  ·  stdlib + tkinter only
Optional: pip install opencv-python mss pillow  (enables recording features)
"""

import os, re, gzip, zlib, bz2, lzma, json, shutil, platform, time
import threading, subprocess, urllib.request, zipfile, tarfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
#  FFMPEG AUTO-INSTALL
# ═══════════════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════════════
#  FORMAT TABLES
# ═══════════════════════════════════════════════════════════════════
TEXT_ALGORITHMS = {
    "gzip  (balanced)":   "gzip",
    "bz2   (high ratio)": "bz2",
    "lzma  (maximum)":    "lzma",
    "zlib  (fast)":       "zlib",
}
TEXT_EXT = {
    ".txt",".csv",".json",".xml",".html",".htm",".md",
    ".log",".py",".js",".css",".ts",".yaml",".yml",
    ".toml",".ini",".cfg",".sql",
}
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
    ".ogv":  dict(codec="libtheora",  acodec="libvorbis",  two_pass=False,
                  ev=[], ea=[], fmt="ogg"),
}
VIDEO_EXT = set(VIDEO_FORMATS.keys())
ALL_EXT   = TEXT_EXT | VIDEO_EXT

SIZE_PRESETS = [
    ("10 KB", 10), ("50 KB", 50), ("100 KB", 100), ("500 KB", 500),
    ("1 MB", 1024), ("5 MB", 5120), ("10 MB", 10240), ("25 MB", 25600),
    ("50 MB", 51200), ("100 MB", 102400), ("500 MB", 512000),
]

# ═══════════════════════════════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════════════════════════════
def human_size(b):
    b = float(b)
    if b < 1024: return f"{b:.0f} B"
    for u in ("KB", "MB", "GB"):
        b /= 1024
        if b < 1024: return f"{b:.2f} {u}"
    return f"{b:.2f} TB"

def get_file_size(p): return os.path.getsize(p)

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, float(t)))
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))

# ═══════════════════════════════════════════════════════════════════
#  TEXT COMPRESSION
# ═══════════════════════════════════════════════════════════════════
def compress_text(src, dst, algo, target_kb, cb=None):
    tb   = int(target_kb * 1024)
    orig = get_file_size(src)
    if cb: cb(8, "Reading file…")
    with open(src, "rb") as f:
        data = f.read()
    EXT = {"gzip": ".gz", "bz2": ".bz2", "lzma": ".xz", "zlib": ".zlib"}
    if not dst.endswith(EXT[algo]):
        dst += EXT[algo]
    best, bd = None, float("inf")
    levels = range(1, 10) if algo in ("gzip","bz2","lzma") else range(0, 10)
    for i, lv in enumerate(levels):
        try:
            if   algo == "gzip": c = gzip.compress(data, compresslevel=lv)
            elif algo == "bz2":  c = bz2.compress(data,  compresslevel=lv)
            elif algo == "lzma": c = lzma.compress(data, preset=lv)
            else:                c = zlib.compress(data, level=lv)
        except Exception:
            continue
        d = abs(len(c) - tb)
        if d < bd:
            bd, best = d, c
        if cb: cb(10 + i * 9, f"{algo} level {lv}  →  {human_size(len(c))}")
    if cb: cb(93, "Writing output…")
    with open(dst, "wb") as f:
        f.write(best)
    cs = get_file_size(dst)
    if cb: cb(100, "Done!")
    return dict(original_size=orig, compressed_size=cs,
                ratio=(1-cs/orig)*100 if orig else 0,
                output_path=dst, target_bytes=tb,
                accuracy_pct=abs(cs-tb)/tb*100)

# ═══════════════════════════════════════════════════════════════════
#  VIDEO COMPRESSION
# ═══════════════════════════════════════════════════════════════════
def get_video_info(src):
    fp = ffprobe_exe()
    if not fp: return 0.0, 0, 0, False
    try:
        r = subprocess.run(
            [fp, "-v","quiet","-print_format","json","-show_streams","-show_format", src],
            capture_output=True, text=True, timeout=30)
        inf = json.loads(r.stdout)
        dur = float(inf.get("format",{}).get("duration", 0))
        w = h = 0; ha = False
        for s in inf.get("streams", []):
            if s.get("codec_type") == "video": w, h = s.get("width",0), s.get("height",0)
            if s.get("codec_type") == "audio": ha = True
        return dur, w, h, ha
    except Exception:
        return 0.0, 0, 0, False

def _stream_ff(proc, dur, cb, sp, ep, lbl):
    tr = re.compile(r"time=(\d+):(\d+):([\d.]+)")
    for line in proc.stderr:
        m = tr.search(line)
        if m and dur > 0:
            cur = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
            if cb: cb(sp + (ep-sp)*min(cur/dur,1.0), f"{lbl}  {cur:.0f}s / {dur:.0f}s")

def compress_video(src, dst, target_kb, cb=None):
    ff = ffmpeg_exe()
    if not ff: raise RuntimeError("__FFMPEG_MISSING__")
    ox = Path(dst).suffix.lower()
    if ox not in VIDEO_FORMATS:
        raise ValueError(f"Output format '{ox}' not supported.")
    cfg  = VIDEO_FORMATS[ox]
    tb   = int(target_kb * 1024)
    orig = get_file_size(src)
    dur, w, h, ha = get_video_info(src)
    if dur <= 0: raise ValueError("Cannot read video duration. File may be corrupt.")
    ak  = 64 if ha else 0
    tk2 = max(10, (target_kb * 8) / dur)
    vk  = max(10, tk2 - ak)
    ak  = min(ak, tk2)
    if cb: cb(4, f"Duration {dur:.0f}s  |  {w}x{h}  |  {tk2:.0f} kbps  |  {ox}")
    plog = str(Path(dst).parent / (Path(dst).stem + "_ffpass"))

    def run(args, lbl, sp, ep):
        proc = subprocess.Popen([ff, "-y"] + args,
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        _stream_ff(proc, dur, cb, sp, ep, lbl)
        proc.wait()
        return proc.returncode

    vf  = ["-c:v", cfg["codec"], "-b:v", f"{vk:.0f}k"] + cfg["ev"]
    af  = (["-c:a", cfg["acodec"], "-b:a", f"{ak:.0f}k"] + cfg["ea"] if ha else ["-an"])
    ff2 = (["-f", cfg["fmt"]] if cfg["fmt"] else [])

    if cfg["two_pass"]:
        if cb: cb(8, "Pass 1/2 — analysing…")
        if run(["-i",src]+vf+["-pass","1","-passlogfile",plog,"-an","-f","null",os.devnull],
               "Pass 1", 8, 48) != 0:
            raise RuntimeError("FFmpeg pass-1 failed.")
        if cb: cb(50, "Pass 2/2 — encoding…")
        if run(["-i",src]+vf+["-pass","2","-passlogfile",plog]+af+ff2+[dst],
               "Pass 2", 50, 95) != 0:
            raise RuntimeError("FFmpeg pass-2 failed.")
        for f in Path(dst).parent.glob(Path(plog).name + "*"):
            try: f.unlink()
            except: pass
    else:
        if cb: cb(10, "Encoding…")
        if run(["-i",src]+vf+af+ff2+[dst], "Encoding", 10, 95) != 0:
            raise RuntimeError("FFmpeg encoding failed.")

    cs = get_file_size(dst)
    if cb: cb(100, "Done!")
    return dict(original_size=orig, compressed_size=cs,
                ratio=(1-cs/orig)*100 if orig else 0,
                output_path=dst, target_bytes=tb,
                accuracy_pct=abs(cs-tb)/tb*100)

# ═══════════════════════════════════════════════════════════════════
#  RECORDING OVERLAY  — floating on-screen badge visible while recording
# ═══════════════════════════════════════════════════════════════════
class RecordingOverlay(tk.Toplevel):
    """
    A small always-on-top borderless pill that floats over the desktop.
    Shows blinking ● REC  +  elapsed timer  +  a stop button.
    Draggable so user can reposition it anywhere.
    Call close() to destroy it.
    """
    W = 220; H = 52
    BG      = "#0f0a0a"
    RED     = "#ef4444"
    RED2    = "#fca5a5"
    DIMRED  = "#7f1d1d"
    TEXT    = "#fef2f2"
    DIM     = "#64748b"
    STOPBG  = "#1c0909"

    def __init__(self, root, on_stop, label="Screen"):
        super().__init__(root)
        self._on_stop  = on_stop
        self._label    = label
        self._elapsed  = 0
        self._tick_job = None
        self._dot_vis  = True
        self._drag_x   = 0
        self._drag_y   = 0

        # Position: bottom-right corner, a bit above taskbar
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = sw - self.W - 24
        y  = sh - self.H - 60
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

        self.overrideredirect(True)          # no title bar
        self.attributes("-topmost", True)    # always on top
        self.configure(bg=self.BG)
        try:
            self.attributes("-alpha", 0.93)  # slight transparency
        except Exception:
            pass

        self._build()
        self._tick()
        self._blink()

        # Drag to reposition
        self.bind("<ButtonPress-1>",   self._drag_start)
        self.bind("<B1-Motion>",       self._drag_move)

    # ── layout ───────────────────────────────────────
    def _build(self):
        # Outer red-glow border frame
        border = tk.Frame(self, bg=self.DIMRED, bd=0)
        border.place(x=0, y=0, width=self.W, height=self.H)

        inner = tk.Frame(border, bg=self.BG, bd=0)
        inner.place(x=1, y=1, width=self.W-2, height=self.H-2)

        # Left: blinking dot + REC label + timer
        left = tk.Frame(inner, bg=self.BG)
        left.pack(side="left", fill="y", padx=(10,4), pady=4)

        dot_row = tk.Frame(left, bg=self.BG)
        dot_row.pack(anchor="w")
        self._dot_cv = tk.Canvas(dot_row, bg=self.BG,
                                  highlightthickness=0, width=10, height=10)
        self._dot_cv.pack(side="left", pady=(1,0))
        self._dot = self._dot_cv.create_oval(1,1,9,9, fill=self.RED, outline="")
        tk.Label(dot_row, text=f" REC  ·  {self._label}",
                 font=("Segoe UI", 8, "bold"),
                 bg=self.BG, fg=self.RED2).pack(side="left")

        self._timer_lbl = tk.Label(left, text="00:00",
                 font=("Segoe UI", 18, "bold"),
                 bg=self.BG, fg=self.TEXT)
        self._timer_lbl.pack(anchor="w", pady=(0,2))

        # Right: stop button
        right = tk.Frame(inner, bg=self.BG)
        right.pack(side="right", fill="y", padx=(4,10), pady=8)
        stop_btn = tk.Button(right, text="■\nStop",
                 font=("Segoe UI", 7, "bold"),
                 bg=self.STOPBG, fg=self.RED2,
                 activebackground=self.RED, activeforeground="white",
                 relief="flat", bd=0, padx=8, pady=4,
                 cursor="hand2", command=self._stop_clicked)
        stop_btn.pack(expand=True)

        # Thin red top-edge accent line
        accent = tk.Frame(border, bg=self.RED, height=2)
        accent.place(x=1, y=1, width=self.W-2, height=2)

    # ── drag ─────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        nx = e.x_root - self._drag_x
        ny = e.y_root - self._drag_y
        self.geometry(f"+{nx}+{ny}")

    # ── animation ────────────────────────────────────
    def _tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        try:
            self._timer_lbl.config(text=f"{m:02d}:{s:02d}")
            self._tick_job = self.after(1000, self._tick)
        except tk.TclError:
            pass

    def _blink(self):
        try:
            self._dot_vis = not self._dot_vis
            self._dot_cv.itemconfig(
                self._dot, fill=self.RED if self._dot_vis else "#3b0000")
            self.after(600, self._blink)
        except tk.TclError:
            pass

    # ── stop ─────────────────────────────────────────
    def _stop_clicked(self):
        self.close()
        if self._on_stop:
            self._on_stop()

    def pause(self):
        """Called externally to indicate recording is paused."""
        try:
            self._dot_cv.itemconfig(self._dot, fill="#fbbf24")
            self._dot_vis = False
        except tk.TclError:
            pass

    def resume(self):
        """Called externally to indicate recording has resumed."""
        try:
            self._dot_cv.itemconfig(self._dot, fill=self.RED)
            self._dot_vis = True
        except tk.TclError:
            pass

    def close(self):
        if self._tick_job:
            try: self.after_cancel(self._tick_job)
            except: pass
        try: self.destroy()
        except: pass


# ═══════════════════════════════════════════════════════════════════
#  AREA SELECTOR  — fullscreen drag-to-select overlay
# ═══════════════════════════════════════════════════════════════════
class AreaSelector(tk.Toplevel):
    """
    Semi-transparent fullscreen overlay. User drags to pick a region.
    on_done(x, y, w, h) is called with screen-pixel coords then destroyed.
    """
    OVERLAY  = "#000000"
    BORDER   = "#60a5fa"
    LABEL_BG = "#1e3a8a"
    LABEL_FG = "#e2e8f0"

    def __init__(self, parent, on_done):
        super().__init__(parent)
        self._on_done  = on_done
        self._sx = self._sy = 0
        self._dragging = False
        self._rect     = None
        self._info_txt = None

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.38)
        self.configure(bg=self.OVERLAY)
        self.config(cursor="crosshair")

        self._cv = tk.Canvas(self, bg=self.OVERLAY,
                             highlightthickness=0, cursor="crosshair")
        self._cv.pack(fill="both", expand=True)

        # Instruction banner
        self._cv.create_rectangle(0, 0, sw, 46, fill="#0f172a", outline="")
        self._cv.create_text(sw//2, 23,
            text="  Click and drag to select the area to record  —  ESC to cancel  ",
            font=("Segoe UI", 11, "bold"), fill="#60a5fa")

        self._cv.bind("<ButtonPress-1>",   self._on_press)
        self._cv.bind("<B1-Motion>",       self._on_drag)
        self._cv.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    @staticmethod
    def _even(n): return n if n % 2 == 0 else n - 1

    def _on_press(self, e):
        self._sx, self._sy = e.x, e.y
        self._dragging = True
        self._cv.delete("sel")

    def _on_drag(self, e):
        if not self._dragging: return
        self._cv.delete("sel")
        x1, y1 = min(self._sx, e.x), min(self._sy, e.y)
        x2, y2 = max(self._sx, e.x), max(self._sy, e.y)
        w = self._even(x2 - x1)
        h = self._even(y2 - y1)
        SW = self.winfo_screenwidth()
        SH = self.winfo_screenheight()

        # Dark veil outside selection (4 rects)
        for rx1,ry1,rx2,ry2 in [
            (0,0,SW,y1),(0,y2,SW,SH),(0,y1,x1,y2),(x2,y1,SW,y2)
        ]:
            self._cv.create_rectangle(rx1,ry1,rx2,ry2,
                fill="#000000", outline="", tags="sel")

        # Selection rectangle
        self._cv.create_rectangle(x1,y1,x2,y2,
            outline=self.BORDER, width=2, dash=(6,3), tags="sel")

        # Corner handles
        for cx,cy in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
            self._cv.create_rectangle(cx-5,cy-5,cx+5,cy+5,
                fill=self.BORDER, outline="", tags="sel")

        # Size badge
        bx = x1+(x2-x1)//2
        by = max(y1-30, 54)
        badge_w = 120
        self._cv.create_rectangle(bx-badge_w//2,by-13,bx+badge_w//2,by+13,
            fill=self.LABEL_BG, outline=self.BORDER, width=1, tags="sel")
        self._cv.create_text(bx, by,
            text=f"{w} × {h}  at ({x1}, {y1})",
            font=("Segoe UI", 8, "bold"), fill=self.LABEL_FG, tags="sel")

    def _on_release(self, e):
        if not self._dragging: return
        self._dragging = False
        x1 = min(self._sx, e.x); y1 = min(self._sy, e.y)
        x2 = max(self._sx, e.x); y2 = max(self._sy, e.y)
        w = self._even(x2 - x1); h = self._even(y2 - y1)
        if w < 20 or h < 20:
            self._cv.delete("sel"); return
        self.destroy()
        self._on_done(x1, y1, w, h)


# ═══════════════════════════════════════════════════════════════════
#  SCREEN RECORDER
# ═══════════════════════════════════════════════════════════════════
class ScreenRecorder(tk.Toplevel):
    BG = "#0d0d0d"; CARD = "#1e1e1e"; BORDER = "#333333"
    ACC = "#C8102E"; RED = "#ef4444"; GREEN = "#22c55e"
    TEXT = "#f5f5f5"; DIM = "#606060"; YELLOW = "#fbbf24"
    PURPLE = "#9b1fe8"

    def __init__(self, parent, on_file_ready):
        super().__init__(parent)
        self.title("Screen Recorder")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._on_file_ready = on_file_ready
        self._recording  = False
        self._paused     = False
        self._proc       = None
        self._out_path   = None
        self._elapsed    = 0
        self._tick_job   = None
        self._region     = None          # None = full screen, (x,y,w,h) = custom
        self._build()
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()//2 - self.winfo_width()//2
        py = parent.winfo_y() + parent.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{px}+{py}")

    # ─────────────────────────────────────────────────
    def _build(self):
        hdr = tk.Frame(self, bg=self.PURPLE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  ⬛ Screen Recorder",
                 font=("Segoe UI",13,"bold"),
                 bg=self.PURPLE, fg="white", pady=14).pack(side="left", padx=6)

        body = tk.Frame(self, bg=self.BG, padx=22, pady=14)
        body.pack(fill="both", expand=True)

        # ── Capture area card ─────────────────────────
        area_card = tk.Frame(body, bg=self.CARD,
                             highlightthickness=1, highlightbackground=self.BORDER)
        area_card.pack(fill="x", pady=(0,12))

        area_top = tk.Frame(area_card, bg=self.CARD, padx=12, pady=8)
        area_top.pack(fill="x")

        self._mode_var = tk.StringVar(value="full")
        mode_f = tk.Frame(area_top, bg=self.CARD)
        mode_f.pack(side="left")
        tk.Label(mode_f, text="Capture:", font=("Segoe UI",8,"bold"),
                 bg=self.CARD, fg=self.DIM).pack(side="left", padx=(0,8))
        for val, lbl in [("full","Full Screen"),("region","Custom Region")]:
            tk.Radiobutton(mode_f, text=lbl, variable=self._mode_var, value=val,
                           font=("Segoe UI",8), bg=self.CARD, fg=self.TEXT,
                           selectcolor=self.PURPLE, activebackground=self.CARD,
                           activeforeground=self.TEXT,
                           command=self._on_mode_change
                           ).pack(side="left", padx=6)

        self._sel_btn = tk.Button(area_top, text="  ✥ Select Area  ",
                 font=("Segoe UI",8,"bold"),
                 bg=self.PURPLE, fg="white",
                 activebackground="#6d28d9", activeforeground="white",
                 relief="flat", bd=0, padx=10, pady=4,
                 cursor="hand2", command=self._pick_area)

        # Region info label + minimap (shown after selection)
        self._region_lbl = tk.Label(area_card, text="",
                 font=("Courier New",8), bg=self.CARD,
                 fg=self.ACC, anchor="w", padx=12)
        self._minimap = tk.Canvas(area_card, bg="#020b18",
                                   highlightthickness=1,
                                   highlightbackground=self.BORDER, height=0)
        self._minimap.pack(fill="x", padx=12, pady=(0,6))

        # ── Settings row ──────────────────────────────
        sets = tk.Frame(body, bg=self.BG)
        sets.pack(fill="x", pady=(0,10))

        fps_f = tk.Frame(sets, bg=self.BG)
        fps_f.pack(side="left", padx=(0,18))
        tk.Label(fps_f, text="FPS", font=("Segoe UI",8,"bold"),
                 bg=self.BG, fg=self.DIM).pack()
        self._fps_var = tk.StringVar(value="30")
        ttk.Combobox(fps_f, textvariable=self._fps_var,
                     values=["15","24","30","60"], width=6,
                     state="readonly").pack()

        mon_f = tk.Frame(sets, bg=self.BG)
        mon_f.pack(side="left", padx=(0,18))
        tk.Label(mon_f, text="Monitor / Display", font=("Segoe UI",8,"bold"),
                 bg=self.BG, fg=self.DIM).pack()
        self._mon_var = tk.StringVar(value=":0.0" if SYSTEM == "Linux" else "1")
        tk.Entry(mon_f, textvariable=self._mon_var, width=8,
                 font=("Segoe UI",9), bg=self.CARD, fg=self.TEXT,
                 insertbackground=self.ACC, relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=self.BORDER,
                 justify="center").pack(ipady=3)

        crf_f = tk.Frame(sets, bg=self.BG)
        crf_f.pack(side="left")
        tk.Label(crf_f, text="Quality (CRF)", font=("Segoe UI",8,"bold"),
                 bg=self.BG, fg=self.DIM).pack()
        self._crf_var = tk.StringVar(value="23")
        ttk.Combobox(crf_f, textvariable=self._crf_var,
                     values=["18 (best)","23 (good)","28 (smaller)","32 (smallest)"],
                     width=14, state="readonly").pack()

        # ── Output path ───────────────────────────────
        pr = tk.Frame(body, bg=self.BG)
        pr.pack(fill="x", pady=(0,10))
        tk.Label(pr, text="Save as", font=("Segoe UI",8,"bold"),
                 bg=self.BG, fg=self.DIM).pack(anchor="w", pady=(0,4))
        prow = tk.Frame(pr, bg=self.BG)
        prow.pack(fill="x")
        self._path_sv = tk.StringVar(value=str(SCRIPT_DIR / "screen_recording.mp4"))
        tk.Entry(prow, textvariable=self._path_sv, font=("Segoe UI",8),
                 bg=self.CARD, fg=self.TEXT, insertbackground=self.ACC,
                 relief="flat", bd=0, highlightthickness=1,
                 highlightcolor=self.ACC, highlightbackground=self.BORDER
                 ).pack(side="left", fill="x", expand=True, padx=(0,8), ipady=5)
        tk.Button(prow, text="Browse", font=("Segoe UI",8),
                  bg=self.CARD, fg=self.ACC, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  command=self._browse).pack(side="left")

        # ── Status ────────────────────────────────────
        st = tk.Frame(body, bg=self.BG)
        st.pack(fill="x", pady=(0,6))
        self._status_lbl = tk.Label(st, text="Ready to record",
                 font=("Segoe UI",9), bg=self.BG, fg=self.DIM)
        self._status_lbl.pack(side="left")
        self._timer_lbl = tk.Label(st, text="00:00",
                 font=("Segoe UI",18,"bold"), bg=self.BG, fg=self.PURPLE)
        self._timer_lbl.pack(side="right")
        self._dot_cv = tk.Canvas(st, bg=self.BG, highlightthickness=0,
                                   width=16, height=16)
        self._dot_cv.pack(side="right", padx=6)
        self._dot = self._dot_cv.create_oval(2,2,14,14, fill=self.DIM, outline="")

        if not ffmpeg_exe():
            self._status_lbl.config(text="FFmpeg not found!", fg=self.RED)

        # ── Buttons ───────────────────────────────────
        br = tk.Frame(body, bg=self.BG)
        br.pack(pady=(8,0))
        self._rec_btn = tk.Button(br, text="  ● Start Recording  ",
                 font=("Segoe UI",11,"bold"),
                 bg=self.PURPLE, fg="white",
                 activebackground="#6d28d9", activeforeground="white",
                 relief="flat", bd=0, padx=18, pady=10,
                 cursor="hand2", command=self._toggle_record)
        self._rec_btn.pack(side="left", padx=6)

        self._pause_btn = tk.Button(br, text="  ⏸ Pause  ",
                 font=("Segoe UI",10,"bold"),
                 bg=self.CARD, fg=self.DIM,
                 activebackground=self.BORDER,
                 relief="flat", bd=0, padx=14, pady=10,
                 cursor="hand2", command=self._toggle_pause, state="disabled")
        self._pause_btn.pack(side="left", padx=6)

        self._use_btn = tk.Button(br, text="  Use for Compression  ",
                 font=("Segoe UI",10,"bold"),
                 bg=self.GREEN, fg="white",
                 activebackground="#16a34a", activeforeground="white",
                 relief="flat", bd=0, padx=16, pady=10,
                 cursor="hand2", command=self._use_recording, state="disabled")
        self._use_btn.pack(side="left", padx=6)

        tk.Button(br, text="Cancel", font=("Segoe UI",9),
                  bg=self.CARD, fg=self.DIM, activebackground=self.BORDER,
                  relief="flat", bd=0, padx=12, pady=10,
                  cursor="hand2", command=self._on_close).pack(side="left", padx=6)

    # ─────────────────────────────────────────────────
    #  MODE TOGGLE
    # ─────────────────────────────────────────────────
    def _on_mode_change(self):
        if self._mode_var.get() == "region":
            self._sel_btn.pack(side="right", padx=(8,0))
        else:
            self._sel_btn.pack_forget()
            self._region = None
            self._region_lbl.config(text="")
            self._region_lbl.pack_forget()
            self._minimap.config(height=0)
            self._minimap.delete("all")

    # ─────────────────────────────────────────────────
    #  AREA PICKER
    # ─────────────────────────────────────────────────
    def _pick_area(self):
        self.withdraw()
        self.after(200, lambda: AreaSelector(self, on_done=self._area_selected))

    def _area_selected(self, x, y, w, h):
        self._region = (x, y, w, h)
        self.deiconify(); self.lift()
        self._region_lbl.config(text=f"  Region:  {w} × {h} px   at  ({x}, {y})")
        self._region_lbl.pack(fill="x", pady=(0,4))
        self._draw_minimap(x, y, w, h)
        self._status_lbl.config(text=f"Region set: {w}×{h} at ({x},{y})", fg=self.ACC)

    def _draw_minimap(self, rx, ry, rw, rh):
        SW = self.winfo_screenwidth()
        SH = self.winfo_screenheight()
        MAP_H = 80
        self._minimap.config(height=MAP_H)
        self._minimap.delete("all")
        self._minimap.update_idletasks()
        MW = self._minimap.winfo_width() or 440
        scale = min(MW / SW, MAP_H / SH)
        sx = int((MW - SW*scale)/2); sy = int((MAP_H - SH*scale)/2)
        ssw = int(SW*scale); ssh = int(SH*scale)
        # Screen outline
        self._minimap.create_rectangle(sx,sy,sx+ssw,sy+ssh,
            fill="#0a1224", outline="#1e3d7a", width=1)
        # Selection highlight
        bx=sx+int(rx*scale); by=sy+int(ry*scale)
        bw=max(4,int(rw*scale)); bh=max(4,int(rh*scale))
        self._minimap.create_rectangle(bx,by,bx+bw,by+bh,
            fill="#1d4ed820", outline="#60a5fa", width=2)
        if bw > 30 and bh > 14:
            self._minimap.create_text(bx+bw//2, by+bh//2,
                text=f"{rw}×{rh}", font=("Segoe UI",7,"bold"), fill="#bfdbfe")
        self._minimap.create_text(sx+ssw//2, sy+ssh+10,
            text=f"Screen: {SW}×{SH}", font=("Segoe UI",7), fill="#334155")

    # ─────────────────────────────────────────────────
    #  RECORD
    # ─────────────────────────────────────────────────
    def _browse(self):
        p = filedialog.asksaveasfilename(title="Save recording as",
            defaultextension=".mp4", filetypes=[("MP4","*.mp4"),("All files","*.*")])
        if p: self._path_sv.set(p)

    def _toggle_record(self):
        if not self._recording: self._start_recording()
        else: self._stop_recording()

    def _start_recording(self):
        ff = ffmpeg_exe()
        if not ff:
            messagebox.showerror("FFmpeg Missing",
                "FFmpeg required for screen recording.\nInstall via Settings.", parent=self)
            return
        if self._mode_var.get() == "region" and self._region is None:
            messagebox.showwarning("No Region",
                "Click  ✥ Select Area  to draw your capture region first.", parent=self)
            return

        out = self._path_sv.get().strip() or str(SCRIPT_DIR/"screen_recording.mp4")
        self._out_path = out
        fps = self._fps_var.get()
        crf = self._crf_var.get().split()[0]
        try: crf = str(int(crf))
        except: crf = "23"

        use_region = (self._mode_var.get() == "region") and self._region
        rx, ry, rw, rh = self._region if use_region else (0, 0, 0, 0)

        if SYSTEM == "Windows":
            if use_region:
                src_args = ["-f","gdigrab","-framerate",fps,
                            "-offset_x",str(rx),"-offset_y",str(ry),
                            "-video_size",f"{rw}x{rh}","-i","desktop"]
            else:
                src_args = ["-f","gdigrab","-framerate",fps,"-i","desktop"]
        elif SYSTEM == "Darwin":
            src_args = ["-f","avfoundation","-framerate",fps,"-i","1:none"]
        else:
            mon = self._mon_var.get().strip() or ":0.0"
            if use_region:
                src_args = ["-f","x11grab","-framerate",fps,
                            "-video_size",f"{rw}x{rh}","-i",f"{mon}+{rx},{ry}"]
            else:
                src_args = ["-f","x11grab","-framerate",fps,"-i",mon]

        vf_args = (["-vf",f"crop={rw}:{rh}:{rx}:{ry}"]
                   if use_region and SYSTEM == "Darwin" else [])

        cmd = ([ff,"-y"] + src_args + vf_args +
               ["-c:v","libx264","-preset","ultrafast",
                "-crf",crf,"-pix_fmt","yuv420p", out])
        try:
            self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self); return

        self._recording = True; self._paused = False; self._elapsed = 0
        mode_txt = f"Region {rw}x{rh}" if use_region else "Full screen"
        self._rec_btn.config(text="  ■ Stop Recording  ", bg=self.RED)
        self._pause_btn.config(state="normal", text="  ⏸ Pause  ",
                               bg="#b45309", fg="white")
        self._status_lbl.config(text=f"Recording {mode_txt}…", fg=self.RED)
        self._use_btn.config(state="disabled")
        self._overlay = RecordingOverlay(self, on_stop=self._toggle_record, label=mode_txt)
        self._tick_timer(); self._blink_dot()

    def _stop_recording(self):
        self._recording = False
        self._paused = False
        # Close the floating overlay
        if hasattr(self, "_overlay") and self._overlay:
            try: self._overlay.close()
            except: pass
            self._overlay = None
        if self._proc:
            try:
                self._proc.stdin.write(b"q"); self._proc.stdin.flush()
                self._proc.wait(timeout=5)
            except Exception:
                try: self._proc.terminate()
                except: pass
            self._proc = None
        self._rec_btn.config(text="  ● Start Recording  ", bg=self.PURPLE)
        self._pause_btn.config(state="disabled", text="  ⏸ Pause  ",
                               bg=self.CARD, fg=self.DIM)
        self._status_lbl.config(text=f"Saved: {Path(self._out_path).name}", fg=self.DIM)
        self._dot_cv.itemconfig(self._dot, fill=self.DIM)
        self._use_btn.config(state="normal")
        if self._tick_job:
            try: self.after_cancel(self._tick_job)
            except: pass

    def _toggle_pause(self):
        if not self._recording: return
        self._paused = not self._paused
        if self._paused:
            # Suspend the FFmpeg process on Unix, or just pause timer on Windows
            if self._proc and SYSTEM != "Windows":
                try:
                    import signal
                    os.kill(self._proc.pid, signal.SIGSTOP)
                except Exception: pass
            self._pause_btn.config(text="  ▶ Resume  ", bg="#16a34a")
            self._status_lbl.config(text="Paused…", fg="#fbbf24")
            if hasattr(self, "_overlay") and self._overlay:
                try: self._overlay.pause()
                except: pass
        else:
            if self._proc and SYSTEM != "Windows":
                try:
                    import signal
                    os.kill(self._proc.pid, signal.SIGCONT)
                except Exception: pass
            self._pause_btn.config(text="  ⏸ Pause  ", bg="#b45309")
            self._status_lbl.config(text="Recording…", fg=self.RED)
            if hasattr(self, "_overlay") and self._overlay:
                try: self._overlay.resume()
                except: pass

    def _tick_timer(self):
        if not self._recording: return
        if not self._paused:
            self._elapsed += 1
            m, s = divmod(self._elapsed, 60)
            self._timer_lbl.config(text=f"{m:02d}:{s:02d}")
        self._tick_job = self.after(1000, self._tick_timer)

    def _blink_dot(self):
        if not self._recording: return
        if not self._paused:
            cur = self._dot_cv.itemcget(self._dot, "fill")
            self._dot_cv.itemconfig(self._dot, fill=self.RED if cur != self.RED else self.BG)
        else:
            self._dot_cv.itemconfig(self._dot, fill="#fbbf24")
        self.after(500, self._blink_dot)

    def _use_recording(self):
        if self._out_path and os.path.isfile(self._out_path):
            self._on_file_ready(self._out_path); self._on_close()
        else:
            messagebox.showerror("Not found", "Recording not found.", parent=self)

    def _on_close(self):
        if self._recording: self._stop_recording()
        try: self.destroy()
        except: pass

# ═══════════════════════════════════════════════════════════════════
#  WEBCAM RECORDER
# ═══════════════════════════════════════════════════════════════════
class WebcamRecorder(tk.Toplevel):
    BG = "#0d0d0d"; CARD = "#1e1e1e"; BORDER = "#333333"
    ACC = "#C8102E"; RED = "#ef4444"; GREEN = "#22c55e"
    TEXT = "#f5f5f5"; DIM = "#606060"

    def __init__(self, parent, on_file_ready):
        super().__init__(parent)
        self.title("Webcam Recorder")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._on_file_ready = on_file_ready
        self._recording = False
        self._paused   = False
        self._cap = None; self._writer = None
        self._out_path = None; self._preview_job = None
        self._tick_job = None; self._elapsed = 0; self._cv2 = None
        self._build()
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()//2 - self.winfo_width()//2
        py = parent.winfo_y() + parent.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{px}+{py}")
        self._try_load_cv2()

    def _build(self):
        hdr = tk.Frame(self, bg=self.ACC)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  📷 Webcam Recorder",
                 font=("Segoe UI",13,"bold"),
                 bg=self.ACC, fg="white", pady=14).pack(side="left", padx=6)

        body = tk.Frame(self, bg=self.BG, padx=18, pady=14)
        body.pack(fill="both")

        self._preview = tk.Canvas(body, bg="#000d1a",
                                   highlightthickness=1, highlightbackground=self.BORDER)
        self._preview.config(width=480, height=270)
        self._preview.pack(pady=(0,10))
        self._preview_msg = self._preview.create_text(
            240, 135, text="Camera preview will appear here",
            font=("Segoe UI",10), fill=self.DIM)

        st = tk.Frame(body, bg=self.BG)
        st.pack(fill="x", pady=(0,8))
        self._status_lbl = tk.Label(st, text="Ready", font=("Segoe UI",9), bg=self.BG, fg=self.DIM)
        self._status_lbl.pack(side="left")
        self._timer_lbl = tk.Label(st, text="00:00", font=("Segoe UI",14,"bold"), bg=self.BG, fg=self.ACC)
        self._timer_lbl.pack(side="right")
        self._dot_cv = tk.Canvas(st, bg=self.BG, highlightthickness=0, width=14, height=14)
        self._dot_cv.pack(side="right", padx=6)
        self._dot = self._dot_cv.create_oval(2,2,12,12, fill=self.DIM, outline="")

        pr = tk.Frame(body, bg=self.BG)
        pr.pack(fill="x", pady=(0,10))
        tk.Label(pr, text="Save as:", font=("Segoe UI",8), bg=self.BG, fg=self.DIM).pack(side="left", padx=(0,6))
        self._path_sv = tk.StringVar(value=str(SCRIPT_DIR/"webcam_recording.mp4"))
        tk.Entry(pr, textvariable=self._path_sv, font=("Segoe UI",8),
                 bg=self.CARD, fg=self.TEXT, insertbackground=self.ACC,
                 relief="flat", bd=0, highlightthickness=1,
                 highlightcolor=self.ACC, highlightbackground=self.BORDER
                 ).pack(side="left", fill="x", expand=True, padx=(0,6), ipady=4)
        tk.Button(pr, text="Browse", font=("Segoe UI",8),
                  bg=self.CARD, fg=self.ACC, relief="flat", bd=0, padx=8, pady=3,
                  cursor="hand2", command=self._browse_save).pack(side="left")

        br = tk.Frame(body, bg=self.BG)
        br.pack(pady=(4,0))
        self._rec_btn = tk.Button(br, text="  ● Record  ",
                 font=("Segoe UI",10,"bold"), bg=self.RED, fg="white",
                 activebackground="#dc2626", activeforeground="white",
                 relief="flat", bd=0, padx=18, pady=8,
                 cursor="hand2", command=self._toggle_record)
        self._rec_btn.pack(side="left", padx=6)
        self._pause_btn = tk.Button(br, text="  ⏸ Pause  ",
                 font=("Segoe UI",10,"bold"), bg=self.CARD, fg=self.DIM,
                 activebackground=self.BORDER, activeforeground=self.TEXT,
                 relief="flat", bd=0, padx=14, pady=8,
                 cursor="hand2", command=self._toggle_pause, state="disabled")
        self._pause_btn.pack(side="left", padx=6)
        self._use_btn = tk.Button(br, text="  Use for Compression  ",
                 font=("Segoe UI",10,"bold"), bg=self.GREEN, fg="white",
                 activebackground="#16a34a", activeforeground="white",
                 relief="flat", bd=0, padx=18, pady=8,
                 cursor="hand2", command=self._use_recording, state="disabled")
        self._use_btn.pack(side="left", padx=6)
        tk.Button(br, text="Cancel", font=("Segoe UI",9),
                  bg=self.CARD, fg=self.DIM, activebackground=self.BORDER,
                  relief="flat", bd=0, padx=12, pady=8,
                  cursor="hand2", command=self._on_close).pack(side="left", padx=6)

    def _try_load_cv2(self):
        try:
            import cv2
            self._cv2 = cv2
            self._status_lbl.config(text="Opening camera…", fg=self.DIM)
            # Run camera open in background so UI doesn't freeze
            threading.Thread(target=self._start_preview, daemon=True).start()
        except ImportError:
            self._status_lbl.config(text="pip install opencv-python", fg=self.RED)
            self._preview.itemconfig(self._preview_msg,
                text="opencv-python not installed\nRun: pip install opencv-python", fill=self.RED)
            self._rec_btn.config(state="disabled")

    def _start_preview(self):
        cv2 = self._cv2
        cap = None

        # Try DirectShow (Windows) first, then default, then indices 0-3
        backends = []
        if platform.system() == "Windows":
            backends = [
                (0, cv2.CAP_DSHOW),
                (0, cv2.CAP_MSMF),
                (0, cv2.CAP_ANY),
                (1, cv2.CAP_DSHOW),
                (1, cv2.CAP_ANY),
                (2, cv2.CAP_DSHOW),
                (2, cv2.CAP_ANY),
            ]
        else:
            backends = [
                (0, cv2.CAP_ANY),
                (1, cv2.CAP_ANY),
                (2, cv2.CAP_ANY),
            ]

        for idx, backend in backends:
            try:
                c = cv2.VideoCapture(idx, backend)
                if c.isOpened():
                    # Verify we can actually read a frame
                    ret, frame = c.read()
                    if ret and frame is not None:
                        cap = c
                        break
                    else:
                        c.release()
                else:
                    c.release()
            except Exception:
                continue

        if cap is None:
            self.after(0, self._no_camera)
            return

        # Set reasonable resolution
        cap.set(self._cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(self._cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(self._cv2.CAP_PROP_FPS, 30)

        self._cap = cap
        self.after(0, self._camera_ready)

    def _camera_ready(self):
        self._status_lbl.config(text="Camera ready ✓", fg=self.GREEN)
        self._preview.itemconfig(self._preview_msg, text="")
        self._rec_btn.config(state="normal")
        self._update_preview()

    def _no_camera(self):
        self._status_lbl.config(
            text="No camera found — see hints below", fg=self.RED)
        self._preview.itemconfig(self._preview_msg,
            text=(
                "Cannot open webcam.\n\n"
                "Windows fix:\n"
                "  Settings → Privacy → Camera\n"
                "  → Enable 'Allow apps to access camera'\n\n"
                "Also check: camera not used by Teams/Zoom/etc.\n"
                "Then click  [ Retry Camera ]  below."
            ),
            fill="#ff7a7a")
        self._rec_btn.config(state="disabled")
        # Show retry button
        if not hasattr(self, "_retry_btn"):
            self._retry_btn = tk.Button(
                self._rec_btn.master,
                text="  ↺ Retry Camera  ",
                font=("Segoe UI", 10, "bold"),
                bg=self.ACC, fg="white",
                activebackground=self.ACC2 if hasattr(self, "ACC2") else "#a00020",
                relief="flat", bd=0, padx=14, pady=8,
                cursor="hand2",
                command=self._retry_camera)
            self._retry_btn.pack(side="left", padx=6)

    def _retry_camera(self):
        if hasattr(self, "_retry_btn"):
            try: self._retry_btn.destroy()
            except: pass
            del self._retry_btn
        self._preview.itemconfig(self._preview_msg,
            text="Searching for camera…", fill=self.DIM)
        self._status_lbl.config(text="Retrying…", fg=self.DIM)
        if self._cv2 is None:
            self._try_load_cv2()
        else:
            threading.Thread(target=self._start_preview, daemon=True).start()

    def _update_preview(self):
        if self._cv2 is None or self._cap is None: return
        try:
            ret, frame = self._cap.read()
            if ret:
                frame_resized = self._cv2.resize(frame, (480, 270))
                rgb = self._cv2.cvtColor(frame_resized, self._cv2.COLOR_BGR2RGB)
                if self._recording and not self._paused and self._writer:
                    self._writer.write(frame_resized)
                h, w = rgb.shape[:2]
                ppm = (f"P6 {w} {h} 255 ").encode() + rgb.tobytes()
                photo = tk.PhotoImage(width=w, height=h, data=ppm, format="PPM")
                self._preview.create_image(0, 0, anchor="nw", image=photo)
                self._preview._photo = photo
        except Exception:
            pass
        self._preview_job = self.after(33, self._update_preview)

    def _toggle_record(self):
        if not self._recording: self._start_recording()
        else: self._stop_recording()

    def _start_recording(self):
        out = self._path_sv.get().strip() or str(SCRIPT_DIR/"webcam_recording.mp4")
        self._out_path = out
        fourcc = self._cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = self._cv2.VideoWriter(out, fourcc, 20.0, (480, 270))
        self._recording = True; self._paused = False; self._elapsed = 0
        self._rec_btn.config(text="  ■ Stop  ", bg="#dc2626")
        self._pause_btn.config(state="normal", text="  ⏸ Pause  ",
                               bg="#b45309", fg="white")
        self._status_lbl.config(text="Recording…", fg=self.RED)
        self._use_btn.config(state="disabled")
        self._overlay = RecordingOverlay(self, on_stop=self._toggle_record, label="Webcam")
        self._tick_timer(); self._blink_dot()

    def _stop_recording(self):
        self._recording = False
        self._paused = False
        if hasattr(self, "_overlay") and self._overlay:
            try: self._overlay.close()
            except: pass
            self._overlay = None
        if self._writer: self._writer.release(); self._writer = None
        self._rec_btn.config(text="  ● Record  ", bg=self.RED)
        self._pause_btn.config(state="disabled", text="  ⏸ Pause  ",
                               bg=self.CARD, fg=self.DIM)
        self._status_lbl.config(text=f"Saved: {Path(self._out_path).name}", fg=self.DIM)
        self._dot_cv.itemconfig(self._dot, fill=self.DIM)
        self._use_btn.config(state="normal")
        if self._tick_job:
            try: self.after_cancel(self._tick_job)
            except: pass
        # Show fullscreen preview of the recorded video
        self.after(200, lambda: self._show_fullscreen_preview())

    def _show_fullscreen_preview(self):
        """Open a fullscreen window to preview the just-recorded video."""
        if not self._out_path or not os.path.isfile(self._out_path): return
        if self._cv2 is None: return
        try:
            FullscreenVideoPreview(self, self._out_path, self._cv2)
        except Exception:
            pass

    def _toggle_pause(self):
        if not self._recording: return
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.config(text="  ▶ Resume  ", bg="#16a34a")
            self._status_lbl.config(text="Paused…", fg="#fbbf24")
            if hasattr(self, "_overlay") and self._overlay:
                try: self._overlay.pause()
                except: pass
        else:
            self._pause_btn.config(text="  ⏸ Pause  ", bg="#b45309")
            self._status_lbl.config(text="Recording…", fg=self.RED)
            if hasattr(self, "_overlay") and self._overlay:
                try: self._overlay.resume()
                except: pass

    def _tick_timer(self):
        if not self._recording: return
        if not self._paused:
            self._elapsed += 1
            m, s = divmod(self._elapsed, 60)
            self._timer_lbl.config(text=f"{m:02d}:{s:02d}")
        self._tick_job = self.after(1000, self._tick_timer)

    def _blink_dot(self):
        if not self._recording: return
        if not self._paused:
            cur = self._dot_cv.itemcget(self._dot, "fill")
            self._dot_cv.itemconfig(self._dot, fill=self.RED if cur != self.RED else self.BG)
        else:
            self._dot_cv.itemconfig(self._dot, fill="#fbbf24")
        self.after(500, self._blink_dot)

    def _browse_save(self):
        p = filedialog.asksaveasfilename(title="Save recording as",
            defaultextension=".mp4", filetypes=[("MP4","*.mp4"),("All files","*.*")])
        if p: self._path_sv.set(p)

    def _use_recording(self):
        if self._out_path and os.path.isfile(self._out_path):
            self._on_file_ready(self._out_path); self._on_close()
        else:
            messagebox.showerror("Not found", "Recording not found.", parent=self)

    def _on_close(self):
        if self._recording: self._stop_recording()
        if self._preview_job:
            try: self.after_cancel(self._preview_job)
            except: pass
        self._cv2 = None   # signals _update_preview to stop
        if self._cap:
            try: self._cap.release()
            except: pass
            self._cap = None
        try: self.destroy()
        except: pass

# ═══════════════════════════════════════════════════════════════════
#  FULLSCREEN VIDEO PREVIEW  — shown after webcam recording ends
# ═══════════════════════════════════════════════════════════════════
class FullscreenVideoPreview(tk.Toplevel):
    """Plays back a recorded video file in a fullscreen window using OpenCV."""
    BG = "#000000"

    def __init__(self, parent, video_path, cv2_module):
        super().__init__(parent)
        self._cv2      = cv2_module
        self._path     = video_path
        self._playing  = True
        self._cap      = None
        self._job      = None

        self.title("Recording Preview")
        self.configure(bg=self.BG)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>",   lambda e: self._close())
        self.bind("<space>",    lambda e: self._toggle_play())
        self.bind("<Return>",   lambda e: self._close())

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Canvas fills full screen
        self._canvas = tk.Canvas(self, bg=self.BG, highlightthickness=0,
                                  width=sw, height=sh)
        self._canvas.pack(fill="both", expand=True)

        # Overlay controls bar at bottom
        ctrl = tk.Frame(self, bg="#111111")
        ctrl.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)

        tk.Label(ctrl, text="  ⬛ Recording Preview",
                 font=("Segoe UI",10,"bold"), bg="#111111", fg="#aaaaaa",
                 pady=6).pack(side="left", padx=8)

        self._play_btn = tk.Button(ctrl, text="  ⏸ Pause  ",
                 font=("Segoe UI",9,"bold"), bg="#1e1e1e", fg="white",
                 activebackground="#333333", relief="flat", bd=0,
                 padx=12, pady=6, cursor="hand2", command=self._toggle_play)
        self._play_btn.pack(side="left", padx=4)

        tk.Button(ctrl, text="  ✕ Close (Esc)  ",
                 font=("Segoe UI",9,"bold"), bg="#7f1d1d", fg="white",
                 activebackground="#dc2626", relief="flat", bd=0,
                 padx=12, pady=6, cursor="hand2", command=self._close
                 ).pack(side="right", padx=8)

        tk.Label(ctrl, text="Space = pause/play  ·  Esc = close",
                 font=("Segoe UI",8), bg="#111111", fg="#555555",
                 pady=6).pack(side="right", padx=12)

        self._sw = sw; self._sh = sh - 44  # leave space for control bar
        self._start_playback()

    def _start_playback(self):
        try:
            self._cap = self._cv2.VideoCapture(self._path)
            fps = self._cap.get(self._cv2.CAP_PROP_FPS) or 20
            self._delay = max(1, int(1000 / fps))
            self._advance()
        except Exception:
            self._close()

    def _advance(self):
        if not self._playing:
            self._job = self.after(100, self._advance)
            return
        if self._cap is None: return
        try:
            ret, frame = self._cap.read()
            if not ret:
                # Loop back
                self._cap.set(self._cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if not ret:
                    self._close(); return
            # Scale frame to fill screen while keeping aspect ratio
            fh, fw = frame.shape[:2]
            scale = min(self._sw / fw, self._sh / fh)
            nw, nh = int(fw * scale), int(fh * scale)
            frame_r = self._cv2.resize(frame, (nw, nh))
            rgb = self._cv2.cvtColor(frame_r, self._cv2.COLOR_BGR2RGB)
            ppm = (f"P6 {nw} {nh} 255 ").encode() + rgb.tobytes()
            photo = tk.PhotoImage(width=nw, height=nh, data=ppm, format="PPM")
            cx = self._sw // 2; cy = self._sh // 2
            self._canvas.create_image(cx, cy, anchor="center", image=photo)
            self._canvas._photo = photo
        except Exception:
            pass
        self._job = self.after(self._delay, self._advance)

    def _toggle_play(self):
        self._playing = not self._playing
        self._play_btn.config(text="  ▶ Play  " if not self._playing else "  ⏸ Pause  ")

    def _close(self):
        if self._job:
            try: self.after_cancel(self._job)
            except: pass
        if self._cap:
            try: self._cap.release()
            except: pass
        try: self.destroy()
        except: pass


# ═══════════════════════════════════════════════════════════════════
#  SLIM PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════
class SlimProgress(tk.Frame):
    H = 6
    C_BG = "#1a1a1a"; C_A = "#C8102E"; C_B = "#FF4D6A"

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=self.C_BG, height=self.H, **kw)
        self._pct = 0.0; self._target = 0.0; self._running = False
        self._cv = tk.Canvas(self, height=self.H, bg=self.C_BG,
                             highlightthickness=0, bd=0)
        self._cv.pack(fill="both", expand=True)
        self._cv.bind("<Configure>", lambda e: self._draw())

    def set_value(self, pct):
        self._target = max(0.0, min(100.0, float(pct)))
        if not self._running:
            self._running = True
            self.after(16, self._tick)

    def reset(self):
        self._pct = 0.0; self._target = 0.0; self._running = False
        self.after(50, self._draw)

    def _tick(self):
        self._pct += (self._target - self._pct) * 0.15
        if abs(self._target - self._pct) < 0.05:
            self._pct = self._target
        self._draw()
        if abs(self._target - self._pct) > 0.05:
            self.after(16, self._tick)
        else:
            self._running = False

    def _draw(self):
        try:
            cv = self._cv; cv.delete("all")
            W = cv.winfo_width() or 400
            cv.create_rectangle(0, 0, W, self.H, fill=self.C_BG, outline="")
            fw = max(0, int(self._pct / 100 * W))
            if fw > 0:
                segs = max(1, fw)
                for i in range(0, fw, max(1, fw//40)):
                    i2 = min(i + max(1, fw//40), fw)
                    col = lerp_color(self.C_A, self.C_B, i/max(fw,1))
                    cv.create_rectangle(i, 0, i2, self.H, fill=col, outline="")
        except tk.TclError: pass

# ═══════════════════════════════════════════════════════════════════
#  FFMPEG INSTALL DIALOG
# ═══════════════════════════════════════════════════════════════════
class FFmpegDialog(tk.Toplevel):
    BG = "#0d0d0d"; CARD = "#1e1e1e"; BORDER = "#333333"; ACC = "#C8102E"
    TEXT = "#f5f5f5"; DIM = "#606060"

    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.title("Install FFmpeg")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.grab_set()
        self._on_success = on_success
        self._build()
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()//2 - self.winfo_width()//2
        py = parent.winfo_y() + parent.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{px}+{py}")

    def _build(self):
        hdr = tk.Frame(self, bg=self.ACC)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  FFmpeg Required", font=("Segoe UI",13,"bold"),
                 bg=self.ACC, fg="white", pady=12).pack(side="left", padx=8)
        body = tk.Frame(self, bg=self.BG, padx=22, pady=14)
        body.pack(fill="x")
        tk.Label(body, text=f"FFmpeg is needed for video compression.\nOS: {SYSTEM}",
                 font=("Segoe UI",9), bg=self.BG, fg=self.TEXT, justify="left").pack(anchor="w")
        manual = {"Windows":"winget install ffmpeg","Darwin":"brew install ffmpeg",
                  "Linux":"sudo apt install ffmpeg"}.get(SYSTEM,"https://ffmpeg.org/download.html")
        mbox = tk.Frame(body, bg=self.CARD, highlightthickness=1, highlightbackground=self.BORDER)
        mbox.pack(fill="x", pady=(10,0))
        tk.Label(mbox, text=f"  Manual:  {manual}", font=("Courier New",8),
                 bg=self.CARD, fg=self.DIM, pady=7).pack(anchor="w")
        pf = tk.Frame(self, bg=self.BG, padx=22)
        pf.pack(fill="x", pady=(8,0))
        self._log = tk.StringVar(value="Click Auto Install to begin.")
        tk.Label(pf, textvariable=self._log, font=("Segoe UI",8), bg=self.BG,
                 fg=self.DIM, anchor="w", wraplength=420).pack(fill="x")
        self._prog = SlimProgress(pf)
        self._prog.pack(fill="x", pady=6)
        bf = tk.Frame(self, bg=self.BG, pady=14, padx=22)
        bf.pack(fill="x")
        self._ibtn = tk.Button(bf, text="  Auto Install  ", font=("Segoe UI",10,"bold"),
                 bg=self.ACC, fg="white", activebackground="#2563eb", activeforeground="white",
                 relief="flat", bd=0, pady=8, cursor="hand2", command=self._start)
        self._ibtn.pack(side="left", padx=(0,10))
        tk.Button(bf, text="Cancel", font=("Segoe UI",9), bg=self.CARD, fg=self.DIM,
                  activebackground=self.BORDER, relief="flat", bd=0, padx=14, pady=8,
                  cursor="hand2", command=self.destroy).pack(side="left")

    def _start(self):
        self._ibtn.config(state="disabled", text="Installing…")
        def worker():
            try:
                p = install_ffmpeg_auto(
                    log_cb=lambda m: self.after(0, lambda: self._log.set(m)),
                    prog_cb=lambda v: self.after(0, lambda: self._prog.set_value(v)))
                self.after(0, lambda: self._done(p))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._fail(msg))
        threading.Thread(target=worker, daemon=True).start()

    def _done(self, p):
        messagebox.showinfo("Installed!", f"FFmpeg ready!\n\n{p}", parent=self)
        self.destroy(); self._on_success()

    def _fail(self, msg):
        self._ibtn.config(state="normal", text="  Retry  ")
        messagebox.showerror("Failed", f"{msg}\n\nPlease install manually.", parent=self)

# ═══════════════════════════════════════════════════════════════════
#  COMPLETION POPUP
# ═══════════════════════════════════════════════════════════════════
class CompletionPopup(tk.Toplevel):
    BG = "#0d0d0d"; CARD = "#1e1e1e"; BORDER = "#333333"; ACC = "#C8102E"
    GREEN = "#22c55e"; YELLOW = "#fbbf24"; RED = "#ef4444"
    TEXT = "#f5f5f5"; DIM = "#606060"

    def __init__(self, parent, result, src_name):
        super().__init__(parent)
        self.title("Compression Complete")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.attributes("-topmost", True)
        self._result = result
        self._build(src_name)
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()//2 - self.winfo_width()//2
        py = parent.winfo_y() + parent.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{px}+{py}")
        self._alpha = 0.0
        self.attributes("-alpha", 0.0)
        self._fade_in()

    def _build(self, src_name):
        r = self._result
        orig = r["original_size"]; comp = r["compressed_size"]
        tgt = r["target_bytes"]; acc = r["accuracy_pct"]
        if   acc <= 10: acc_col, acc_txt = self.GREEN,  "Excellent"
        elif acc <= 25: acc_col, acc_txt = self.YELLOW, "Good"
        else:           acc_col, acc_txt = self.RED,    "Off target"
        hdr_col = self.GREEN if comp <= tgt * 1.1 else self.YELLOW
        hdr = tk.Frame(self, bg=hdr_col)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  ✓ Compression Complete!",
                 font=("Segoe UI",13,"bold"), bg=hdr_col, fg="white", pady=14
                 ).pack(side="left")
        body = tk.Frame(self, bg=self.BG, padx=26, pady=14)
        body.pack(fill="x")
        tk.Label(body, text=src_name, font=("Segoe UI",9,"bold"),
                 bg=self.BG, fg=self.TEXT, anchor="w").pack(fill="x", pady=(0,10))
        grid = tk.Frame(body, bg=self.BG)
        grid.pack(fill="x", pady=(0,12))
        saved = orig - comp; ratio = r["ratio"]

        def row(ri, label, value, vcol=None):
            tk.Label(grid, text=label, font=("Segoe UI",9), bg=self.BG,
                     fg=self.DIM, anchor="w", width=18).grid(row=ri, column=0, sticky="w", pady=2)
            tk.Label(grid, text=value, font=("Segoe UI",9,"bold"),
                     bg=self.BG, fg=vcol or self.TEXT, anchor="w").grid(row=ri, column=1, sticky="w", padx=(8,0))

        row(0, "Original Size",   human_size(orig))
        row(1, "Target Size",     human_size(tgt),  self.ACC)
        row(2, "Compressed Size", human_size(comp), self.GREEN if comp <= tgt*1.1 else self.YELLOW)
        row(3, "Space Saved",     human_size(saved) if saved > 0 else "None",
            self.GREEN if saved > 0 else self.RED)
        row(4, "Reduction",       f"{ratio:.1f}%", self.GREEN if ratio > 0 else self.RED)
        row(5, "Accuracy",        f"±{acc:.1f}%  —  {acc_txt}", acc_col)

        pb = tk.Frame(body, bg=self.CARD, highlightthickness=1, highlightbackground=self.BORDER)
        pb.pack(fill="x", pady=(0,12))
        tk.Label(pb, text="  Saved to:", font=("Segoe UI",8), bg=self.CARD, fg=self.DIM, pady=4).pack(anchor="w")
        tk.Label(pb, text=f"  {r['output_path']}", font=("Courier New",8), bg=self.CARD,
                 fg=self.ACC, pady=4, wraplength=420, justify="left").pack(anchor="w")
        tk.Button(body, text="   Close   ", font=("Segoe UI",10,"bold"),
                  bg=self.ACC, fg="white", activebackground="#2563eb", activeforeground="white",
                  relief="flat", bd=0, pady=8, cursor="hand2",
                  command=self.destroy).pack()

    def _fade_in(self):
        self._alpha = min(1.0, self._alpha + 0.08)
        try:
            self.attributes("-alpha", self._alpha)
            if self._alpha < 1.0: self.after(18, self._fade_in)
        except tk.TclError: pass

# ═══════════════════════════════════════════════════════════════════
#  MAIN APP  —  Fixed layout, no scrollbar, sidebar nav
# ═══════════════════════════════════════════════════════════════════
class App(tk.Tk):
    # ── Palette (LG Dark Premium Theme) ─────────────
    BG      = "#0d0d0d"
    PANEL   = "#161616"
    CARD    = "#1e1e1e"
    CARD2   = "#252525"
    BORDER  = "#333333"
    BORDER2 = "#444444"
    ACC     = "#C8102E"   # LG signature red
    ACC2    = "#E8192C"   # brighter red
    ACC3    = "#FF4D6A"   # light red / pink highlight
    PURPLE  = "#9b1fe8"
    GREEN   = "#16a34a"
    GREEN2  = "#22c55e"
    RED     = "#dc2626"
    RED2    = "#ef4444"
    YELLOW  = "#b45309"
    YELLOW2 = "#fbbf24"
    TEXT    = "#f5f5f5"
    TEXT2   = "#a0a0a0"
    DIM     = "#606060"
    LG      = "#C8102E"
    # ── Fonts ────────────────────────────────────────
    F_LOGO  = ("Segoe UI", 16, "bold")
    F_NAV   = ("Segoe UI", 9,  "bold")
    F_H1    = ("Segoe UI", 11, "bold")
    F_H2    = ("Segoe UI", 9,  "bold")
    F_BODY  = ("Segoe UI", 9)
    F_SMALL = ("Segoe UI", 8)
    F_MONO  = ("Courier New", 8)
    F_BIG   = ("Segoe UI", 22, "bold")

    W = 980; H = 660
    SIDEBAR_W = 190

    def __init__(self):
        super().__init__()
        self.title("Compressor Pro")
        self.configure(bg=self.BG)
        self.resizable(False, False)
        self.geometry(f"{self.W}x{self.H}")

        # State
        self._src_sv        = tk.StringVar()
        self._dst_sv        = tk.StringVar()
        self._algo_var      = tk.StringVar(value=list(TEXT_ALGORITHMS)[0])
        self._out_fmt       = tk.StringVar(value=".mp4")
        self._status_sv     = tk.StringVar(value="Select a file to begin")
        self._target_kb     = 500.0
        self._compress_busy = False
        self._unit          = tk.StringVar(value="KB")
        self._active_tab    = tk.StringVar(value="compress")

        # Widget refs
        self._progbar        = None
        self._pct_lbl        = None
        self._compress_btn   = None
        self._ff_status_lbl  = None
        self._ff_btn         = None
        self._file_lbl       = None
        self._preset_btns    = {}
        self._num_entry      = None
        self._unit_btns      = {}
        self._target_lbl     = None
        self._fmt_btns       = {}
        self._fmt_info_lbl   = None
        self._result_cv      = None
        self._result_text    = None
        self._content_frames = {}

        self._build()
        self._check_ffmpeg()
        self._show_tab("compress")

    # ─────────────────────────────────────────────────
    #  BUILD
    # ─────────────────────────────────────────────────
    def _build(self):
        # ── Sidebar ──────────────────────────────────
        self._sidebar = tk.Frame(self, bg=self.PANEL, width=self.SIDEBAR_W)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Logo
        logo_f = tk.Frame(self._sidebar, bg=self.ACC, height=70)
        logo_f.pack(fill="x")
        logo_f.pack_propagate(False)
        self._logo_lbl = tk.Label(logo_f, text="LG", font=self.F_LOGO,
                                  bg=self.ACC, fg="white")
        self._logo_lbl.pack(expand=True)
        self._load_lg_logo(logo_f)

        tk.Frame(self._sidebar, bg=self.LG, height=1).pack(fill="x")

        # Nav buttons
        nav_items = [
            ("compress", "⬜  Compress",       self.ACC),
            ("webcam",   "📷  Webcam Record",  self.ACC2),
            ("screen",   "⬛  Screen Record",  self.PURPLE),
            ("adb",      "🐞  ADB Logs",      "#58a6ff"),
            ("settings", "⚙  Settings",        self.TEXT2),
        ]
        self._nav_btns = {}
        nav_container = tk.Frame(self._sidebar, bg=self.PANEL, pady=8)
        nav_container.pack(fill="x")
        for key, label, col in nav_items:
            btn = tk.Button(nav_container, text=f"  {label}",
                            font=self.F_NAV, bg=self.PANEL, fg=self.TEXT2,
                            activebackground=self.CARD, activeforeground=self.TEXT,
                            relief="flat", bd=0, anchor="w",
                            pady=12, padx=8,
                            cursor="hand2",
                            command=lambda k=key: self._show_tab(k))
            btn.pack(fill="x", padx=8, pady=1)
            self._nav_btns[key] = btn

        # Spacer
        tk.Frame(self._sidebar, bg=self.PANEL).pack(fill="both", expand=True)

        # FFmpeg status at bottom of sidebar
        ff_f = tk.Frame(self._sidebar, bg=self.CARD, pady=8, padx=10)
        ff_f.pack(fill="x", side="bottom")
        self._ff_status_lbl = tk.Label(ff_f, text="",
                 font=self.F_SMALL, bg=self.CARD, fg=self.DIM)
        self._ff_status_lbl.pack(anchor="w")
        self._ff_btn = tk.Button(ff_f, text="Install FFmpeg",
                 font=("Segoe UI",8,"bold"),
                 bg=self.YELLOW, fg="#0d0d0d",
                 activebackground=self.YELLOW2,
                 relief="flat", bd=0, padx=8, pady=4,
                 cursor="hand2", command=self._open_install)

        # ── Main content area ─────────────────────────
        self._main = tk.Frame(self, bg=self.BG)
        self._main.pack(side="left", fill="both", expand=True)

        # Top bar
        topbar = tk.Frame(self._main, bg=self.PANEL, height=56)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self._topbar_title = tk.Label(topbar, text="Compress File",
                 font=("Segoe UI",13,"bold"), bg=self.PANEL, fg=self.TEXT)
        self._topbar_title.pack(side="left", padx=20, pady=0)
        tk.Frame(topbar, bg=self.PANEL).pack(side="left", fill="x", expand=True)

        # Divider
        tk.Frame(self._main, bg=self.BORDER, height=1).pack(fill="x")

        # Content region
        self._content_area = tk.Frame(self._main, bg=self.BG)
        self._content_area.pack(fill="both", expand=True)

        # Build individual tab frames
        self._build_compress_tab()
        self._build_webcam_tab()
        self._build_screen_tab()
        self._build_adb_tab()
        self._build_settings_tab()

    # ─────────────────────────────────────────────────
    #  LG LOGO LOADER
    # ─────────────────────────────────────────────────
    def _load_lg_logo(self, parent_frame):
        """Download LG logo and place it in the sidebar header."""
        LG_LOGO_URL = (
            "https://play-lh.googleusercontent.com/"
            "arF0MKr3xxSqN4HyZSMpsyvWn5mZxRR5xEEJ8i5iOiRwR-zKULaZiZJOOnNQm4KB1mCh"
        )
        def fetch():
            try:
                import io
                from PIL import Image, ImageTk
                req = urllib.request.Request(LG_LOGO_URL,
                    headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                img = Image.open(io.BytesIO(data)).convert("RGBA")
                img = img.resize((190, 160), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.after(0, lambda: _apply(photo))
            except Exception:
                pass  # keep text fallback silently

        def _apply(photo):
            try:
                self._logo_lbl.config(image=photo, text="", compound="center")
                self._logo_lbl._photo = photo
            except tk.TclError:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    # ─────────────────────────────────────────────────
    #  COMPRESS TAB
    # ─────────────────────────────────────────────────
    def _build_compress_tab(self):
        f = tk.Frame(self._content_area, bg=self.BG)
        self._content_frames["compress"] = f

        # Two-column layout
        left  = tk.Frame(f, bg=self.BG, width=400)
        right = tk.Frame(f, bg=self.BG, width=350)
        left.pack(side="left", fill="both", expand=True, padx=(16,8), pady=14)
        right.pack(side="left", fill="both", expand=True, padx=(8,16), pady=14)
        left.pack_propagate(False); right.pack_propagate(False)

        # ── LEFT COLUMN ────────────────────────────
        # File selection
        self._section_label(left, "01  Source & Output")
        fc = self._card(left)
        for lbl, sv, cmd, primary in [
            ("INPUT  ", self._src_sv, self._browse_src, True),
            ("OUTPUT ", self._dst_sv, self._browse_dst, False),
        ]:
            row = tk.Frame(fc, bg=self.CARD)
            row.pack(fill="x", pady=(0,6))
            tk.Label(row, text=lbl, font=self.F_MONO,
                     bg=self.CARD, fg=self.DIM).pack(side="left")
            tk.Entry(row, textvariable=sv,
                     font=self.F_SMALL, bg=self.CARD2, fg=self.TEXT,
                     insertbackground=self.ACC3, relief="flat", bd=0,
                     highlightthickness=1, highlightcolor=self.ACC2,
                     highlightbackground=self.BORDER2
                     ).pack(side="left", fill="x", expand=True, padx=(4,6), ipady=5)
            tk.Button(row, text="Browse",
                      font=self.F_SMALL,
                      bg=self.ACC if primary else self.CARD2,
                      fg="white" if primary else self.ACC3,
                      activebackground=self.ACC3, activeforeground="white",
                      relief="flat", bd=0, padx=10, pady=4,
                      cursor="hand2", command=cmd).pack(side="left")

        self._file_lbl = tk.Label(fc, text="No file selected",
                 font=self.F_SMALL, bg=self.CARD, fg=self.DIM, anchor="w")
        self._file_lbl.pack(fill="x", pady=(4,0))

        # Target size
        self._section_label(left, "02  Target Size")
        sc = self._card(left)

        # Presets  (5 per row × 3 rows max)
        pg = tk.Frame(sc, bg=self.CARD)
        pg.pack(fill="x", pady=(0,8))
        COLS = 5
        for idx, (lbl, kb) in enumerate(SIZE_PRESETS):
            rr, cc = divmod(idx, COLS)
            b = tk.Button(pg, text=lbl, font=("Segoe UI",7,"bold"),
                          bg=self.CARD2, fg=self.TEXT2,
                          activebackground=self.ACC, activeforeground="white",
                          relief="flat", bd=0, width=7, pady=5,
                          cursor="hand2",
                          command=lambda k=kb, l=lbl: self._pick_preset(k,l))
            b.grid(row=rr, column=cc, padx=2, pady=2, sticky="ew")
            self._preset_btns[kb] = b
        for cc in range(COLS):
            pg.columnconfigure(cc, weight=1)

        # Custom size row
        cr = tk.Frame(sc, bg=self.CARD)
        cr.pack(fill="x")
        tk.Label(cr, text="Custom:", font=self.F_SMALL,
                 bg=self.CARD, fg=self.DIM).pack(side="left", padx=(0,6))
        nb = tk.Frame(cr, bg=self.CARD2, highlightthickness=1,
                      highlightbackground=self.BORDER2)
        nb.pack(side="left", padx=(0,6))
        self._num_entry = tk.Entry(nb, width=6,
                 font=("Segoe UI",11,"bold"), bg=self.CARD2, fg=self.ACC3,
                 insertbackground=self.ACC3, justify="center", relief="flat", bd=0)
        self._num_entry.insert(0, "500")
        self._num_entry.pack(padx=8, pady=4)
        self._num_entry.bind("<Return>",     self._apply_custom)
        self._num_entry.bind("<FocusOut>",   self._apply_custom)
        self._num_entry.bind("<KeyRelease>", self._apply_custom)

        uf = tk.Frame(cr, bg=self.CARD)
        uf.pack(side="left", padx=(0,10))
        for u in ("KB","MB","GB"):
            b = tk.Button(uf, text=u, font=("Segoe UI",7,"bold"),
                          bg=self.CARD2, fg=self.TEXT2,
                          activebackground=self.ACC, activeforeground="white",
                          relief="flat", bd=0, width=3, pady=3,
                          cursor="hand2",
                          command=lambda uu=u: self._set_unit(uu))
            b.pack(side="left", padx=1)
            self._unit_btns[u] = b

        self._target_lbl = tk.Label(cr, text="→  500.00 KB",
                 font=("Segoe UI",10,"bold"), bg=self.CARD, fg=self.ACC3)
        self._target_lbl.pack(side="left")

        self._set_unit("KB")
        self._pick_preset(500, "500 KB")

        # COMPRESS button
        btn_f = tk.Frame(left, bg=self.BG)
        btn_f.pack(fill="x", pady=(12,0))
        self._compress_btn = tk.Button(btn_f, text="  COMPRESS NOW  ",
                 font=("Segoe UI",12,"bold"),
                 bg=self.ACC, fg="white",
                 activebackground=self.ACC2, activeforeground="white",
                 relief="flat", bd=0, pady=12,
                 cursor="hand2", command=self._start_compress)
        self._compress_btn.pack(fill="x")

        # Progress
        prog_f = tk.Frame(left, bg=self.BG)
        prog_f.pack(fill="x", pady=(8,0))
        ptop = tk.Frame(prog_f, bg=self.BG)
        ptop.pack(fill="x")
        tk.Label(ptop, textvariable=self._status_sv,
                 font=self.F_SMALL, bg=self.BG, fg=self.DIM,
                 anchor="w").pack(side="left")
        self._pct_lbl = tk.Label(ptop, text="",
                 font=self.F_H2, bg=self.BG, fg=self.ACC3)
        self._pct_lbl.pack(side="right")
        self._progbar = SlimProgress(prog_f)
        self._progbar.pack(fill="x", pady=(4,0))

        # ── RIGHT COLUMN ───────────────────────────
        # Format options
        self._section_label(right, "03  Output Format")
        oc = self._card(right)

        fg2 = tk.Frame(oc, bg=self.CARD)
        fg2.pack(fill="x", pady=(0,4))
        FCOLS = 5
        for idx, fmt in enumerate(sorted(VIDEO_FORMATS.keys())):
            rr, cc = divmod(idx, FCOLS)
            b = tk.Button(fg2, text=fmt,
                          font=("Courier New",7,"bold"),
                          bg=self.CARD2, fg=self.TEXT2,
                          activebackground=self.ACC, activeforeground="white",
                          relief="flat", bd=0, padx=2, pady=4, width=5,
                          cursor="hand2",
                          command=lambda fmt2=fmt: self._pick_fmt(fmt2))
            b.grid(row=rr, column=cc, padx=2, pady=2)
            self._fmt_btns[fmt] = b

        self._fmt_info_lbl = tk.Label(oc, text="",
                 font=self.F_SMALL, bg=self.CARD, fg=self.DIM, anchor="w")
        self._fmt_info_lbl.pack(fill="x", pady=(4,0))
        self._pick_fmt(".mp4")

        # Text Algorithm
        self._section_label(right, "04  Text Algorithm")
        ta_c = self._card(right)
        for lab in TEXT_ALGORITHMS:
            tk.Radiobutton(ta_c, text=lab, variable=self._algo_var, value=lab,
                           font=self.F_MONO, bg=self.CARD, fg=self.TEXT2,
                           selectcolor=self.ACC, activebackground=self.CARD,
                           activeforeground=self.ACC3
                           ).pack(anchor="w", pady=2)

        # Result
        self._section_label(right, "Result")
        rc = self._card(right)

        self._result_cv = tk.Canvas(rc, bg=self.CARD,
                                     highlightthickness=0, height=88)
        self._result_cv.pack(fill="x")
        self._result_cv.after(100, self._draw_placeholder)

        self._result_text = tk.Text(rc, height=5,
                 bg=self.CARD, fg=self.TEXT, font=self.F_MONO,
                 relief="flat", bd=0, padx=8, pady=6,
                 state="disabled", insertbackground=self.TEXT)
        self._result_text.pack(fill="x", pady=(6,0))
        for tag, col in [("grn", self.GREEN2),("red", self.RED2),
                          ("yel",self.YELLOW2),("blu",self.ACC3),("dim",self.DIM)]:
            self._result_text.tag_config(tag, foreground=col)

    # ─────────────────────────────────────────────────
    #  WEBCAM TAB
    # ─────────────────────────────────────────────────
    def _build_webcam_tab(self):
        f = tk.Frame(self._content_area, bg=self.BG)
        self._content_frames["webcam"] = f
        self._splash_tab(f,
            icon="📷", title="Webcam Recorder",
            desc="Record video directly from your webcam.\nThe recording will be auto-loaded for compression.",
            btn_text="Open Webcam Recorder",
            btn_color=self.ACC,
            cmd=self._open_webcam)

    # ─────────────────────────────────────────────────
    #  SCREEN RECORD TAB
    # ─────────────────────────────────────────────────
    def _build_screen_tab(self):
        f = tk.Frame(self._content_area, bg=self.BG)
        self._content_frames["screen"] = f
        self._splash_tab(f,
            icon="⬛", title="Screen Recorder",
            desc="Record your screen using FFmpeg.\nRequires FFmpeg to be installed. Saves as MP4.",
            btn_text="Open Screen Recorder",
            btn_color=self.PURPLE,
            cmd=self._open_screen)

    # ─────────────────────────────────────────────────
    #  ADB TOOLS TAB
    # ─────────────────────────────────────────────────
    def _build_adb_tab(self):
        import threading as _threading
        from datetime import datetime as _datetime

        ADB_BG    = "#0d1117"; ADB_CARD  = "#1c2128"; ADB_INPUT = "#21262d"
        ADB_ACC   = "#58a6ff"; ADB_AH    = "#79b8ff"; ADB_PRI   = "#e6edf3"
        ADB_SEC   = "#8b949e"; ADB_OK    = "#3fb950"; ADB_WARN  = "#d29922"
        ADB_ERR   = "#f85149"; ADB_BDR   = "#30363d"
        F_MONO    = ("Courier New", 9)
        F_HEAD    = ("Courier New", 10, "bold")
        F_LBL     = ("Courier New", 8, "bold")

        f = tk.Frame(self._content_area, bg=ADB_BG)
        self._content_frames["adb"] = f

        # ── Sub-page state ────────────────────────────
        adb_active_btn   = [None]
        adb_log_proc     = [None]
        adb_save_dir     = tk.StringVar(value=os.path.expanduser("~"))

        # ── Layout: sidebar + content ─────────────────
        adb_side = tk.Frame(f, bg="#161b22", width=190)
        adb_side.pack(side="left", fill="y")
        adb_side.pack_propagate(False)

        adb_main = tk.Frame(f, bg=ADB_BG)
        adb_main.pack(side="left", fill="both", expand=True)

        # Sidebar logo
        logo_row = tk.Frame(adb_side, bg="#161b22")
        logo_row.pack(fill="x", pady=(20,10), padx=14)
        tk.Label(logo_row, text="🐞", font=("Courier", 18, "bold"),
                 fg=ADB_ACC, bg="#161b22").pack(side="left")
        tk.Label(logo_row, text=" ADB Tools", font=("Courier", 12, "bold"),
                 fg=ADB_PRI, bg="#161b22").pack(side="left")
        tk.Frame(adb_side, bg=ADB_BDR, height=1).pack(fill="x", padx=14, pady=(0,10))

        adb_pages = {}

        def _adb_nav_btn(label, pid):
            btn = tk.Button(adb_side, text=label, anchor="w",
                font=("Courier", 9), fg=ADB_SEC, bg="#161b22",
                relief="flat", cursor="hand2", padx=12, pady=9,
                activeforeground=ADB_PRI, activebackground=ADB_CARD,
                command=lambda p=pid: _adb_switch(p))
            btn.pack(fill="x", padx=8, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(
                bg=ADB_CARD if b is not adb_active_btn[0] else ADB_ACC,
                fg=ADB_PRI  if b is not adb_active_btn[0] else "#0d1117"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(
                bg=ADB_ACC  if b is adb_active_btn[0] else "#161b22",
                fg="#0d1117" if b is adb_active_btn[0] else ADB_SEC))
            return btn

        def _adb_switch(pid):
            if adb_active_btn[0]:
                adb_active_btn[0].configure(bg="#161b22", fg=ADB_SEC)
            btn_map = {"bugreport": btn_bug, "logcat": btn_log}
            adb_active_btn[0] = btn_map[pid]
            adb_active_btn[0].configure(bg=ADB_ACC, fg="#0d1117")
            for k, pg in adb_pages.items():
                if k == pid: pg.pack(fill="both", expand=True, padx=24, pady=24)
                else:        pg.pack_forget()

        btn_bug = _adb_nav_btn("🐞  Bug Report", "bugreport")
        btn_log = _adb_nav_btn("📋  ADB Logs",   "logcat")

        # Save location
        tk.Frame(adb_side, bg=ADB_BDR, height=1).pack(fill="x", padx=14, pady=12)
        sl = tk.Frame(adb_side, bg="#161b22"); sl.pack(fill="x", padx=14)
        tk.Label(sl, text="SAVE LOCATION", font=("Courier",7,"bold"),
                 fg=ADB_SEC, bg="#161b22").pack(anchor="w")
        dir_row2 = tk.Frame(sl, bg=ADB_INPUT, highlightbackground=ADB_BDR,
                            highlightthickness=1); dir_row2.pack(fill="x", pady=(4,0))
        tk.Label(dir_row2, textvariable=adb_save_dir, font=("Courier",7), fg=ADB_SEC,
                 bg=ADB_INPUT, anchor="w", wraplength=130, justify="left"
                 ).pack(side="left", fill="x", expand=True, padx=6, pady=5)
        def _adb_browse():
            d = filedialog.askdirectory(initialdir=adb_save_dir.get(), title="Choose save folder")
            if d: adb_save_dir.set(d)
        tk.Button(dir_row2, text="…", font=("Courier",8,"bold"), fg=ADB_ACC, bg=ADB_INPUT,
                  relief="flat", cursor="hand2", activeforeground=ADB_AH,
                  activebackground=ADB_INPUT, command=_adb_browse).pack(side="right", padx=4)

        # ── Output box helper ─────────────────────────
        def _mk_outbox(parent, h=10):
            wrap = tk.Frame(parent, bg=ADB_CARD, highlightbackground=ADB_BDR,
                            highlightthickness=1); wrap.pack(fill="both", expand=True)
            sb = tk.Scrollbar(wrap); sb.pack(side="right", fill="y")
            tb = tk.Text(wrap, bg=ADB_CARD, fg=ADB_PRI, font=("Courier New",9),
                         relief="flat", wrap="word", height=h,
                         yscrollcommand=sb.set, padx=12, pady=10,
                         insertbackground=ADB_ACC, selectbackground=ADB_ACC,
                         selectforeground="#0d1117")
            tb.pack(fill="both", expand=True)
            sb.configure(command=tb.yview)
            tb.configure(state="disabled")
            return tb

        def _adb_append(tb, text):
            tb.configure(state="normal")
            tb.insert("end", text)
            tb.see("end")
            tb.configure(state="disabled")

        def _mk_btn(parent, text, cmd, color=None):
            c = color or ADB_ACC
            btn = tk.Button(parent, text=text, command=cmd,
                            font=("Courier",9,"bold"), fg="#0d1117", bg=c,
                            relief="flat", cursor="hand2", padx=14, pady=7,
                            activeforeground="#0d1117",
                            activebackground=ADB_AH, disabledforeground="#555")
            def _lc(h, b=btn, orig=c):
                r,g,b2 = int(orig[1:3],16),int(orig[3:5],16),int(orig[5:7],16)
                r,g,b2 = min(r+28,255),min(g+28,255),min(b2+28,255)
                btn.configure(bg=f"#{r:02x}{g:02x}{b2:02x}" if h else orig)
            btn.bind("<Enter>", lambda e: _lc(True))
            btn.bind("<Leave>", lambda e: _lc(False))
            return btn

        def _ph_entry(entry, ph):
            entry.insert(0, ph); entry.configure(fg=ADB_SEC)
            entry.bind("<FocusIn>",  lambda e: (entry.delete(0,"end"),
                                                entry.configure(fg=ADB_PRI))
                                               if entry.get()==ph else None)
            entry.bind("<FocusOut>", lambda e: (entry.insert(0,ph),
                                                entry.configure(fg=ADB_SEC))
                                               if not entry.get() else None)

        # ══ BUG REPORT PAGE ══════════════════════════
        pg_bug = tk.Frame(adb_main, bg=ADB_BG)
        adb_pages["bugreport"] = pg_bug

        tk.Label(pg_bug, text="Bug Report", font=("Courier",18,"bold"),
                 fg=ADB_PRI, bg=ADB_BG).pack(anchor="w")
        tk.Label(pg_bug, text="Capture a full device bug report via ADB.",
                 font=("Courier",9), fg=ADB_SEC, bg=ADB_BG).pack(anchor="w", pady=(2,14))

        bug_card = tk.Frame(pg_bug, bg=ADB_CARD, highlightbackground=ADB_BDR,
                            highlightthickness=1); bug_card.pack(fill="x")
        bug_inner = tk.Frame(bug_card, bg=ADB_CARD); bug_inner.pack(fill="x", padx=20, pady=16)
        tk.Label(bug_inner, text="Device ID  (serial number)", font=F_LBL,
                 fg=ADB_SEC, bg=ADB_CARD).pack(anchor="w")
        id_wrap = tk.Frame(bug_inner, bg=ADB_INPUT, highlightbackground=ADB_BDR,
                           highlightthickness=1); id_wrap.pack(fill="x", pady=(4,12))
        bug_dev_var = tk.StringVar()
        bug_entry = tk.Entry(id_wrap, textvariable=bug_dev_var, font=("Courier",10),
                             fg=ADB_PRI, bg=ADB_INPUT, relief="flat",
                             insertbackground=ADB_ACC)
        bug_entry.pack(fill="x", padx=10, pady=8)
        _ph_entry(bug_entry, "e.g. emulator-5554 or R5CT61234AB")

        bug_run_btn = _mk_btn(bug_inner, "▶  Run Bug Report", lambda: None)
        bug_run_btn.pack(anchor="w")

        bug_out = _mk_outbox(pg_bug, h=12)
        bug_out.pack(fill="both", expand=True, pady=(16,0))

        def _run_bugreport():
            dev = bug_dev_var.get().strip()
            ph  = "e.g. emulator-5554 or R5CT61234AB"
            if not dev or dev == ph:
                messagebox.showerror("Missing Device ID",
                    "Please enter a valid device serial number."); return
            sdir = adb_save_dir.get()
            if not os.path.isdir(sdir):
                messagebox.showerror("Invalid Directory",
                    f"Save location does not exist:\n{sdir}"); return
            ts   = _datetime.now().strftime("%Y%m%d_%H%M%S")
            out  = os.path.join(sdir, f"bugreport_{dev}_{ts}.zip")
            cmd  = ["adb", "-s", dev, "bugreport", out]
            _adb_append(bug_out, f"$ {' '.join(cmd)}\n\nRunning — this may take a minute…\n")
            bug_run_btn.configure(state="disabled", text="⏳ Running…")
            def worker():
                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:
                        f.after(0, _adb_append, bug_out, line)
                    proc.wait()
                    msg = (f"\n✅  Saved to:\n{out}\n" if proc.returncode == 0
                           else f"\n❌  adb exited with code {proc.returncode}\n")
                except FileNotFoundError:
                    msg = "\n❌  'adb' not found. Add Android SDK platform-tools to PATH.\n"
                except Exception as ex:
                    msg = f"\n❌  Error: {ex}\n"
                f.after(0, _adb_append, bug_out, msg)
                f.after(0, bug_run_btn.configure,
                        {"state": "normal", "text": "▶  Run Bug Report"})
            _threading.Thread(target=worker, daemon=True).start()

        bug_run_btn.configure(command=_run_bugreport)

        # ══ LOGCAT PAGE ══════════════════════════════
        pg_log = tk.Frame(adb_main, bg=ADB_BG)
        adb_pages["logcat"] = pg_log

        tk.Label(pg_log, text="ADB Logs", font=("Courier",18,"bold"),
                 fg=ADB_PRI, bg=ADB_BG).pack(anchor="w")
        tk.Label(pg_log, text="Stream live logcat output from a connected device.",
                 font=("Courier",9), fg=ADB_SEC, bg=ADB_BG).pack(anchor="w", pady=(2,14))

        log_card = tk.Frame(pg_log, bg=ADB_CARD, highlightbackground=ADB_BDR,
                            highlightthickness=1); log_card.pack(fill="x")
        log_inner = tk.Frame(log_card, bg=ADB_CARD)
        log_inner.pack(fill="x", padx=20, pady=16)
        btn_row = tk.Frame(log_inner, bg=ADB_CARD); btn_row.pack(fill="x")

        log_run_btn  = _mk_btn(btn_row, "▶  Start Logcat", lambda: None)
        log_run_btn.pack(side="left")
        log_stop_btn = _mk_btn(btn_row, "⏹  Stop", lambda: None, color=ADB_ERR)
        log_stop_btn.pack(side="left", padx=(10,0))
        log_stop_btn.configure(state="disabled")
        log_save_btn = _mk_btn(btn_row, "💾  Save Log", lambda: None, color=ADB_OK)
        log_save_btn.pack(side="left", padx=(10,0))
        log_save_btn.configure(state="disabled")

        log_out = _mk_outbox(pg_log, h=18)
        log_out.pack(fill="both", expand=True, pady=(16,0))

        def _start_logcat():
            if adb_log_proc[0]: return
            sdir = adb_save_dir.get()
            if not os.path.isdir(sdir):
                messagebox.showerror("Invalid Directory",
                    f"Save location does not exist:\n{sdir}"); return
            cmd = ["adb", "logcat"]
            _adb_append(log_out, f"$ {' '.join(cmd)}\n\n")
            log_run_btn.configure(state="disabled")
            log_stop_btn.configure(state="normal")
            log_save_btn.configure(state="disabled")
            def stream():
                try:
                    adb_log_proc[0] = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                                        stderr=subprocess.STDOUT, text=True)
                    for line in adb_log_proc[0].stdout:
                        f.after(0, _adb_append, log_out, line)
                except FileNotFoundError:
                    f.after(0, _adb_append, log_out,
                            "\n❌  'adb' not found. Add platform-tools to PATH.\n")
                except Exception as ex:
                    f.after(0, _adb_append, log_out, f"\n❌  {ex}\n")
                finally:
                    adb_log_proc[0] = None
                    f.after(0, log_run_btn.configure,  {"state": "normal"})
                    f.after(0, log_stop_btn.configure, {"state": "disabled"})
                    f.after(0, log_save_btn.configure, {"state": "normal"})
            _threading.Thread(target=stream, daemon=True).start()

        def _stop_logcat():
            if adb_log_proc[0]:
                adb_log_proc[0].terminate()
                adb_log_proc[0] = None
            log_run_btn.configure(state="normal")
            log_stop_btn.configure(state="disabled")
            log_save_btn.configure(state="normal")

        def _save_log():
            content = log_out.get("1.0", "end-1c")
            if not content.strip():
                messagebox.showinfo("Nothing to save", "The log is empty."); return
            ts  = _datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(adb_save_dir.get(), f"logcat_{ts}.txt")
            try:
                with open(out, "w", encoding="utf-8") as fh:
                    fh.write(content)
                messagebox.showinfo("Saved", f"Log saved to:\n{out}")
            except Exception as ex:
                messagebox.showerror("Save Failed", str(ex))

        log_run_btn.configure(command=_start_logcat)
        log_stop_btn.configure(command=_stop_logcat)
        log_save_btn.configure(command=_save_log)

        # Default sub-page
        _adb_switch("bugreport")

    # ─────────────────────────────────────────────────
    #  SETTINGS TAB
    # ─────────────────────────────────────────────────
    def _build_settings_tab(self):
        f = tk.Frame(self._content_area, bg=self.BG)
        self._content_frames["settings"] = f

        inner = tk.Frame(f, bg=self.BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="⚙", font=("Segoe UI",42),
                 bg=self.BG, fg=self.BORDER2).pack()
        tk.Label(inner, text="Settings",
                 font=("Segoe UI",18,"bold"), bg=self.BG, fg=self.TEXT).pack(pady=(4,2))
        tk.Label(inner, text="FFmpeg path and installation",
                 font=self.F_BODY, bg=self.BG, fg=self.DIM).pack()

        btn_f = tk.Frame(inner, bg=self.BG)
        btn_f.pack(pady=20)

        tk.Button(btn_f, text="  Install / Update FFmpeg  ",
                  font=("Segoe UI",10,"bold"),
                  bg=self.YELLOW, fg="#0d0d0d",
                  activebackground=self.YELLOW2,
                  relief="flat", bd=0, padx=16, pady=10,
                  cursor="hand2", command=self._open_install
                  ).pack(side="left", padx=6)

        tk.Button(btn_f, text="  Check FFmpeg Status  ",
                  font=("Segoe UI",10,"bold"),
                  bg=self.CARD, fg=self.ACC3,
                  activebackground=self.CARD2,
                  relief="flat", bd=0, padx=16, pady=10,
                  cursor="hand2", command=self._check_ffmpeg_msg
                  ).pack(side="left", padx=6)

    # ─────────────────────────────────────────────────
    #  SPLASH / LAUNCHER TEMPLATE
    # ─────────────────────────────────────────────────
    def _splash_tab(self, parent, icon, title, desc, btn_text, btn_color, cmd):
        inner = tk.Frame(parent, bg=self.BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Icon badge
        badge_f = tk.Frame(inner, bg=self.CARD,
                           highlightthickness=2, highlightbackground=self.BORDER2)
        badge_f.pack(pady=(0,16))
        tk.Label(badge_f, text=icon, font=("Segoe UI",48),
                 bg=self.CARD, padx=30, pady=20).pack()

        tk.Label(inner, text=title,
                 font=("Segoe UI",18,"bold"), bg=self.BG, fg=self.TEXT).pack()
        tk.Label(inner, text=desc,
                 font=self.F_BODY, bg=self.BG, fg=self.DIM,
                 justify="center").pack(pady=(6,20))

        tk.Button(inner, text=f"  {btn_text}  ",
                  font=("Segoe UI",11,"bold"),
                  bg=btn_color, fg="white",
                  activebackground=self.ACC3,
                  relief="flat", bd=0, padx=20, pady=12,
                  cursor="hand2", command=cmd).pack()

        # Tip
        tk.Label(inner, text="Recording will be auto-loaded into the Compress tab.",
                 font=self.F_SMALL, bg=self.BG, fg=self.BORDER2).pack(pady=(12,0))

    # ─────────────────────────────────────────────────
    #  WIDGET HELPERS
    # ─────────────────────────────────────────────────
    def _section_label(self, parent, text):
        row = tk.Frame(parent, bg=self.BG)
        row.pack(fill="x", pady=(10,4))
        tk.Label(row, text=text, font=self.F_H2,
                 bg=self.BG, fg=self.ACC3).pack(side="left")
        tk.Frame(row, bg=self.BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(8,0), pady=6)

    def _card(self, parent):
        c = tk.Frame(parent, bg=self.CARD,
                     highlightthickness=1, highlightbackground=self.BORDER2,
                     padx=12, pady=10)
        c.pack(fill="x", pady=(0,4))
        return c

    # ─────────────────────────────────────────────────
    #  TAB SWITCHING
    # ─────────────────────────────────────────────────
    def _show_tab(self, key):
        self._active_tab.set(key)
        titles = {
            "compress": "Compress File",
            "webcam":   "Webcam Recorder",
            "screen":   "Screen Recorder",
            "adb":      "ADB Tools",
            "settings": "Settings",
        }
        self._topbar_title.config(text=titles.get(key, key.title()))
        for k, btn in self._nav_btns.items():
            btn.config(
                bg=self.CARD if k == key else self.PANEL,
                fg=self.TEXT if k == key else self.TEXT2)
        for k, frame in self._content_frames.items():
            if k == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # ─────────────────────────────────────────────────
    #  FFMPEG
    # ─────────────────────────────────────────────────
    def _check_ffmpeg(self):
        if ffmpeg_exe():
            self._ff_status_lbl.config(text="✓ FFmpeg ready", fg=self.GREEN2)
            self._ff_btn.pack_forget()
        else:
            self._ff_status_lbl.config(text="✗ FFmpeg missing", fg=self.YELLOW2)
            self._ff_btn.pack(fill="x", pady=(4,0))

    def _check_ffmpeg_msg(self):
        p = ffmpeg_exe()
        if p:
            messagebox.showinfo("FFmpeg Status", f"FFmpeg is installed.\n\n{p}")
        else:
            messagebox.showwarning("FFmpeg Status", "FFmpeg is NOT installed.")

    def _open_install(self):
        FFmpegDialog(self, on_success=self._check_ffmpeg)

    # ─────────────────────────────────────────────────
    #  RECORDERS
    # ─────────────────────────────────────────────────
    def _open_webcam(self):
        WebcamRecorder(self, on_file_ready=self._load_recorded)

    def _open_screen(self):
        ScreenRecorder(self, on_file_ready=self._load_recorded)

    def _load_recorded(self, path):
        self._src_sv.set(path)
        p   = Path(path)
        ext = self._out_fmt.get()
        self._dst_sv.set(str(p.parent / (p.stem + "_compressed" + ext)))
        sz  = get_file_size(path)
        self._file_lbl.config(text=f"  {p.name}   {human_size(sz)}  (recorded)")
        self._status_sv.set(f"Loaded: {human_size(sz)}")
        self._show_tab("compress")

    # ─────────────────────────────────────────────────
    #  SIZE PICKER
    # ─────────────────────────────────────────────────
    def _pick_preset(self, kb, label):
        self._target_kb = float(kb)
        for k, b in self._preset_btns.items():
            b.config(bg=self.ACC if k == kb else self.CARD2,
                     fg="white" if k == kb else self.TEXT2)
        if kb >= 1048576:
            self._num_entry.delete(0,"end")
            self._num_entry.insert(0, f"{kb/1048576:.0f}")
            self._set_unit("GB")
        elif kb >= 1024:
            self._num_entry.delete(0,"end")
            self._num_entry.insert(0, f"{kb/1024:.0f}")
            self._set_unit("MB")
        else:
            self._num_entry.delete(0,"end")
            self._num_entry.insert(0, str(int(kb)))
            self._set_unit("KB")
        self._refresh_target(kb)

    def _set_unit(self, u):
        self._unit.set(u)
        for k, b in self._unit_btns.items():
            b.config(bg=self.ACC if k == u else self.CARD2,
                     fg="white" if k == u else self.TEXT2)

    def _apply_custom(self, _=None):
        try: v = float(self._num_entry.get())
        except ValueError: return
        u = self._unit.get()
        if u == "MB": v *= 1024
        elif u == "GB": v *= 1048576
        v = max(10.0, v)
        self._target_kb = v
        for k, b in self._preset_btns.items():
            b.config(bg=self.ACC if abs(k-v) < 1 else self.CARD2,
                     fg="white" if abs(k-v) < 1 else self.TEXT2)
        self._refresh_target(v)

    def _refresh_target(self, kb):
        self._target_lbl.config(text=f"→  {human_size(kb * 1024)}")

    # ─────────────────────────────────────────────────
    #  FORMAT
    # ─────────────────────────────────────────────────
    def _pick_fmt(self, fmt):
        self._out_fmt.set(fmt)
        for f, b in self._fmt_btns.items():
            b.config(bg=self.ACC if f == fmt else self.CARD2,
                     fg="white" if f == fmt else self.TEXT2)
        c = VIDEO_FORMATS.get(fmt, {})
        self._fmt_info_lbl.config(
            text=f"  {c.get('codec','?')} / {c.get('acodec','?')}  {'2-pass' if c.get('two_pass') else '1-pass'}")
        dst = self._dst_sv.get()
        if dst:
            self._dst_sv.set(str(Path(dst).with_suffix(fmt)))

    # ─────────────────────────────────────────────────
    #  BROWSE
    # ─────────────────────────────────────────────────
    def _browse_src(self):
        vid  = " ".join("*"+e for e in sorted(VIDEO_EXT))
        txt  = " ".join("*"+e for e in sorted(TEXT_EXT))
        all_ = " ".join("*"+e for e in sorted(ALL_EXT))
        path = filedialog.askopenfilename(
            title="Select file to compress",
            filetypes=[("All supported", all_),("Video", vid),("Text", txt),("All files","*.*")])
        if not path: return
        self._src_sv.set(path)
        p = Path(path); ext = p.suffix.lower()
        out_ext = self._out_fmt.get() if ext in VIDEO_EXT else ext
        self._dst_sv.set(str(p.parent / (p.stem + "_compressed" + out_ext)))
        sz = get_file_size(path)
        self._file_lbl.config(text=f"  {p.name}   Original: {human_size(sz)}")
        self._status_sv.set(f"Loaded: {human_size(sz)}")

    def _browse_dst(self):
        src = self._src_sv.get()
        de  = (self._out_fmt.get() if Path(src).suffix.lower() in VIDEO_EXT
               else (Path(src).suffix if src else ".mp4"))
        path = filedialog.asksaveasfilename(title="Save output as",
            defaultextension=de,
            filetypes=[("Video"," ".join("*"+e for e in sorted(VIDEO_EXT))),
                       ("Text"," ".join("*"+e for e in sorted(TEXT_EXT))),
                       ("All files","*.*")])
        if path: self._dst_sv.set(path)

    # ─────────────────────────────────────────────────
    #  COMPRESSION
    # ─────────────────────────────────────────────────
    def _set_progress(self, pct, msg=""):
        pct = float(pct)
        self._progbar.set_value(pct)
        self._pct_lbl.config(text=f"{pct:.0f}%")
        if msg: self._status_sv.set(msg)
        self.update_idletasks()

    def _start_compress(self):
        if self._compress_busy: return
        src = self._src_sv.get().strip()
        dst = self._dst_sv.get().strip()
        in_ext = Path(src).suffix.lower() if src else ""
        ox     = Path(dst).suffix.lower() if dst else ""
        if not src or not os.path.isfile(src):
            messagebox.showerror("No File", "Select a source file first."); return
        if not dst:
            messagebox.showerror("No Output", "Set an output path."); return
        is_vid = in_ext in VIDEO_EXT
        is_txt = in_ext in TEXT_EXT
        if not is_vid and not is_txt:
            messagebox.showwarning("Unsupported", f"'{in_ext}' is not supported."); return
        if is_vid and ox not in VIDEO_FORMATS:
            messagebox.showerror("Bad Format", f"'{ox}' not supported."); return

        self._compress_busy = True
        self._compress_btn.config(state="disabled", text="  Compressing…  ", bg=self.DIM)
        self._rc(); self._draw_placeholder()
        self._progbar.reset(); self._pct_lbl.config(text="0%")

        target   = self._target_kb
        src_name = Path(src).name

        def worker():
            try:
                def cb(p, m=""): self.after(0, lambda p=p, m=m: self._set_progress(p, m))
                if is_vid: r = compress_video(src, dst, target, cb)
                else:
                    algo = TEXT_ALGORITHMS[self._algo_var.get()]
                    r = compress_text(src, dst, algo, target, cb)
                self.after(0, lambda: self._on_done(r, src_name, is_vid, ox))
            except Exception as exc:
                msg = str(exc)
                if "__FFMPEG_MISSING__" in msg:
                    self.after(60, self._no_ffmpeg)
                else:
                    self.after(60, lambda: self._show_error(msg))
            finally:
                self.after(0, self._compress_done)

        threading.Thread(target=worker, daemon=True).start()

    def _compress_done(self):
        self._compress_busy = False
        self._compress_btn.config(state="normal", text="  COMPRESS NOW  ", bg=self.ACC)

    def _on_done(self, r, src_name, is_vid, out_ext):
        self._progbar.set_value(100)
        self._pct_lbl.config(text="100%")
        self._status_sv.set(
            f"Done — {human_size(r['compressed_size'])}  (±{r['accuracy_pct']:.1f}%)")
        self._draw_result_bars(r["original_size"], r["compressed_size"], r["target_bytes"])
        self._show_result_text(r, src_name, is_vid, out_ext)
        CompletionPopup(self, r, src_name)

    def _no_ffmpeg(self):
        self._progbar.reset(); self._pct_lbl.config(text="0%")
        self._rc()
        self._rw("FFmpeg required for video compression.\n", "yel")
        self._rw("Go to Settings to install it.\n", "dim")
        self._open_install()

    def _show_result_text(self, r, src_name, is_vid, out_ext):
        self._rc()
        orig  = r["original_size"]; comp = r["compressed_size"]
        ratio = r["ratio"]; acc = r["accuracy_pct"]
        tgt   = r["target_bytes"]; saved = orig - comp; over = comp > tgt
        if   acc <= 10: badge, a_tag = "Excellent", "grn"
        elif acc <= 25: badge, a_tag = "Good",       "yel"
        else:           badge, a_tag = "Off target", "red"
        self._rw(f"Original: {human_size(orig)}   Target: {human_size(tgt)}\n", "dim")
        tag = "grn" if not over else "yel"
        self._rw(f"Result:   {human_size(comp)}  ({'over' if over else 'under'} by {human_size(abs(comp-tgt))})\n", tag)
        self._rw(f"Saved:    {human_size(saved) if saved > 0 else 'None'}  ({ratio:.1f}% reduction)\n",
                 "grn" if ratio > 0 else "red")
        self._rw(f"Accuracy: {badge}  ±{acc:.1f}%\n", a_tag)
        self._rw(f"Path:     {r['output_path']}\n", "blu")

    def _show_error(self, msg):
        self._draw_placeholder()
        self._rc()
        self._rw("Error\n\n", "red")
        self._rw(f"{msg}\n", "dim")
        self._status_sv.set("Error — see result panel.")
        self._progbar.reset(); self._pct_lbl.config(text="0%")

    def _rw(self, t, tag=None):
        self._result_text.config(state="normal")
        self._result_text.insert("end", t, tag or "")
        self._result_text.config(state="disabled")

    def _rc(self):
        self._result_text.config(state="normal")
        self._result_text.delete("1.0","end")
        self._result_text.config(state="disabled")

    def _draw_placeholder(self):
        try:
            cv = self._result_cv; cv.delete("all")
            W = cv.winfo_width() or 400
            H = cv.winfo_height() or 88
            cv.create_text(W//2, H//2,
                           text="Results will appear here",
                           font=("Segoe UI",9), fill=self.BORDER2)
        except tk.TclError: pass

    def _draw_result_bars(self, orig, comp, tgt):
        try:
            cv = self._result_cv; cv.update_idletasks(); cv.delete("all")
            W = cv.winfo_width() or 400; mv = max(orig, comp, tgt, 1)
            BH = 18; LW = 72; PAD = 8; bw = W - LW - PAD
            def bar(y, val, color, label, txt):
                fw = max(4, int(bw * val / mv))
                cv.create_text(LW-5, y+BH//2, text=label,
                               font=("Segoe UI",7,"bold"), fill=self.DIM, anchor="e")
                cv.create_rectangle(LW, y, LW+bw, y+BH, fill="#1a1a1a", outline="")
                for i in range(fw):
                    cv.create_line(LW+i, y, LW+i, y+BH,
                                   fill=lerp_color(color,"#ffffff", i/max(fw,1)*0.2))
                cv.create_text(LW+fw+5, y+BH//2, text=txt,
                               font=("Segoe UI",7,"bold"), fill=self.TEXT, anchor="w")
            bar(6,  orig, "#3a3a3a",    "Original",  human_size(orig))
            bar(32, tgt,  self.ACC,     "Target",    human_size(tgt))
            c = self.GREEN2 if comp <= tgt*1.1 else self.YELLOW2
            bar(58, comp, c,            "Result",    human_size(comp))
        except tk.TclError: pass

# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    App().mainloop()