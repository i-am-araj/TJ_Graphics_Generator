"""
Tractor Sales Infographic Generator — Streamlit UI
===================================================
Folder structure (put all files in the same folder as this script):

  your_project/
  ├── App.py                        ← this file
  ├── assets/
  │   ├── Background.jpg
  │   ├── TJ_New_Logo.png
  │   ├── mahindra-1673872647.png
  │   ├── mahindra.png
  │   ├── swaraj-1608095532.webp
  │   ├── swaraj.png
  │   ├── sonalika_New_Logo_HD.png
  │   ├── escorts_kubota_logo.png
  │   ├── esctorts_kubota.png
  │   ├── John_Deere_logo_svg.png
  │   ├── john_deere.png
  │   ├── eicher-logo.png
  │   ├── eicher.png
  │   ├── new_holland_logo.png
  │   ├── new_holland.png
  │   ├── tafe.png
  │   └── others.png
  └── output/                       ← generated PNGs saved here (auto-created)

Run:
  streamlit run App.py
"""

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os, sys, math, io, json, copy, platform

# ══════════════════════════════════════════════════════════════════
#  PATHS  ★ Edit BASE to match your project folder ★
# ══════════════════════════════════════════════════════════════════
BASE_DIR    = r"D:\Python\Projects\Graphic Generator"
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
LOGOS_DIR   = os.path.join(BASE_DIR, "assets", "logos")
TRACTORS_DIR= os.path.join(BASE_DIR, "assets", "tractors")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")

for _d in (ASSETS_DIR, LOGOS_DIR, TRACTORS_DIR, OUTPUT_DIR):
    os.makedirs(_d, exist_ok=True)

def asset(filename):
    """Root assets folder — for Background.jpg, TJ_New_Logo.png etc."""
    return os.path.join(ASSETS_DIR, filename)

def logo(filename):
    """assets/logos/ folder."""
    return os.path.join(LOGOS_DIR, filename)

def tractor(filename):
    """assets/tractors/ folder."""
    return os.path.join(TRACTORS_DIR, filename)

# ── Font paths  ★ Edit if you want a different font ★ ────────────
#  Place Barlow .ttf files in assets/fonts/ to override these.
#  Falls back to Arial on Windows, Liberation on Linux.
def find_font(bold=True):
    win = os.environ.get("WINDIR", r"C:\Windows")
    # 1. Check assets/fonts/ first (works on all platforms incl. Cloud)
    bundled = os.path.join(BASE_DIR, "assets", "fonts")
    if os.path.isdir(bundled):
        for f in sorted(os.listdir(bundled)):
            if not f.lower().endswith(".ttf"):
                continue
            fl = f.lower()
            if bold and any(w in fl for w in ("bold","black","heavy")):
                return os.path.join(bundled, f)
            if not bold and any(w in fl for w in ("regular","light","medium")):
                return os.path.join(bundled, f)
    # 2. System fonts fallback
    system_fonts = (
        [os.path.join(win,"Fonts","arialbd.ttf"),
         os.path.join(win,"Fonts","calibrib.ttf")]
        if bold else
        [os.path.join(win,"Fonts","arial.ttf"),
         os.path.join(win,"Fonts","calibri.ttf")]
    ) + (
        ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for p in system_fonts:
        if os.path.exists(p):
            return p
    return None

FONT_BOLD_PATH    = find_font(bold=True)
FONT_REGULAR_PATH = find_font(bold=False)

# ══════════════════════════════════════════════════════════════════
#  BRAND LIST
#  Logo  file : assets/logos/<BrandName>.png
#  Tractor file: assets/tractors/<BrandName>.png
#  (no mapping needed — filename = brand name)
# ══════════════════════════════════════════════════════════════════
ALL_BRANDS = [
    "Mahindra", "Swaraj", "Sonalika", "Kubota", "TAFE",
    "John Deere", "Eicher", "New Holland", "Others",
]

def brand_logo_path(brand):
    """
    Look for assets/logos/<brand>.<ext>
    Tries .png, .jpg, .jpeg, .webp in order.
    File name must exactly match the brand name (case-insensitive).
    """
    if not os.path.isdir(LOGOS_DIR):
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        for f in os.listdir(LOGOS_DIR):
            if f.lower() == (brand + ext).lower():
                return os.path.join(LOGOS_DIR, f)
    return None

def brand_tractor_path(brand):
    """
    Look for assets/tractors/<brand>.<ext>
    Tries .png, .jpg, .jpeg, .webp in order.
    File name must exactly match the brand name (case-insensitive).
    """
    if not os.path.isdir(TRACTORS_DIR):
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        for f in os.listdir(TRACTORS_DIR):
            if f.lower() == (brand + ext).lower():
                return os.path.join(TRACTORS_DIR, f)
    return None

# ══════════════════════════════════════════════════════════════════
#  DEFAULT ROAD POSITIONS  (x, y on 1080×1350 canvas)
# ══════════════════════════════════════════════════════════════════
DEFAULT_POSITIONS = [
    {"x": 200, "y": 1240, "side": "left"},   # rank 1
    {"x": 500, "y": 1120, "side": "right"},  # rank 2
    {"x": 485, "y":  920, "side": "left"},   # rank 3
    {"x": 400, "y":  770, "side": "left"},   # rank 4
    {"x": 585, "y":  700, "side": "right"},  # rank 5
    {"x": 515, "y":  540, "side": "right"},  # rank 6
    {"x": 650, "y":  470, "side": "left"},   # rank 7
    {"x": 800, "y":  420, "side": "left"},  # rank 8
    {"x": 980, "y":  390, "side": "left"},  # rank 9
]

# ══════════════════════════════════════════════════════════════════
#  SIZING TABLES  (index = rank 0–8)
# ══════════════════════════════════════════════════════════════════
TRACTOR_W  = [200,178,160,145,132,120,108, 97, 86]
TRACTOR_H  = [120,107, 96, 87, 79, 72, 65, 58, 52]
LOGO_H     = [ 36, 32, 29, 27, 25, 23, 21, 20, 18]
FONT_UNITS = [ 33, 30, 28, 26, 24, 22, 21, 20, 19]
FONT_YOY   = [ 19, 18, 17, 16, 16, 15, 15, 14, 14]
ARROW_LEN  = [ 90, 80, 72, 66, 60, 55, 50, 46, 42]
LABEL_W    = [230,210,192,178,165,155,146,138,130]

# ══════════════════════════════════════════════════════════════════
#  COLOURS
# ══════════════════════════════════════════════════════════════════
C_TITLE = (232,  33,  42, 255)
C_DARK  = ( 26,  26,  26, 255)
C_WHITE = (255, 255, 255, 255)
C_UP    = ( 34, 165,  71, 255)
C_DOWN  = (232,  33,  42, 255)
C_ARROW = ( 26,  26,  26, 255)


# ══════════════════════════════════════════════════════════════════
#  IMAGE HELPERS
# ══════════════════════════════════════════════════════════════════

@st.cache_data
def remove_black_bg(path, threshold=35):
    img = Image.open(path).convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    brightness = r + g + b
    hard = brightness < threshold
    soft = (brightness >= threshold) & (brightness < threshold + 80)
    new_a = arr[:,:,3].copy()
    new_a[hard] = 0
    new_a[soft] = ((brightness[soft] - threshold) / 80 * 255).clip(0, 255)
    arr[:,:,3] = new_a
    return Image.fromarray(arr.clip(0,255).astype(np.uint8), "RGBA")


def _load_img(path, max_w=500):
    """Internal: load image from full path, remove black bg, resize."""
    if not path or not os.path.exists(path):
        return None
    img = remove_black_bg(path)
    if img.width > max_w:
        r = max_w / img.width
        img = img.resize((max_w, int(img.height * r)), Image.LANCZOS)
    return img

@st.cache_data
def load_root(filename, max_w=500):
    """Load from assets/ root (Background.jpg, TJ logo etc.)"""
    return _load_img(asset(filename) if filename else None, max_w)


def fit_image(img, w, h):
    ir = img.width / img.height
    br = w / h
    nw = w if ir > br else int(h * ir)
    nh = int(w / ir) if ir > br else h
    return img.resize((max(1, nw), max(1, nh)), Image.LANCZOS)


def get_font(size, bold=True):
    path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
    if path and os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def fmt(n):
    return f"{int(n):,}"


def draw_arrow(draw, x1, y1, x2, y2, color=C_ARROW, width=2, head=8):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    spread = math.pi / 6
    for sign in (+1, -1):
        ex = int(x2 - head * math.cos(angle - sign * spread))
        ey = int(y2 - head * math.sin(angle - sign * spread))
        draw.line([(x2, y2), (ex, ey)], fill=color, width=width)


# ══════════════════════════════════════════════════════════════════
#  POSITION OVERLAY
# ══════════════════════════════════════════════════════════════════

def draw_positions_overlay(positions):
    bg_path = asset("Background.jpg")
    if not os.path.exists(bg_path):
        img = Image.new("RGB", (1080, 1350), (210, 210, 210))
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), "Background.jpg not found in assets/",
                  fill=(200, 0, 0), font=get_font(28))
        return img

    bg   = Image.open(bg_path).convert("RGB")
    draw = ImageDraw.Draw(bg)
    font = get_font(20)

    for i, pos in enumerate(positions):
        x, y, side = pos["x"], pos["y"], pos["side"]
        col = (30, 100, 220) if side == "left" else (30, 180, 80)
        r   = 18
        draw.ellipse([x-r, y-r, x+r, y+r], fill=col, outline=(255,255,255), width=3)
        lbl = str(i + 1)
        tw, th = text_size(draw, lbl, font)
        draw.text((x - tw//2, y - th//2), lbl, font=font, fill=(255,255,255))
        arrow = "→" if side == "right" else "←"
        ix = x + r + 4 if side == "right" else x - r - 22
        draw.text((ix, y - 10), arrow, font=font, fill=col)

    return bg


# ══════════════════════════════════════════════════════════════════
#  INFOGRAPHIC RENDERER
# ══════════════════════════════════════════════════════════════════

def generate_infographic(data, report_month, compare_month, total_yoy, positions):
    bg_path = asset("Background.jpg")
    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Background.jpg not found in: {ASSETS_DIR}")

    canvas = Image.open(bg_path).convert("RGBA")
    W, H   = canvas.size
    draw   = ImageDraw.Draw(canvas)

    ranked = sorted(data, key=lambda x: x[1], reverse=True)

    assets_cache = {}
    for brand, units, yoy in ranked:
        if brand not in assets_cache:
            assets_cache[brand] = {
                "logo":    _load_img(brand_logo_path(brand)),
                "tractor": _load_img(brand_tractor_path(brand)),
            }

    tj_logo = load_root("TJ_New_Logo.png", max_w=300)

    # ── Header ────────────────────────────────────────────────────
    f_title = get_font(69, bold=True)
    f_sub   = get_font(31, bold=False)
    f_tlbl  = get_font(46, bold=True)
    f_tyoy  = get_font(33, bold=True)

    tx, ty = 44, 32
    draw.text((tx, ty),    "Tractor Sales", font=f_title, fill=C_TITLE)
    draw.text((tx, ty+73), "in India",      font=f_title, fill=C_TITLE)

    sub = f"Retail Sales {report_month} as compare to {compare_month}"
    sw, sh = text_size(draw, sub, f_sub)
    by = ty + 73 + 73 + 4
    draw.rectangle([tx-4, by, tx+sw+14, by+sh+8], fill=C_DARK)
    draw.text((tx+2, by+4), sub, font=f_sub, fill=C_WHITE)

    total_u = sum(u for _, u, _ in ranked)
    roy = by + sh + 18
    draw.text((tx, roy), "Total:", font=f_tlbl, fill=C_DARK)
    lw2, _ = text_size(draw, "Total: ", f_tlbl)
    nt = f" {fmt(total_u)}"
    draw.text((tx + lw2, roy), nt, font=f_tlbl, fill=C_DARK)
    nw, _ = text_size(draw, nt, f_tlbl)
    yc = C_UP if total_yoy >= 0 else C_DOWN
    ya = "▲" if total_yoy >= 0 else "▼"
    draw.text((tx + lw2 + nw, roy),
              f" {ya}{abs(total_yoy):.2f}% (YoY)", font=f_tyoy, fill=yc)

    # ── TJ Logo ───────────────────────────────────────────────────
    if tj_logo:
        tl_h = 100
        r2   = tl_h / tj_logo.height
        tl   = tj_logo.resize((int(tj_logo.width * r2), tl_h), Image.LANCZOS)
        canvas.paste(tl, (W - tl.width - 26, 24), tl)

    # ── Tractors + Labels + Arrows ────────────────────────────────
    for rank, (brand, units, yoy) in enumerate(ranked):
        pos  = positions[rank]
        rx, ry, side = pos["x"], pos["y"], pos["side"]

        tw  = TRACTOR_W[rank];  th  = TRACTOR_H[rank]
        lh  = LOGO_H[rank]
        fu  = get_font(FONT_UNITS[rank], bold=True)
        fy  = get_font(FONT_YOY[rank],   bold=True)
        al  = ARROW_LEN[rank];  lbw = LABEL_W[rank]

        up      = yoy >= 0
        yoy_col = C_UP   if up else C_DOWN
        yoy_arr = "▲"    if up else "▼"
        yoy_txt = f"{yoy_arr}{abs(yoy):.2f}%"
        unit_txt = fmt(units)

        # 1. Tractor — base at road point, centered horizontally
        timg = assets_cache[brand]["tractor"]
        if timg:
            tr = fit_image(timg, tw, th)
            canvas.paste(tr, (rx - tr.width // 2, ry - tr.height), tr)

        # 2. Dot on road point
        dr = 5
        draw.ellipse([rx-dr, ry-dr, rx+dr, ry+dr],
                     fill=C_DARK, outline=C_WHITE, width=2)

        # 3. Arrow — horizontal at tractor mid-height
        ay = ry - th // 2
        if side == "right":
            ax1 = rx + tw // 2 + 6
            ax2 = ax1 + al
        else:
            ax1 = rx - tw // 2 - 6
            ax2 = ax1 - al
        draw_arrow(draw, ax1, ay, ax2, ay, color=C_ARROW, width=2, head=8)

        # 4. Label
        uw, uh = text_size(draw, unit_txt, fu)
        yw, yh = text_size(draw, yoy_txt,  fy)
        logo_img = assets_cache[brand]["logo"]
        logo_r   = None
        if logo_img:
            lr  = lh / logo_img.height
            lnw = min(int(logo_img.width * lr), lbw)
            logo_r = logo_img.resize((lnw, lh), Image.LANCZOS)

        lh_act  = lh if logo_r else 0
        bh_act  = 20 if not logo_r else 0
        block_h = lh_act + bh_act + uh + 4 + yh + 2
        lty     = max(10, min(ay - block_h // 2, H - block_h - 10))

        if side == "right":
            lx_base = min(ax2 + 6, W - lbw - 8)
            def px(ew, _b=lx_base): return _b
        else:
            rx_base = max(ax2 - 6, lbw + 8)
            def px(ew, _b=rx_base): return _b - ew

        cy = lty
        if logo_r:
            lx = max(4, px(logo_r.width))
            canvas.paste(logo_r, (lx, cy), logo_r)
            cy += lh + 2
        else:
            fb = get_font(16, bold=True)
            bw, bh = text_size(draw, brand, fb)
            draw.text((max(4, px(bw)), cy), brand, font=fb, fill=C_DARK)
            cy += bh + 4

        draw.text((max(4, px(uw)), cy), unit_txt, font=fu, fill=C_DARK)
        cy += uh + 3
        draw.text((max(4, px(yw)), cy), yoy_txt,  font=fy, fill=yoy_col)

    return canvas.convert("RGB")


# ══════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════

if "positions" not in st.session_state:
    st.session_state.positions = copy.deepcopy(DEFAULT_POSITIONS)

if "brands" not in st.session_state:
    st.session_state.brands = [
        {"brand":"Mahindra",    "units":19652, "yoy": 11.71},
        {"brand":"Swaraj",      "units":16007, "yoy": 11.51},
        {"brand":"Sonalika",    "units":10194, "yoy": 10.01},
        {"brand":"Kubota",      "units": 8926, "yoy": 16.11},
        {"brand":"TAFE",        "units": 8489, "yoy": 20.13},
        {"brand":"John Deere",  "units": 6460, "yoy":  9.31},
        {"brand":"Eicher",      "units": 4661, "yoy":  2.42},
        {"brand":"New Holland", "units": 3931, "yoy": 29.95},
        {"brand":"Others",      "units": 3760, "yoy":-17.85},
    ]

if "result_img" not in st.session_state:
    st.session_state.result_img = None


# ══════════════════════════════════════════════════════════════════
#  PAGE CONFIG & STYLES
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Tractor Sales Infographic",
    page_icon="🚜",
    layout="wide",
)

st.markdown("""
<style>
.main > div { padding-top: 1rem; }
h1 { color: #E8212A; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    background: #f0f0f0; border-radius: 8px 8px 0 0;
    padding: 8px 20px; font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: #E8212A !important; color: white !important;
}
.coord-box {
    background: #1a1a1a; color: #00ff88; font-family: monospace;
    padding: 12px 18px; border-radius: 8px; font-size: 15px; margin: 8px 0;
}
.info-box {
    background: #fff8e1; border-left: 4px solid #f9a825;
    padding: 10px 14px; border-radius: 4px; font-size: 13px; margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar info ──────────────────────────────────────────────────
st.sidebar.markdown("### ℹ️ Info")
st.sidebar.markdown(f"**Base:** `{BASE_DIR}`")
st.sidebar.markdown(f"**Platform:** `{platform.system()}`")
if FONT_BOLD_PATH:
    st.sidebar.success(f"Font: `{os.path.basename(FONT_BOLD_PATH)}`")
else:
    st.sidebar.warning("No TTF font found. Add Barlow .ttf files to `assets/fonts/`")

# ── Asset file check — shows exactly what is found per brand ──────
st.sidebar.markdown("### 🔍 Asset Check")
for brand in ALL_BRANDS:
    lp = brand_logo_path(brand)
    tp = brand_tractor_path(brand)
    l_icon = "🟢" if lp else "🔴"
    t_icon = "🟢" if tp else "🔴"
    l_name = os.path.basename(lp) if lp else "NOT FOUND"
    t_name = os.path.basename(tp) if tp else "NOT FOUND"
    st.sidebar.markdown(
        "**" + brand + "**  \n" +
        l_icon + " Logo: `" + l_name + "`  \n" +
        t_icon + " Tractor: `" + t_name + "`"
    )

# ── Asset folder checks ───────────────────────────────────────────
missing = []
for label, path in [
    ("assets/",          ASSETS_DIR),
    ("assets/logos/",    LOGOS_DIR),
    ("assets/tractors/", TRACTORS_DIR),
]:
    if not os.path.isdir(path):
        missing.append(f"- `{label}` → `{path}`")

if missing:
    st.error("❌ **Missing folders. Create these next to App.py:**\n\n" + "\n".join(missing))
    st.stop()

if not os.path.exists(asset("Background.jpg")):
    st.error(f"❌ `Background.jpg` not found in `{ASSETS_DIR}`")
    st.stop()

st.title("🚜 Tractor Sales Infographic Generator")

tab1, tab2 = st.tabs(["🎯 Position Finder", "🖼️ Generate Infographic"])


# ══════════════════════════════════════════════════════════════════
#  TAB 1 — POSITION FINDER
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 🎯 Road Position Finder")
    st.markdown("""
    <div class="info-box">
    <b>How to find exact positions:</b><br>
    1. Open <b>Background.jpg</b> from the <code>assets/</code> folder in <b>Paint</b> (Windows) or <b>Preview</b> (Mac) or <b>GIMP</b>.<br>
    2. Hover your mouse over the road — the app status bar shows the X, Y pixel coordinate.<br>
    3. Note the coordinates for each of the 9 tractor positions on the road.<br>
    4. Enter those X, Y values into the slots on the right and click <b>Save slot</b>.<br>
    5. Click <b>Refresh map</b> to see updated circles on the road image below.<br>
    6. Once happy, copy the <b>Positions JSON</b> for your records.
    </div>
    """, unsafe_allow_html=True)

    col_img, col_ctrl = st.columns([3, 2])

    with col_img:
        overlay = draw_positions_overlay(st.session_state.positions)

        DISPLAY_W = 620
        scale     = DISPLAY_W / overlay.width
        display_h = int(overlay.height * scale)
        small     = overlay.resize((DISPLAY_W, display_h), Image.LANCZOS)

        st.image(small,
                 caption=f"Canvas: 1080×1350 px  |  Displayed: {DISPLAY_W}×{display_h} px  |  Scale: {scale:.4f}×",
                 use_container_width=False)

        st.markdown("---")
        st.markdown("#### 🖱️ Coordinate Converter")
        st.caption(
            f"Image shown at **{scale:.4f}×** scale. "
            "Enter the coordinates from your image viewer to convert them to canvas coords."
        )

        cx1, cx2 = st.columns(2)
        with cx1:
            disp_x = st.number_input("Displayed X (px)", 0, DISPLAY_W, 0, step=1, key="disp_x")
        with cx2:
            disp_y = st.number_input("Displayed Y (px)", 0, display_h, 0, step=1, key="disp_y")

        real_x = int(round(disp_x / scale))
        real_y = int(round(disp_y / scale))

        st.markdown(f"""
        <div class="coord-box">
        🎯 &nbsp; Canvas X: <b>{real_x}</b> &nbsp;|&nbsp; Canvas Y: <b>{real_y}</b>
        &nbsp;&nbsp; ← use these values
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Quick-assign to a position slot:**")
        qa1, qa2, qa3 = st.columns(3)
        with qa1:
            target = st.selectbox("Slot", list(range(1, 10)),
                                  format_func=lambda x: f"Slot {x} (rank {x})")
        with qa2:
            new_side = st.selectbox("Label side", ["left", "right"], key="qa_side")
        with qa3:
            st.write(""); st.write("")
            if st.button("📌 Assign to slot", use_container_width=True):
                idx = target - 1
                st.session_state.positions[idx] = {"x": real_x, "y": real_y, "side": new_side}
                st.success(f"✅ Slot {target} updated → X:{real_x}, Y:{real_y}, side:{new_side}")
                st.rerun()

    with col_ctrl:
        st.markdown("#### 📍 All 9 Positions")
        st.caption("🔵 = left label side &nbsp;&nbsp; 🟢 = right label side")

        for i in range(9):
            pos = st.session_state.positions[i]
            icon = "🔵" if pos["side"] == "left" else "🟢"
            with st.expander(f"{icon} Slot {i+1} — x={pos['x']}, y={pos['y']}, {pos['side']}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    nx = st.number_input("X", 0, 1080, pos["x"], step=1, key=f"ex_{i}")
                    ny = st.number_input("Y", 0, 1350, pos["y"], step=1, key=f"ey_{i}")
                with ec2:
                    ns = st.radio("Label side", ["left", "right"],
                                  index=0 if pos["side"] == "left" else 1,
                                  key=f"es_{i}")
                if st.button("✅ Save slot", key=f"save_{i}", use_container_width=True):
                    st.session_state.positions[i] = {"x": nx, "y": ny, "side": ns}
                    st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Positions JSON")
        st.caption("Copy this into generate_infographic.py → ROAD_POSITIONS")
        st.code(json.dumps(st.session_state.positions, indent=2), language="json")

        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("🔄 Reset to defaults", use_container_width=True):
                st.session_state.positions = copy.deepcopy(DEFAULT_POSITIONS)
                st.rerun()
        with rc2:
            if st.button("🔍 Refresh map", use_container_width=True):
                st.rerun()


# ══════════════════════════════════════════════════════════════════
#  TAB 2 — GENERATOR
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🖼️ Configure & Generate")

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        report_month  = st.text_input("Report Month",  "March 2026")
    with mc2:
        compare_month = st.text_input("Compare Month", "March 2025")
    with mc3:
        total_yoy = st.number_input("Market YoY %", value=10.87, step=0.01, format="%.2f")

    st.markdown("---")
    st.markdown("### 📊 Brand Sales Data")
    st.caption("Brands auto-sort **highest → lowest** before rendering.")

    h1, h2, h3 = st.columns([2.5, 2, 2])
    h1.markdown("**Brand**")
    h2.markdown("**Units Sold**")
    h3.markdown("**YoY %**")

    brand_data = []
    for i, row in enumerate(st.session_state.brands):
        c1, c2, c3 = st.columns([2.5, 2, 2])
        with c1:
            brand = st.selectbox("Brand", ALL_BRANDS,
                                  index=ALL_BRANDS.index(row["brand"])
                                        if row["brand"] in ALL_BRANDS else 0,
                                  key=f"b_{i}", label_visibility="collapsed")
        with c2:
            units = st.number_input("Units", value=int(row["units"]),
                                     step=100, min_value=0,
                                     key=f"u_{i}", label_visibility="collapsed")
        with c3:
            yoy = st.number_input("YoY %", value=float(row["yoy"]),
                                   step=0.01, format="%.2f",
                                   key=f"y_{i}", label_visibility="collapsed")
        brand_data.append((brand, int(units), float(yoy)))
        st.session_state.brands[i] = {"brand": brand, "units": int(units), "yoy": float(yoy)}

    st.markdown("---")

    btn1, btn2 = st.columns(2)
    with btn1:
        gen_clicked = st.button("🔄 Generate Infographic", type="primary", use_container_width=True)
    with btn2:
        if st.session_state.result_img:
            buf = io.BytesIO()
            st.session_state.result_img.save(buf, format="PNG", dpi=(150, 150))
            fn = f"tractor_sales_{report_month.replace(' ', '_')}.png"
            st.download_button("📥 Download PNG", data=buf.getvalue(),
                               file_name=fn, mime="image/png",
                               use_container_width=True)
        else:
            st.button("📥 Download PNG", disabled=True, use_container_width=True)

    if gen_clicked:
        with st.spinner("Rendering..."):
            try:
                img = generate_infographic(
                    brand_data, report_month, compare_month,
                    total_yoy, st.session_state.positions
                )
                st.session_state.result_img = img
                out_path = os.path.join(
                    OUTPUT_DIR,
                    f"tractor_sales_{report_month.replace(' ', '_')}.png"
                )
                img.save(out_path, "PNG", dpi=(150, 150))
                st.success(f"✅ Saved to: `{out_path}`")
            except Exception as e:
                st.error(f"❌ {e}")
                st.exception(e)

    if st.session_state.result_img:
        st.markdown("### Preview")
        img  = st.session_state.result_img
        prev = img.resize((680, int(img.height * 680 / img.width)), Image.LANCZOS)
        st.image(prev, caption=f"Tractor Sales — {report_month}", use_container_width=False)
    else:
        st.info("👆 Click **Generate Infographic** to preview here.")