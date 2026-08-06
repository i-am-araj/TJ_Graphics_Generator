"""
Tractor Sales Infographic Generator
====================================
Generates a 1080x1350 PNG infographic from sales data.

Usage:
    python3 generate_infographic.py

Configuration:
    Edit the DATA and CONFIG sections below to update monthly figures.
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os, math

# ═══════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════
UPLOADS   = '/mnt/user-data/uploads'
OUTPUT    = '/mnt/user-data/outputs/tractor_sales_infographic.png'

# Point these at your actual Barlow .ttf files for exact weight matching.
# Falls back to Bold/Regular automatically if Black/SemiBold files are
# missing or left pointing at the same file.
FONT_BLACK    = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'      # ← replace with Barlow-Black.ttf
FONT_BOLD     = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FONT_SEMIBOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'   # ← replace with Barlow-SemiBold.ttf
FONT_REGULAR  = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'

# ═══════════════════════════════════════════════════════════════
#  ★  EDIT THIS SECTION EACH MONTH  ★
# ═══════════════════════════════════════════════════════════════
REPORT_MONTH  = "March 2026"
COMPARE_MONTH = "March 2025"
TOTAL_YOY     = 10.87          # overall market YoY %

DATA = [
    # brand_key,       units,   yoy %
    ("Mahindra",       19652,   11.71),
    ("Swaraj",         16007,   11.51),
    ("Sonalika",       10194,   10.01),
    ("Kubota",          8926,   16.11),
    ("TAFE",            8489,   20.13),
    ("John Deere",      6460,    9.31),
    ("Eicher",          4661,    2.42),
    ("New Holland",     3931,   29.95),
    ("Others",          3760,  -17.85),
]

# ═══════════════════════════════════════════════════════════════
#  BRAND ASSET MAP  (logo file, tractor file)
# ═══════════════════════════════════════════════════════════════
BRAND_ASSETS = {
    "Mahindra":    ("mahindra-1673872647.png",  "mahindra.png"),
    "Swaraj":      ("swaraj-1608095532.webp",   "swaraj.png"),
    "Sonalika":    ("sonalika_New_Logo_HD.png",  "others.png"),
    "Kubota":      ("escorts_kubota_logo.png",   "esctorts_kubota.png"),
    "TAFE":        ("tafe.png",                         "tafe.png"),
    "John Deere":  ("John_Deere_logo_svg.png",   "john_deere.png"),
    "Eicher":      ("eicher-logo.png",            "eicher.png"),
    "New Holland": ("new_holland_logo.png",       "new_holland.png"),
    "Others":      (None,                         "others.png"),
}

# ═══════════════════════════════════════════════════════════════
#  COLOURS
# ═══════════════════════════════════════════════════════════════
C_TITLE      = (232,  33,  42, 255)   # red
C_DARK       = ( 26,  26,  26, 255)   # near-black
C_WHITE      = (255, 255, 255, 255)
C_UP         = ( 34, 165,  71, 255)   # green
C_DOWN       = (232,  33,  42, 255)   # red
C_ARROW      = ( 26,  26,  26, 255)   # connector line/dot
C_TRANSPARENT= (  0,   0,   0,   0)

# ═══════════════════════════════════════════════════════════════
#  9 FIXED ROAD POSITIONS  (verified on actual background image)
#  x, y  = road centerline point (tractor base sits here)
#  side  = 'left' or 'right' (which side labels go)
# ═══════════════════════════════════════════════════════════════
ROAD_POSITIONS  = [
    {"x": 200, "y": 1280, "side": "left"},   # rank 1
    {"x": 500, "y": 1120, "side": "right"},  # rank 2
    {"x": 485, "y":  920, "side": "left"},   # rank 3
    {"x": 400, "y":  770, "side": "left"},   # rank 4
    {"x": 585, "y":  700, "side": "right"},  # rank 5
    {"x": 515, "y":  540, "side": "right"},  # rank 6
    {"x": 650, "y":  470, "side": "left"},   # rank 7
    {"x": 800, "y":  420, "side": "left"},  # rank 8
    {"x": 980, "y":  390, "side": "left"},  # rank 9
]

# Tractor sizes per rank (px), logo heights, font sizes
TRACTOR_W  = [200, 178, 160, 145, 132, 120, 108,  97, 86]
TRACTOR_H  = [120, 107,  96,  87,  79,  72,  65,  58, 52]
LOGO_H     = [ 36,  32,  29,  27,  25,  23,  21,  20, 18]
FONT_UNITS = [ 33,  30,  28,  26,  24,  22,  21,  20, 19]
FONT_YOY   = [ 19,  18,  17,  16,  16,  15,  15,  14, 14]
ARROW_LEN  = [ 90,  80,  72,  66,  60,  55,  50,  46, 42]
LABEL_W    = [230, 210, 192, 178, 165, 155, 146, 138, 130]


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def remove_black_bg(img: Image.Image, threshold: int = 35) -> Image.Image:
    """Convert black/near-black pixels to transparent."""
    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    brightness = r + g + b
    # Hard transparent zone
    hard = brightness < threshold
    # Soft edge zone
    soft = (brightness >= threshold) & (brightness < threshold + 80)
    new_a = arr[:,:,3].copy()
    new_a[hard] = 0
    new_a[soft] = ((brightness[soft] - threshold) / 80 * 255).clip(0, 255)
    arr[:,:,3] = new_a
    return Image.fromarray(arr.clip(0,255).astype(np.uint8), "RGBA")


def load_asset(filename: str, remove_bg: bool = True,
               max_w: int = 600) -> Image.Image | None:
    """Load an image from uploads, optionally remove black bg, resize."""
    if filename is None:
        return None
    path = os.path.join(UPLOADS, filename)
    if not os.path.exists(path):
        print(f"  [WARN] missing: {filename}")
        return None
    img = Image.open(path).convert("RGBA")
    if remove_bg:
        img = remove_black_bg(img)
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    return img


def fit_image(img: Image.Image, w: int, h: int) -> Image.Image:
    """Resize image to fit within w×h keeping aspect ratio."""
    img_ratio = img.width / img.height
    box_ratio  = w / h
    if img_ratio > box_ratio:
        new_w, new_h = w, int(w / img_ratio)
    else:
        new_w, new_h = int(h * img_ratio), h
    return img.resize((max(1,new_w), max(1,new_h)), Image.LANCZOS)


def fmt_number(n: int) -> str:
    """Format number in Indian numbering style."""
    return f"{n:,}"


def draw_arrow(draw: ImageDraw.Draw, x1, y1, x2, y2,
               color=(26,26,26,255), width=2, head=8):
    """Draw a line with arrowhead at (x2,y2)."""
    draw.line([(x1,y1),(x2,y2)], fill=color, width=width)
    # Arrowhead
    angle = math.atan2(y2-y1, x2-x1)
    spread = math.pi / 6
    for sign in (+1, -1):
        ex = int(x2 - head * math.cos(angle - sign * spread))
        ey = int(y2 - head * math.sin(angle - sign * spread))
        draw.line([(x2,y2),(ex,ey)], fill=color, width=width)


def text_size(draw: ImageDraw.Draw, text: str,
              font: ImageFont.FreeTypeFont) -> tuple[int,int]:
    bb = draw.textbbox((0,0), text, font=font)
    return bb[2]-bb[0], bb[3]-bb[1]


def draw_trend_triangle(draw: ImageDraw.Draw, x: int, y: int,
                         size: int, up: bool,
                         color=(34,165,71,255),
                         height_ratio: float = 0.8) -> int:
    """
    Draw a solid filled triangle (▲ or ▼) at (x, y) = top-left of its
    bounding box. Width == size; height == size * height_ratio, so the
    triangle's vertical height is a bit LESS than its horizontal width
    (flatter than an equilateral triangle).

    This replaces the Unicode ▲/▼ glyphs, which render as a missing-
    glyph box ("tofu"/question-mark) on fonts (like Liberation Sans)
    that don't include those symbols.

    Returns the pixel width consumed (== size), so callers can advance
    the x-cursor exactly like they would after drawing a character.
    """
    w = size
    h = size * height_ratio
    if up:
        # pointy top, flat bottom
        pts = [
            (x + w / 2, y),            # top point
            (x,         y + h),        # bottom-left
            (x + w,     y + h),        # bottom-right
        ]
    else:
        # flat top, pointy bottom
        pts = [
            (x,         y),            # top-left
            (x + w,     y),            # top-right
            (x + w / 2, y + h),        # bottom point
        ]
    draw.polygon(pts, fill=color)
    return size


# ═══════════════════════════════════════════════════════════════
#  FONT LOADER
# ═══════════════════════════════════════════════════════════════
def get_font(size: int, bold: bool = True,
             weight: str | None = None) -> ImageFont.FreeTypeFont:
    """
    weight overrides bold: "black" | "bold" | "semibold" | "regular"
    bold=True/False kept for backward compatibility (maps to bold/regular).
    """
    paths = {
        "black":    FONT_BLACK,
        "bold":     FONT_BOLD,
        "semibold": FONT_SEMIBOLD,
        "regular":  FONT_REGULAR,
    }
    if weight is None:
        weight = "bold" if bold else "regular"
    path = paths.get(weight, FONT_BOLD)
    return ImageFont.truetype(path, size)


# ═══════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════
def generate(data=DATA, report_month=REPORT_MONTH,
             compare_month=COMPARE_MONTH, total_yoy=TOTAL_YOY,
             output=OUTPUT):

    print("Loading assets...")

    # Background
    canvas = Image.open(os.path.join(UPLOADS, "Background.jpg")).convert("RGBA")
    W, H = canvas.size   # 1080 × 1350
    draw  = ImageDraw.Draw(canvas)

    # Sort data: highest → lowest units
    ranked = sorted(data, key=lambda x: x[1], reverse=True)

    # Pre-load all brand assets
    assets = {}
    for brand, logo_f, tractor_f in [
        (b, *BRAND_ASSETS[b]) for b,_,_ in ranked
    ]:
        if brand not in assets:
            assets[brand] = {
                "logo":    load_asset(logo_f,    remove_bg=True),
                "tractor": load_asset(tractor_f, remove_bg=True),
            }

    # TJ Logo
    tj_logo = load_asset("TJ_New_Logo.png", remove_bg=True, max_w=300)

    print("Drawing infographic...")

    # ── HEADER ─────────────────────────────────────────────────
    # Title: "Tractor Sales in India"        → Barlow Black,    69
    # Subtitle: "Retail Sales ... 2025"        → Barlow SemiBold, 31
    # "Total" label                            → Barlow Bold,     46
    # Numbers (total figure + its YoY %)       → Barlow Bold,     33
    f_title = get_font(69, weight="black")
    f_sub   = get_font(31, weight="semibold")
    f_total_lbl = get_font(46, weight="bold")
    f_total_num = get_font(33, weight="bold")
    f_total_yoy = get_font(33, weight="bold")

    title_x, title_y = 44, 32
    draw.text((title_x, title_y),     "Tractor Sales", font=f_title, fill=C_TITLE)
    draw.text((title_x, title_y+72),  "in India",      font=f_title, fill=C_TITLE)

    # Subtitle bar
    sub_text = f"Retail Sales {report_month} as compare to {compare_month}"
    sub_w, sub_h = text_size(draw, sub_text, f_sub)
    bar_y = title_y + 72 + 72 + 4
    draw.rectangle([title_x-4, bar_y, title_x + sub_w + 12, bar_y + sub_h + 8],
                   fill=C_DARK)
    draw.text((title_x + 2, bar_y + 4), sub_text, font=f_sub, fill=C_WHITE)

    # Total row
    total_units = sum(u for _,u,_ in ranked)
    total_y = bar_y + sub_h + 18
    # "Total: "
    draw.text((title_x, total_y), "Total:", font=f_total_lbl, fill=C_DARK)
    tot_lbl_w, _ = text_size(draw, "Total: ", f_total_lbl)
    # number
    num_text = f" {fmt_number(total_units)}"
    draw.text((title_x + tot_lbl_w, total_y), num_text, font=f_total_num, fill=C_DARK)
    num_w, _ = text_size(draw, num_text, f_total_num)
    # YoY — triangle glyph drawn manually, then the "10.87% (YoY)" text
    yoy_col   = C_UP if total_yoy >= 0 else C_DOWN
    yoy_up    = total_yoy >= 0
    tri_size  = f_total_yoy.size  # roughly matches cap-height of the font
    tri_x     = title_x + tot_lbl_w + num_w + 6
    # vertically centre the triangle against the text's ascent
    tri_y     = total_y + (f_total_yoy.size - tri_size) // 2 + 4
    draw_trend_triangle(draw, tri_x, tri_y, tri_size, yoy_up, color=yoy_col)
    yoy_rest_text = f" {abs(total_yoy):.2f}% (YoY)"
    draw.text((tri_x + tri_size, total_y),
              yoy_rest_text, font=f_total_yoy, fill=yoy_col)

    # ── TJ LOGO (top-right) ─────────────────────────────────
    if tj_logo:
        tl_h = 100
        ratio = tl_h / tj_logo.height
        tl_w  = int(tj_logo.width * ratio)
        tl    = tj_logo.resize((tl_w, tl_h), Image.LANCZOS)
        canvas.paste(tl, (W - tl_w - 26, 24), tl)

    # ── TRACTORS + LABELS + ARROWS ──────────────────────────
    for rank, (brand, units, yoy) in enumerate(ranked):
        pos  = ROAD_POSITIONS[rank]
        rx, ry = pos["x"], pos["y"]
        side = pos["side"]

        tw   = TRACTOR_W[rank]
        th   = TRACTOR_H[rank]
        lh   = LOGO_H[rank]
        f_u  = get_font(FONT_UNITS[rank], bold=True)
        # Percentage Numbers (per-brand YoY %) → Barlow Bold, 19, fixed (not rank-scaled)
        f_y  = get_font(19, weight="bold")
        alen = ARROW_LEN[rank]
        lw   = LABEL_W[rank]

        yoy_col  = C_UP   if yoy >= 0 else C_DOWN
        yoy_up   = yoy >= 0
        yoy_rest_text = f"{abs(yoy):.2f}%"
        unit_text = fmt_number(units)

        # ── 1. Place tractor: base centered on road point ──
        tractor_img = assets[brand]["tractor"]
        if tractor_img:
            t_resized = fit_image(tractor_img, tw, th)
            # Center X on road point; base of tractor at road point
            tx = rx - t_resized.width  // 2
            ty = ry - t_resized.height      # base at road point
            canvas.paste(t_resized, (tx, ty), t_resized)

        # ── 2. Dot on road point ──
        dot_r = 5
        draw.ellipse(
            [rx-dot_r, ry-dot_r, rx+dot_r, ry+dot_r],
            fill=C_DARK, outline=C_WHITE, width=2
        )

        # ── 3. Arrow: horizontal from tractor mid to label ──
        arrow_y  = ry - th // 2          # vertical midpoint of tractor
        if side == "right":
            ax1 = rx + tw // 2 + 6      # start: right edge of tractor
            ax2 = ax1 + alen            # end:   label start
        else:
            ax1 = rx - tw // 2 - 6     # start: left edge of tractor
            ax2 = ax1 - alen            # end:   label start

        draw_arrow(draw, ax1, arrow_y, ax2, arrow_y,
                   color=C_ARROW, width=2, head=8)

        # ── 4. Label block ──
        logo_img  = assets[brand]["logo"]
        u_w, u_h  = text_size(draw, unit_text, f_u)
        # width of YoY row = triangle + gap + text
        tri_size_r = f_y.size
        y_text_w, y_h = text_size(draw, yoy_rest_text, f_y)
        y_w = tri_size_r + 2 + y_text_w

        # Logo resized to lh height
        logo_resized = None
        if logo_img:
            logo_ratio   = lh / logo_img.height
            logo_new_w   = min(int(logo_img.width * logo_ratio), lw)
            logo_resized = logo_img.resize(
                (logo_new_w, lh), Image.LANCZOS
            )

        # Stack heights: logo/brand + units + yoy
        logo_h_actual = lh if logo_resized else 0
        brand_h       = 0 if logo_resized else (get_font(16,True).size + 4)
        block_h       = logo_h_actual + brand_h + u_h + 4 + y_h + 2
        label_top_y   = arrow_y - block_h // 2

        # Clamp label_top_y so it stays within canvas
        label_top_y = max(10, min(label_top_y, H - block_h - 10))

        if side == "right":
            label_left = ax2 + 6
            # Clamp so label doesn't go off right edge
            label_left = min(label_left, W - lw - 8)
            def place_x(elem_w, _side="right"):
                return label_left
        else:
            label_right = ax2 - 6
            # Clamp so label doesn't go off left edge
            label_right = max(lw + 8, label_right)
            def place_x(elem_w, _side="left"):
                return label_right - elem_w

        cy = label_top_y

        # Logo or text brand name
        if logo_resized:
            lx = place_x(logo_resized.width)
            lx = max(4, lx)
            canvas.paste(logo_resized, (lx, cy), logo_resized)
            cy += lh + 2
        else:
            f_brand = get_font(16, bold=True)
            b_w, b_h = text_size(draw, brand, f_brand)
            bx = max(4, place_x(b_w))
            draw.text((bx, cy), brand, font=f_brand, fill=C_DARK)
            cy += b_h + 4

        # Units
        ux = max(4, place_x(u_w))
        draw.text((ux, cy), unit_text, font=f_u, fill=C_DARK)
        cy += u_h + 3

        # YoY — draw triangle glyph, then the percentage text right after it
        yx = max(4, place_x(y_w))
        draw_trend_triangle(draw, yx, cy + 2, tri_size_r, yoy_up, color=yoy_col)
        draw.text((yx + tri_size_r + 2, cy), yoy_rest_text, font=f_y, fill=yoy_col)

    # ── SAVE ────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output), exist_ok=True)
    final = canvas.convert("RGB")
    final.save(output, "PNG", dpi=(150,150))
    print(f"\n✅ Saved → {output}")
    print(f"   Size: {os.path.getsize(output):,} bytes")
    return output


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    generate()