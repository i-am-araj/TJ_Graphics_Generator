"""
Tractor Sales Infographic Generator — Streamlit UI
=====================================================
Layout (all paths resolved relative to this file's location,
so this works unchanged on Windows, Linux, and Streamlit Cloud):
  App.py
  assets/Background.jpg, TJ_New_Logo.png, fonts/
  assets/logos/   ← <Brand>.png
  assets/tractors/← <Brand>.png
  positions.json  ← auto-saved
  output/

Run:  streamlit run App.py
"""

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont
import os, math, io, json, copy, base64, platform

# ══════════════════════════════════════════════════════════════════
#  PATHS
# ══════════════════════════════════════════════════════════════════
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR     = os.path.join(BASE_DIR, "assets")
LOGOS_DIR      = os.path.join(BASE_DIR, "assets", "logos")
TRACTORS_DIR   = os.path.join(BASE_DIR, "assets", "tractors")
OUTPUT_DIR     = os.path.join(BASE_DIR, "output")
POSITIONS_JSON = os.path.join(BASE_DIR, "positions.json")

for _d in (ASSETS_DIR, LOGOS_DIR, TRACTORS_DIR, OUTPUT_DIR):
    os.makedirs(_d, exist_ok=True)

def asset(fn):
    """Case-insensitive lookup inside ASSETS_DIR (Windows is case-insensitive,
    but Linux/Streamlit Cloud is not, so an exact-name file uploaded with
    different casing would otherwise fail to be found)."""
    p = os.path.join(ASSETS_DIR, fn)
    if os.path.exists(p):
        return p
    if os.path.isdir(ASSETS_DIR):
        for f in os.listdir(ASSETS_DIR):
            if f.lower() == fn.lower():
                return os.path.join(ASSETS_DIR, f)
    return p

# ══════════════════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════════════════
def find_font_weight(weight):
    """
    weight: one of "black", "bold", "semibold", "regular"
    Looks in assets/fonts/ for a Barlow file matching the weight,
    falls back to system fonts approximating that weight.
    """
    bundled = os.path.join(BASE_DIR, "assets", "fonts")
    weight_keywords = {
        "black":    ("black", "heavy", "extrabold"),
        "bold":     ("bold",),
        "semibold": ("semibold", "demibold", "medium"),
        "regular":  ("regular", "normal", "book"),
    }
    keys = weight_keywords.get(weight, ("regular",))

    if os.path.isdir(bundled):
        # exact weight match first
        for f in sorted(os.listdir(bundled)):
            if not f.lower().endswith(".ttf"):
                continue
            fl = f.lower()
            if any(k in fl for k in keys) and "italic" not in fl:
                return os.path.join(bundled, f)
        # fallback: bold→black, semibold→bold, regular→semibold, etc.
        fallback_chain = {
            "black":    ("bold", "heavy"),
            "bold":     ("black", "semibold"),
            "semibold": ("bold", "medium", "regular"),
            "regular":  ("semibold", "regular", "bold"),
        }
        for k in fallback_chain.get(weight, ()):
            for f in sorted(os.listdir(bundled)):
                if not f.lower().endswith(".ttf"):
                    continue
                fl = f.lower()
                if k in fl and "italic" not in fl:
                    return os.path.join(bundled, f)

    # System font fallback (Windows Arial family has no Black/SemiBold,
    # so Bold is reused for Black, Regular for SemiBold)
    win = os.environ.get("WINDIR", r"C:\Windows")
    sys_map = {
        "black":    [os.path.join(win, "Fonts", "arialbd.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
        "bold":     [os.path.join(win, "Fonts", "arialbd.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
        "semibold": [os.path.join(win, "Fonts", "arial.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
        "regular":  [os.path.join(win, "Fonts", "arial.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
    }
    for p in sys_map.get(weight, sys_map["regular"]):
        if os.path.exists(p):
            return p
    return None

FONT_BLACK_PATH     = find_font_weight("black")
FONT_BOLD_PATH      = find_font_weight("bold")
FONT_SEMIBOLD_PATH  = find_font_weight("semibold")
FONT_REGULAR_PATH   = find_font_weight("regular")

# ══════════════════════════════════════════════════════════════════
#  BRANDS
# ══════════════════════════════════════════════════════════════════
ALL_BRANDS = ["Mahindra","Swaraj","Sonalika","Kubota","TAFE",
              "John Deere","Eicher","New Holland","Others"]

def brand_logo_path(brand):
    if not os.path.isdir(LOGOS_DIR): return None
    for ext in (".png",".jpg",".jpeg",".webp"):
        for f in os.listdir(LOGOS_DIR):
            if f.lower() == (brand+ext).lower():
                return os.path.join(LOGOS_DIR, f)
    return None

def brand_tractor_path(brand):
    if not os.path.isdir(TRACTORS_DIR): return None
    for ext in (".png",".jpg",".jpeg",".webp"):
        for f in os.listdir(TRACTORS_DIR):
            if f.lower() == (brand+ext).lower():
                return os.path.join(TRACTORS_DIR, f)
    return None

# ══════════════════════════════════════════════════════════════════
#  DEFAULT POSITIONS
# ══════════════════════════════════════════════════════════════════
TRACTOR_MAX_W = [220,195,175,158,143,130,118,107,96]
LOGO_H        = [ 70, 64, 58, 52, 48, 44, 40, 37,34]
FONT_UNITS    = [ 36, 33, 30, 28, 26, 24, 23, 22,21]
FONT_YOY      = [ 22, 20, 19, 18, 17, 16, 16, 15,15]
ARROW_LEN     = [100, 88, 78, 70, 64, 58, 53, 48,44]
LABEL_W       = [260,235,215,198,183,170,158,148,138]

DEFAULT_POSITIONS = [
    {"x":200,"y":1300,"side":"top",   "angle":0,"flip":False},
    {"x":525,"y":1150,"side":"right", "angle":0,"flip":False},
    {"x":470,"y": 970,"side":"right", "angle":0,"flip":True },
    {"x":420,"y": 800,"side":"left",  "angle":0,"flip":False},
    {"x":630,"y": 700,"side":"right", "angle":-3,"flip":False},
    {"x":535,"y": 575,"side":"left",  "angle":0,"flip":True },
    {"x":650,"y": 470,"side":"top",   "angle":0,"flip":False},
    {"x":800,"y": 450,"side":"bottom",   "angle":0,"flip":False},
    {"x":980,"y": 390,"side":"top",   "angle":0,"flip":False},
]

def load_positions():
    if os.path.exists(POSITIONS_JSON):
        try:
            with open(POSITIONS_JSON) as f:
                data = json.load(f)
            if isinstance(data,list) and len(data)==9:
                for i,p in enumerate(data):
                    p.setdefault("angle",0)
                    p.setdefault("flip",False)
                    p.setdefault("max_w_override", TRACTOR_MAX_W[i])
                return data
        except Exception: pass
    return copy.deepcopy(DEFAULT_POSITIONS)

def save_positions(positions):
    with open(POSITIONS_JSON,"w") as f:
        json.dump(positions, f, indent=2)

# ══════════════════════════════════════════════════════════════════
#  COLOURS
# ══════════════════════════════════════════════════════════════════
# Red = #de3245  → RGB(222,50,69)
C_RED  =(222,50,69,255)
C_TITLE=C_RED;            C_DARK=(26,26,26,255); C_WHITE=(255,255,255,255)
C_UP=(34,165,71,255);     C_DOWN=C_RED;          C_ARROW=(26,26,26,255)

SCALE = 3

# ══════════════════════════════════════════════════════════════════
#  IMAGE HELPERS
# ══════════════════════════════════════════════════════════════════
def _load_img(path):
    if not path or not os.path.exists(path): return None
    return Image.open(path).convert("RGBA")

@st.cache_data
def load_root(fn):
    p = asset(fn)
    if not os.path.exists(p): return None
    return Image.open(p).convert("RGBA")

def scale_to_width(img, w):
    if img.width==w: return img
    return img.resize((w, max(1,int(img.height*w/img.width))), Image.LANCZOS)

def prepare_tractor(img, max_w, angle, flip):
    tr = scale_to_width(img, max_w)
    if flip:  tr = tr.transpose(Image.FLIP_LEFT_RIGHT)
    if angle: tr = tr.rotate(-angle, resample=Image.BICUBIC, expand=True)
    return tr

def get_font(size, bold=True, weight=None):
    """
    weight overrides bold: "black" | "bold" | "semibold" | "regular"
    bold=True/False kept for backward compatibility (maps to bold/regular).
    """
    if weight == "black":
        path = FONT_BLACK_PATH
    elif weight == "semibold":
        path = FONT_SEMIBOLD_PATH
    elif weight == "regular":
        path = FONT_REGULAR_PATH
    elif weight == "bold":
        path = FONT_BOLD_PATH
    else:
        path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH

    if path and os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def tsz(draw, text, font):
    bb = draw.textbbox((0,0),text,font=font)
    return bb[2]-bb[0], bb[3]-bb[1]

def fmt(n): return f"{int(n):,}"

def img_to_b64(img, f="PNG"):
    buf = io.BytesIO(); img.save(buf,format=f)
    return base64.b64encode(buf.getvalue()).decode()

def draw_dotted_arrow(draw,x1,y1,x2,y2,color,width=3,head=12,dash=14,gap=8,
                       dot_color=C_RED,dot_r=None):
    dx,dy=x2-x1,y2-y1; length=math.hypot(dx,dy)
    if length==0: return
    ux,uy=dx/length,dy/length
    d,seg_on=0.0,True
    while d<length:
        seg=dash if seg_on else gap; e=min(d+seg,length)
        if seg_on:
            draw.line([(int(x1+ux*d),int(y1+uy*d)),(int(x1+ux*e),int(y1+uy*e))],
                      fill=color,width=width)
        d+=seg; seg_on=not seg_on
    # Red dot at the logo end (x2,y2) instead of an arrowhead
    r=dot_r if dot_r is not None else max(width*1.8,head*0.45)
    draw.ellipse([x2-r,y2-r,x2+r,y2+r],fill=dot_color)

# ══════════════════════════════════════════════════════════════════
#  RENDER INFOGRAPHIC
# ══════════════════════════════════════════════════════════════════
def generate_infographic(data, report_month, compare_month, total_yoy, positions):
    S=SCALE
    bg=load_root("Background.jpg")
    if bg is None: raise FileNotFoundError("Background.jpg not found")
    W0,H0=bg.size; W,H=W0*S,H0*S
    canvas=bg.resize((W,H),Image.LANCZOS)
    draw=ImageDraw.Draw(canvas)
    ranked=sorted(data,key=lambda x:x[1],reverse=True)

    acache={}
    for brand,_,__ in ranked:
        if brand not in acache:
            acache[brand]={"logo":_load_img(brand_logo_path(brand)),
                           "tractor":_load_img(brand_tractor_path(brand))}
    tj=load_root("TJ_New_Logo.png")
    strip_png=load_root("Black_Strip.png")

    # Header — exact weights/sizes per spec
    #   Title          : Black,    69
    #   Subtitle bar   : Bold,     31
    #   "Total:" label : Bold,     46
    #   Total number   : Bold,     33
    f_ti = get_font(69*S, weight="black")
    f_su = get_font(31*S, weight="bold")
    f_tl = get_font(46*S, weight="bold")     # "Total:" label
    f_tn = get_font(33*S, weight="bold")     # Total number + YoY %
    tx,ty=44*S,32*S
    draw.text((tx,ty),      "Tractor Sales",font=f_ti,fill=C_TITLE)
    draw.text((tx,ty+73*S), "in India",     font=f_ti,fill=C_TITLE)
    sub=f"Retail Sales {report_month} as compare to {compare_month}"
    sub_bbox=draw.textbbox((0,0),sub,font=f_su)
    sw=sub_bbox[2]-sub_bbox[0]; sh=sub_bbox[3]-sub_bbox[1]
    by=ty+73*S+73*S+4*S
    strip_pad_h=18*S   # horizontal padding (left+right) around the text inside the strip
    strip_pad_v=14*S   # vertical padding (top+bottom) around the text inside the strip
    strip_x1,strip_y1=tx-4*S,by
    strip_x2,strip_y2=tx+sw+strip_pad_h,by+sh+strip_pad_v
    strip_w,strip_h=int(strip_x2-strip_x1),int(strip_y2-strip_y1)
    if strip_png and strip_w>0 and strip_h>0:
        strip_resized=strip_png.resize((strip_w,strip_h),Image.LANCZOS)
        canvas.paste(strip_resized,(int(strip_x1),int(strip_y1)),strip_resized)
    else:
        draw.rectangle([strip_x1,strip_y1,strip_x2,strip_y2],fill=C_DARK)
    # Center text within the strip (both axes), accounting for the glyph bbox's own offsets
    text_y=strip_y1+(strip_h-sh)//2-sub_bbox[1]
    text_x=strip_x1+(strip_w-sw)//2-sub_bbox[0]
    draw.text((text_x,text_y),sub,font=f_su,fill=C_WHITE)
    total_u=sum(u for _,u,__ in ranked)
    roy=by+sh+18*S
    draw.text((tx,roy),"Total:",font=f_tl,fill=C_DARK)
    lw2,_=tsz(draw,"Total: ",f_tl)
    nt=f" {fmt(total_u)}"
    # Total number aligned to baseline of the larger "Total:" label
    num_y_offset = (46-33)*S  # nudge down so baselines roughly align
    draw.text((tx+lw2,roy+num_y_offset),nt,font=f_tn,fill=C_DARK)
    nw,_=tsz(draw,nt,f_tn)
    yc=C_UP if total_yoy>=0 else C_DOWN
    draw.text((tx+lw2+nw,roy+num_y_offset),
              f" {'▲' if total_yoy>=0 else '▼'}{abs(total_yoy):.2f}% (YoY)",
              font=f_tn,fill=yc)
    if tj:
        tl_h=140*S; r2=tl_h/tj.height
        tl=tj.resize((int(tj.width*r2),tl_h),Image.LANCZOS)
        canvas.paste(tl,(W-tl.width-26*S,24*S),tl)

    # Tractors
    for rank,(brand,units,yoy) in enumerate(ranked):
        pos=positions[rank]
        rx=pos["x"]*S; ry=pos["y"]*S
        side=pos["side"]; angle=pos.get("angle",0); flip=pos.get("flip",False)
        tmax=(pos.get("max_w_override",TRACTOR_MAX_W[rank]))*S
        lh=LOGO_H[rank]*S
        fu=get_font(19*S, weight="bold"); fy=get_font(19*S, weight="bold")
        al=ARROW_LEN[rank]*S; lbw=LABEL_W[rank]*S
        up=yoy>=0; yc2=C_UP if up else C_DOWN
        yoy_txt=f"{'▲' if up else '▼'}{abs(yoy):.2f}%"; unit_txt=fmt(units)

        timg=acache[brand]["tractor"]
        tr=prepare_tractor(timg,tmax,angle,flip) if timg else None
        th=tr.height if tr else tmax; tw=tr.width if tr else tmax
        if tr: canvas.paste(tr,(rx-tw//2,ry-th),tr)

        lw_a=max(3,S); hd=12*S; da=14*S; ga=8*S
        dot_gap=10*S   # extra space between red dot and logo/label block
        logo_raw=acache[brand]["logo"]; logo_r=None
        if logo_raw:
            lr=lh/logo_raw.height
            logo_r=logo_raw.resize((min(int(logo_raw.width*lr),lbw),lh),Image.LANCZOS)

        uw,uh=tsz(draw,unit_txt,fu); yw,yh=tsz(draw,yoy_txt,fy)
        block_h=(lh if logo_r else 20*S)+uh+4*S+yh+2*S
        block_w=max(logo_r.width if logo_r else 0,uw,yw)

        if side=="top":
            ax1,ay1=rx,ry-th-4*S; ay2=ay1-al
            draw_dotted_arrow(draw,ax1,ay1,ax1,ay2,C_ARROW,lw_a,hd,da,ga)
            bx=max(4*S,min(ax1-block_w//2,W-block_w-4*S))
            cy=max(4*S,ay2-block_h-4*S-dot_gap)
            if logo_r:
                canvas.paste(logo_r,(bx+(block_w-logo_r.width)//2,cy),logo_r); cy+=lh+2*S
            else:
                fb=get_font(16*S); bw2,bh2=tsz(draw,brand,fb)
                draw.text((bx+(block_w-bw2)//2,cy),brand,font=fb,fill=C_DARK); cy+=bh2+4*S
            draw.text((bx+(block_w-uw)//2,cy),unit_txt,font=fu,fill=C_DARK); cy+=uh+3*S
            draw.text((bx+(block_w-yw)//2,cy),yoy_txt, font=fy,fill=yc2)
        elif side=="bottom":
            ax1,ay1=rx,ry+4*S; ay2=ay1+al
            draw_dotted_arrow(draw,ax1,ay1,ax1,ay2,C_ARROW,lw_a,hd,da,ga)
            bx=max(4*S,min(ax1-block_w//2,W-block_w-4*S))
            cy=min(H-block_h-4*S,ay2+4*S+dot_gap)
            if logo_r:
                canvas.paste(logo_r,(bx+(block_w-logo_r.width)//2,cy),logo_r); cy+=lh+2*S
            else:
                fb=get_font(16*S); bw2,bh2=tsz(draw,brand,fb)
                draw.text((bx+(block_w-bw2)//2,cy),brand,font=fb,fill=C_DARK); cy+=bh2+4*S
            draw.text((bx+(block_w-uw)//2,cy),unit_txt,font=fu,fill=C_DARK); cy+=uh+3*S
            draw.text((bx+(block_w-yw)//2,cy),yoy_txt, font=fy,fill=yc2)
        else:
            ay=ry-th//2
            if side=="right": ax1=rx+tw//2+6*S; ax2=ax1+al
            else:             ax1=rx-tw//2-6*S; ax2=ax1-al
            draw_dotted_arrow(draw,ax1,ay,ax2,ay,C_ARROW,lw_a,hd,da,ga)
            lty=max(10*S,min(ay-block_h//2,H-block_h-10*S))
            if side=="right":
                lx_base=min(ax2+6*S+dot_gap,W-lbw-8*S)
                base_x=lx_base
            else:
                rx_base=max(ax2-6*S-dot_gap,lbw+8*S)
                base_x=rx_base-block_w
            cy=lty
            if logo_r:
                canvas.paste(logo_r,(max(4*S,base_x+(block_w-logo_r.width)//2),cy),logo_r); cy+=lh+2*S
            else:
                fb=get_font(16*S); bw2,bh2=tsz(draw,brand,fb)
                draw.text((max(4*S,base_x+(block_w-bw2)//2),cy),brand,font=fb,fill=C_DARK); cy+=bh2+4*S
            draw.text((max(4*S,base_x+(block_w-uw)//2),cy),unit_txt,font=fu,fill=C_DARK); cy+=uh+3*S
            draw.text((max(4*S,base_x+(block_w-yw)//2),cy),yoy_txt, font=fy,fill=yc2)

    return canvas.convert("RGB")

# ══════════════════════════════════════════════════════════════════
#  INTERACTIVE OVERLAY EDITOR  (HTML5 canvas injected below preview)
# ══════════════════════════════════════════════════════════════════
def build_overlay_editor(positions, brands_ranked, preview_w, preview_h,
                          preview_img_b64):
    CANVAS_W, CANVAS_H = 1080, 1350
    RATIO = preview_w / CANVAS_W

    entities = []
    for rank,(brand,units,yoy) in enumerate(brands_ranked):
        pos           = positions[rank]
        max_w_logical = pos.get("max_w_override", TRACTOR_MAX_W[rank])
        flip          = pos.get("flip",  False)
        angle         = pos.get("angle", 0)
        side          = pos.get("side",  "left")
        disp_w        = max(20, int(max_w_logical * RATIO))

        tp = brand_tractor_path(brand)
        tr_src=""; tr_w=disp_w; tr_h=disp_w
        if tp and os.path.exists(tp):
            img = Image.open(tp).convert("RGBA")
            img = prepare_tractor(img, disp_w, angle, flip)
            tr_src=f"data:image/png;base64,{img_to_b64(img,'PNG')}"
            tr_w,tr_h=img.size

        lp = brand_logo_path(brand)
        lh_d = max(8, int(LOGO_H[rank]*RATIO))
        lo_src=""; lo_w=lh_d; lo_h=lh_d
        if lp and os.path.exists(lp):
            img=Image.open(lp).convert("RGBA")
            img=img.resize((max(1,int(img.width*lh_d/img.height)),lh_d),Image.LANCZOS)
            lo_src=f"data:image/png;base64,{img_to_b64(img,'PNG')}"
            lo_w,lo_h=img.size

        ax_d = pos["x"]*RATIO; ay_d = pos["y"]*RATIO

        lbl_w_d = max(50, int(LABEL_W[rank]*RATIO))
        lbl_h_d = max(20, int((FONT_UNITS[rank]+FONT_YOY[rank]+4)*RATIO*0.9))

        if side=="top":
            lbl_ox = -lbl_w_d//2; lbl_oy = -(tr_h + int(ARROW_LEN[rank]*RATIO) + lbl_h_d + 4)
            lo_ox  = lbl_ox;      lo_oy  = lbl_oy - lo_h - 4
        elif side=="bottom":
            lo_oy  = int(ARROW_LEN[rank]*RATIO) + 4
            lbl_oy = lo_oy + lo_h + 4
            lbl_ox = -lbl_w_d//2; lo_ox = lbl_ox
        elif side=="right":
            lbl_ox = int((tr_w//2 + int(ARROW_LEN[rank]*RATIO) + 6))
            lbl_oy = -tr_h//2 - lbl_h_d//2
            lo_ox  = lbl_ox; lo_oy = lbl_oy - lo_h - 2
        else:
            lbl_ox = -(tr_w//2 + int(ARROW_LEN[rank]*RATIO) + 6 + lbl_w_d)
            lbl_oy = -tr_h//2 - lbl_h_d//2
            lo_ox  = lbl_ox; lo_oy = lbl_oy - lo_h - 2

        up  = yoy>=0
        entities.append({
            "rank":rank,"brand":brand,
            "angle":angle,"flip":flip,"side":side,
            "max_w_logical":max_w_logical,
            "tr":{"src":tr_src,"x":ax_d-tr_w/2,"y":ay_d-tr_h,
                  "w":tr_w,"h":tr_h,"ax":ax_d,"ay":ay_d},
            "lo":{"src":lo_src,"x":ax_d+lo_ox,"y":ay_d+lo_oy,"w":lo_w,"h":lo_h},
            "lb":{"x":ax_d+lbl_ox,"y":ay_d+lbl_oy,"w":lbl_w_d,"h":lbl_h_d,
                  "unit":fmt(units),"yoy":f"{'▲' if up else '▼'}{abs(yoy):.2f}%",
                  "up":up},
        })

    ent_json      = json.dumps(entities)
    positions_json = json.dumps(positions)
    FONT_UNITS_JS  = json.dumps(FONT_UNITS)
    FONT_YOY_JS    = json.dumps(FONT_YOY)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#111;font-family:Arial,sans-serif;color:#eee;
     display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px;}}
#toolbar{{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;
          width:{preview_w}px;}}
#wrap{{position:relative;width:{preview_w}px;height:{preview_h}px;
       overflow:hidden;border:2px solid #333;cursor:default;user-select:none;}}
canvas{{position:absolute;top:0;left:0;}}
button{{padding:6px 14px;border:none;border-radius:5px;cursor:pointer;
        font-size:12px;font-weight:700;transition:opacity .15s;}}
button:hover{{opacity:.8;}} button:disabled{{opacity:.3;cursor:default;}}
#btnSave  {{background:#22a547;color:#fff;}}
#btnReset {{background:#555;   color:#fff;}}
#selInfo  {{background:#1e1e1e;color:#7df;border:1px solid #444;
            border-radius:5px;padding:5px 10px;font-size:11px;
            min-width:160px;text-align:center;flex:1;}}
#pp{{width:{preview_w}px;background:#1e1e1e;border:1px solid #444;
     border-radius:6px;padding:8px 12px;display:none;
     flex-wrap:wrap;gap:7px;align-items:center;font-size:11px;}}
.pg{{display:flex;align-items:center;gap:5px;background:#252525;
     border-radius:4px;padding:4px 8px;}}
.pg label{{color:#999;white-space:nowrap;}}
.pg input[type=range]{{width:75px;accent-color:#ffe000;}}
.pg input[type=number]{{width:42px;background:#333;border:1px solid #555;
  color:#eee;padding:2px 4px;border-radius:3px;text-align:center;}}
.pg select{{background:#333;border:1px solid #555;color:#eee;
  padding:2px 5px;border-radius:3px;}}
.ptitle{{color:#ffe000;font-weight:700;font-size:12px;width:100%;}}
.pnote {{color:#555;font-size:10px;}}
#hint{{font-size:10px;color:#555;text-align:center;width:{preview_w}px;line-height:1.5;}}
</style></head><body>

<div id="toolbar">
  <button id="btnSave" disabled>💾 Save layout</button>
  <button id="btnReset">↺ Reset</button>
  <div id="selInfo">🖱 Click any element to select</div>
</div>

<div id="wrap">
  <canvas id="bgc" width="{preview_w}" height="{preview_h}"></canvas>
  <canvas id="cvs" width="{preview_w}" height="{preview_h}"></canvas>
</div>
<div id="pp"></div>
<div id="hint">
  Drag to <b>move</b> &nbsp;|&nbsp; ↔ handle = <b>resize</b> &nbsp;|&nbsp;
  Panel below = <b>angle / flip / side</b> &nbsp;|&nbsp;
  Purple ⇄ badge = flipped
</div>

<script>
const PW={preview_w}, PH={preview_h};
const RATIO={RATIO};
const CANVAS_W={CANVAS_W}, CANVAS_H={CANVAS_H};
const FONT_UNITS={FONT_UNITS_JS};
const FONT_YOY  ={FONT_YOY_JS};

let origEntities = {ent_json};
let origPositions= {positions_json};

let ents = JSON.parse(JSON.stringify(origEntities));

const imgCache={{}};
function loadAllImages(cb){{
  const srcs=[...new Set(
    ents.flatMap(e=>[e.tr.src,e.lo.src]).filter(s=>s)
  )];
  if(!srcs.length){{cb();return;}}
  let n=srcs.length;
  srcs.forEach(src=>{{
    if(imgCache[src]){{if(--n===0)cb();return;}}
    const im=new Image();
    im.onload=im.onerror=()=>{{imgCache[src]=im;if(--n===0)cb();}};
    im.src=src;
  }});
}}

const bgc=document.getElementById("bgc");
const bctx=bgc.getContext("2d");
const cvs=document.getElementById("cvs");
const ctx=cvs.getContext("2d");

const bgImg=new Image();
bgImg.onload=()=>bctx.drawImage(bgImg,0,0,PW,PH);
bgImg.src="data:image/jpeg;base64,{preview_img_b64}";

let sel=null, dragMode=null, dragStart=null, dirty=false;
const HNDL=8;

function getObj(rank,part){{return ents[rank][part];}}
function getBB(obj){{return{{lx:obj.x,ty:obj.y,rx:obj.x+obj.w,by:obj.y+obj.h}};}}

function hitHandle(obj,mx,my){{
  const bb=getBB(obj);
  return Math.hypot(mx-bb.rx,my-(bb.ty+bb.by)/2)<=HNDL+3;
}}
function hitBody(obj,mx,my){{
  const bb=getBB(obj);
  return mx>=bb.lx&&mx<=bb.rx&&my>=bb.ty&&my<=bb.by;
}}

function render(){{
  ctx.clearRect(0,0,PW,PH);

  ents.forEach((e,ri)=>{{
    ["tr","lo","lb"].forEach(part=>{{
      const obj=e[part];
      const isSel=sel&&sel.rank===ri&&sel.part===part;
      const bb=getBB(obj);

      if(part==="tr"){{
        if(obj.src&&imgCache[obj.src]) ctx.drawImage(imgCache[obj.src],obj.x,obj.y,obj.w,obj.h);
        else{{ctx.fillStyle="#888";ctx.fillRect(obj.x,obj.y,obj.w,obj.h);}}
        if(e.flip){{
          ctx.save();
          ctx.fillStyle="rgba(156,39,176,.9)";ctx.strokeStyle="#fff";ctx.lineWidth=1;
          ctx.beginPath();ctx.arc(obj.x+9,obj.y+9,8,0,Math.PI*2);ctx.fill();ctx.stroke();
          ctx.fillStyle="#fff";ctx.font="bold 8px Arial";
          ctx.textAlign="center";ctx.textBaseline="middle";
          ctx.fillText("⇄",obj.x+9,obj.y+9);ctx.restore();
        }}
        ctx.save();
        ctx.fillStyle="rgba(0,0,0,.6)";ctx.strokeStyle="#fff";ctx.lineWidth=1.2;
        ctx.beginPath();ctx.arc(obj.x+obj.w/2,obj.y+9,9,0,Math.PI*2);ctx.fill();ctx.stroke();
        ctx.fillStyle="#fff";ctx.font="bold 8px Arial";
        ctx.textAlign="center";ctx.textBaseline="middle";
        ctx.fillText(String(ri+1),obj.x+obj.w/2,obj.y+9);ctx.restore();
      }}
      else if(part==="lo"){{
        if(obj.src&&imgCache[obj.src]) ctx.drawImage(imgCache[obj.src],obj.x,obj.y,obj.w,obj.h);
        else{{
          ctx.fillStyle="rgba(255,255,255,.15)";ctx.fillRect(obj.x,obj.y,obj.w,obj.h);
          ctx.fillStyle="#aaa";ctx.font="8px Arial";ctx.fillText("L",obj.x+2,obj.y+10);
        }}
      }}
      else{{
        const fs1=Math.max(6,Math.round(FONT_UNITS[ri]*RATIO*0.85));
        const fs2=Math.max(5,Math.round(FONT_YOY[ri]*RATIO*0.85));
        ctx.save();
        ctx.font=`bold ${{fs1}}px Arial`;ctx.fillStyle="rgba(26,26,26,0.9)";
        ctx.fillText(obj.unit,obj.x,obj.y+fs1);
        ctx.font=`bold ${{fs2}}px Arial`;
        ctx.fillStyle=obj.up?"rgb(34,165,71)":"rgb(232,33,42)";
        ctx.fillText(obj.yoy,obj.x,obj.y+fs1+3+fs2);
        ctx.restore();
      }}

      if(isSel){{
        ctx.save();
        ctx.strokeStyle="#ffe000";ctx.lineWidth=1.8;ctx.setLineDash([4,3]);
        ctx.strokeRect(bb.lx-2,bb.ty-2,obj.w+4,obj.h+4);ctx.restore();
        const hx=bb.rx+HNDL/2,hy=(bb.ty+bb.by)/2;
        ctx.save();
        ctx.fillStyle="#ffe000";ctx.strokeStyle="#222";ctx.lineWidth=1.2;
        ctx.beginPath();ctx.arc(hx,hy,HNDL,0,Math.PI*2);ctx.fill();ctx.stroke();
        ctx.fillStyle="#222";ctx.font="bold 9px Arial";
        ctx.textAlign="center";ctx.textBaseline="middle";
        ctx.fillText("↔",hx,hy);ctx.restore();
      }}
    }});
  }});
}}

function cxy(ev){{const r=cvs.getBoundingClientRect();return{{mx:ev.clientX-r.left,my:ev.clientY-r.top}};}}

cvs.addEventListener("mousedown",ev=>{{
  const{{mx,my}}=cxy(ev);
  if(sel){{
    const obj=ents[sel.rank][sel.part];
    if(hitHandle(obj,mx,my)){{
      dragMode="resize";
      dragStart={{mx,origW:obj.w,origH:obj.h,
                  origMaxW:ents[sel.rank].max_w_logical}};
      cvs.style.cursor="ew-resize";ev.preventDefault();return;
    }}
  }}
  const parts=["tr","lo","lb"];
  for(let ri=ents.length-1;ri>=0;ri--){{
    for(let pi=0;pi<parts.length;pi++){{
      const part=parts[pi];
      if(hitBody(ents[ri][part],mx,my)){{
        sel={{rank:ri,part}};dragMode="move";
        const obj=ents[ri][part];
        dragStart={{mx,my,origX:obj.x,origY:obj.y}};
        cvs.style.cursor="grabbing";
        updateInfo();showPP();render();
        ev.preventDefault();return;
      }}
    }}
  }}
  sel=null;dragMode=null;hidePP();
  document.getElementById("selInfo").textContent="🖱 Click any element to select";
  render();
}});

cvs.addEventListener("mousemove",ev=>{{
  const{{mx,my}}=cxy(ev);
  if(dragMode==="move"&&sel){{
    const obj=ents[sel.rank][sel.part];
    obj.x=dragStart.origX+(mx-dragStart.mx);
    obj.y=dragStart.origY+(my-dragStart.my);
    obj.x=Math.max(-obj.w/2,Math.min(PW-obj.w/2,obj.x));
    obj.y=Math.max(-obj.h/2,Math.min(PH-obj.h/2,obj.y));
    if(sel.part==="tr"){{ents[sel.rank].tr.ax=obj.x+obj.w/2;ents[sel.rank].tr.ay=obj.y+obj.h;}}
    markDirty();updateInfo();render();return;
  }}
  if(dragMode==="resize"&&sel){{
    const obj=ents[sel.rank][sel.part];
    const delta=mx-dragStart.mx;
    const newW=Math.max(10,dragStart.origW+delta);
    const ratio=newW/dragStart.origW;
    obj.w=newW;obj.h=Math.max(5,Math.round(dragStart.origH*ratio));
    if(sel.part==="tr"){{
      ents[sel.rank].max_w_logical=Math.round(dragStart.origMaxW*ratio);
      ents[sel.rank].tr.ax=obj.x+obj.w/2;ents[sel.rank].tr.ay=obj.y+obj.h;
    }}
    markDirty();updateInfo();render();return;
  }}
  if(sel){{
    const obj=ents[sel.rank][sel.part];
    if(hitHandle(obj,mx,my)) cvs.style.cursor="ew-resize";
    else if(hitBody(obj,mx,my)) cvs.style.cursor="grab";
    else cvs.style.cursor="default";
  }}
}});
window.addEventListener("mouseup",()=>{{dragMode=null;if(sel)cvs.style.cursor="grab";}});

function updateInfo(){{
  if(!sel)return;
  const e=ents[sel.rank];const obj=e[sel.part];
  const lx=Math.round(obj.x/RATIO),ly=Math.round(obj.y/RATIO);
  document.getElementById("selInfo").textContent=
    `#${{sel.rank+1}} ${{e.brand}} [${{sel.part}}] x=${{lx}} y=${{ly}} ${{obj.w}}×${{obj.h}}px`;
}}

const pp=document.getElementById("pp");
function showPP(){{
  if(!sel){{hidePP();return;}}
  const e=ents[sel.rank];
  pp.style.display="flex";
  const ang=e.angle||0;
  const sides=["left","right","top","bottom"];
  const opts=sides.map(s=>`<option ${{e.side===s?"selected":""}} value="${{s}}">${{s}}</option>`).join("");
  pp.innerHTML=`
    <div class="ptitle">#${{sel.rank+1}} ${{e.brand}} — ${{sel.part==="tr"?"tractor":sel.part==="lo"?"logo":"label"}}</div>
    ${{sel.part==="tr"?`
    <div class="pg">
      <label>↺ Angle</label>
      <input type="range" id="ppA" min="-45" max="45" value="${{ang}}" oninput="doAngle(this.value)">
      <input type="number" id="ppAN" min="-45" max="45" value="${{ang}}" oninput="doAngle(this.value)">°
    </div>
    <div class="pg">
      <label>⇄ Flip</label>
      <input type="checkbox" id="ppF" ${{e.flip?"checked":""}} onchange="doFlip(this.checked)"
             style="width:15px;height:15px;cursor:pointer;accent-color:#9c27b0;">
    </div>`:"" }}
    <div class="pg">
      <label>Arrow side</label>
      <select onchange="doSide(this.value)">${{opts}}</select>
    </div>
    <div class="pg pnote">Drag to move &nbsp;|&nbsp; ↔ handle to resize ${{sel.part==="tr"?"&nbsp;|&nbsp; Angle/flip → re-generate to see":""}}</div>
  `;
}}
function hidePP(){{pp.style.display="none";pp.innerHTML="";}}

function doAngle(v){{
  if(!sel||sel.part!=="tr")return;
  const val=Math.max(-45,Math.min(45,parseInt(v)||0));
  ents[sel.rank].angle=val;
  const a=document.getElementById("ppA"),an=document.getElementById("ppAN");
  if(a)a.value=val;if(an)an.value=val;
  markDirty();updateInfo();
}}
function doFlip(v){{
  if(!sel||sel.part!=="tr")return;
  ents[sel.rank].flip=v;
  markDirty();updateInfo();render();
}}
function doSide(v){{
  if(!sel)return;
  ents[sel.rank].side=v;
  markDirty();
}}

function markDirty(){{
  dirty=true;
  document.getElementById("btnSave").disabled=false;
}}

document.getElementById("btnSave").addEventListener("click",()=>{{
  const result=ents.map((e,i)=>{{
    const op=origPositions[i];
    return {{
      x:    Math.round(e.tr.ax/RATIO),
      y:    Math.round(e.tr.ay/RATIO),
      side: e.side||op.side,
      angle:e.angle||0,
      flip: e.flip||false,
      max_w_override:e.max_w_logical,
      logo_ox: Math.round((e.lo.x-e.tr.ax)/RATIO),
      logo_oy: Math.round((e.lo.y-e.tr.ay)/RATIO),
      label_ox: Math.round((e.lb.x-e.tr.ax)/RATIO),
      label_oy: Math.round((e.lb.y-e.tr.ay)/RATIO),
    }};
  }});
  window.parent.postMessage({{type:"tractor_save",payload:JSON.stringify(result)}},"*");
  document.getElementById("btnSave").disabled=true;dirty=false;
  document.getElementById("selInfo").textContent="✅ Saved — paste JSON below & click Load";
}});

document.getElementById("btnReset").addEventListener("click",()=>{{
  ents=JSON.parse(JSON.stringify(origEntities));
  sel=null;dirty=false;hidePP();
  document.getElementById("btnSave").disabled=true;
  document.getElementById("selInfo").textContent="↺ Reset to last saved positions";
  render();
}});

loadAllImages(()=>render());
</script></body></html>"""
    return html, preview_h

# ══════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════
if "positions"  not in st.session_state: st.session_state.positions  = load_positions()
if "brands"     not in st.session_state:
    st.session_state.brands = [
        {"brand":"Mahindra",   "units":19652,"yoy": 11.71},
        {"brand":"Swaraj",     "units":16007,"yoy": 11.51},
        {"brand":"Sonalika",   "units":10194,"yoy": 10.01},
        {"brand":"Kubota",     "units": 8926,"yoy": 16.11},
        {"brand":"TAFE",       "units": 8489,"yoy": 20.13},
        {"brand":"John Deere", "units": 6460,"yoy":  9.31},
        {"brand":"Eicher",     "units": 4661,"yoy":  2.42},
        {"brand":"New Holland","units": 3931,"yoy": 29.95},
        {"brand":"Others",     "units": 3760,"yoy":-17.85},
    ]
if "result_img"   not in st.session_state: st.session_state.result_img   = None
if "edit_mode"    not in st.session_state: st.session_state.edit_mode     = False
if "save_msg"     not in st.session_state: st.session_state.save_msg      = ""

# ══════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Tractor Sales Infographic", page_icon="🚜", layout="wide")
st.markdown("""
<style>
.main>div{padding-top:.6rem;}
h1{color:#E8212A;}
.save-ok{background:#e8f5e9;border-left:4px solid #22a547;
         padding:8px 12px;border-radius:4px;font-size:13px;margin:6px 0;}
.edit-on{background:#fff3e0;border-left:4px solid #f57c00;
         padding:8px 12px;border-radius:4px;font-size:13px;margin:6px 0;}
</style>""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown(f"**positions.json:** {'✅' if os.path.exists(POSITIONS_JSON) else '⚠️ not saved yet'}")
if FONT_BOLD_PATH: st.sidebar.success(f"Font: `{os.path.basename(FONT_BOLD_PATH)}`")
else: st.sidebar.warning("No TTF font found")
st.sidebar.markdown("### 🔍 Assets")
for brand in ALL_BRANDS:
    lp=brand_logo_path(brand); tp=brand_tractor_path(brand)
    st.sidebar.markdown(f"**{brand}** {'🟢' if lp else '🔴'}L {'🟢' if tp else '🔴'}T")

missing=[f"`{l}`" for l,p in [("assets/",ASSETS_DIR),("assets/logos/",LOGOS_DIR),
                                ("assets/tractors/",TRACTORS_DIR)] if not os.path.isdir(p)]
if missing: st.error("❌ Missing: "+", ".join(missing)); st.stop()
if not os.path.exists(asset("Background.jpg")): st.error("❌ Background.jpg not found"); st.stop()

st.title("🚜 Tractor Sales Infographic Generator")

# ── Single-tab layout ─────────────────────────────────────────────
st.markdown("### 📋 Report Settings")
mc1,mc2,mc3 = st.columns(3)
with mc1: report_month  = st.text_input("Report Month",  "March 2026")
with mc2: compare_month = st.text_input("Compare Month", "March 2025")
with mc3: total_yoy     = st.number_input("Market YoY %", value=10.87, step=0.01, format="%.2f")

st.markdown("---")
st.markdown("### 📊 Brand Sales Data")
st.caption("Auto-sorted highest → lowest.")
h1,h2,h3 = st.columns([2.5,2,2])
h1.markdown("**Brand**"); h2.markdown("**Units Sold**"); h3.markdown("**YoY %**")
brand_data=[]
for i,row in enumerate(st.session_state.brands):
    c1,c2,c3=st.columns([2.5,2,2])
    with c1:
        brand=st.selectbox("Brand",ALL_BRANDS,
            index=ALL_BRANDS.index(row["brand"]) if row["brand"] in ALL_BRANDS else 0,
            key=f"b_{i}",label_visibility="collapsed")
    with c2:
        units=st.number_input("Units",value=int(row["units"]),step=100,min_value=0,
            key=f"u_{i}",label_visibility="collapsed")
    with c3:
        yoy=st.number_input("YoY",value=float(row["yoy"]),step=0.01,format="%.2f",
            key=f"y_{i}",label_visibility="collapsed")
    brand_data.append((brand,int(units),float(yoy)))
    st.session_state.brands[i]={"brand":brand,"units":int(units),"yoy":float(yoy)}

st.markdown("---")

# ── Generate button (alone, full width) ───────────────────────────
gen_clicked = st.button("🔄 Generate Infographic", type="primary", use_container_width=True)

if gen_clicked:
    with st.spinner("Rendering…"):
        try:
            img = generate_infographic(brand_data, report_month, compare_month,
                                       total_yoy, st.session_state.positions)
            st.session_state.result_img = img
            st.session_state.edit_mode  = False
            out = os.path.join(OUTPUT_DIR,
                  f"tractor_sales_{report_month.replace(' ','_')}.png")
            img.save(out, "PNG", dpi=(300,300), compress_level=1)
            st.success(f"✅ Saved → `{out}`")
        except Exception as e:
            st.error(f"❌ {e}"); st.exception(e)

has_img = st.session_state.result_img is not None
a2, a3  = st.columns(2)

with a2:
    edit_label = "✏️ Edit Mode: ON  (click to turn OFF)" \
                 if st.session_state.edit_mode \
                 else "✏️ Edit Mode: OFF (click to turn ON)"
    if st.button(edit_label, disabled=not has_img, use_container_width=True):
        st.session_state.edit_mode = not st.session_state.edit_mode
        st.rerun()

with a3:
    if has_img:
        buf = io.BytesIO()
        st.session_state.result_img.save(buf, format="PNG", dpi=(300,300), compress_level=1)
        buf.seek(0)
        fn = f"tractor_sales_{report_month.replace(' ','_')}.png"
        st.download_button("📥 Download PNG", data=buf.getvalue(),
                           file_name=fn, mime="image/png", use_container_width=True)
    else:
        st.button("📥 Download PNG", disabled=True, use_container_width=True)

if st.session_state.save_msg:
    st.markdown(f'<div class="save-ok">{st.session_state.save_msg}</div>',
                unsafe_allow_html=True)
    st.session_state.save_msg=""

if st.session_state.result_img:
    img=st.session_state.result_img
    PREV_W=540
    PREV_H=int(img.height*PREV_W/img.width)
    prev=img.resize((PREV_W,PREV_H),Image.LANCZOS)

    if not st.session_state.edit_mode:
        st.markdown("### Preview")
        st.image(prev, caption=f"{report_month} | {img.width}×{img.height}px",
                 use_container_width=False)
    else:
        st.markdown(
            '<div class="edit-on">✏️ <b>Edit Mode ON</b> — '
            'click any tractor / logo / label to select, drag to move, '
            'use the ↔ handle to resize. Set angle/flip in the panel. '
            'Click <b>💾 Save layout</b> then <b>Load</b> to apply.</div>',
            unsafe_allow_html=True)

        ranked_ed=sorted(st.session_state.brands,key=lambda x:x["units"],reverse=True)
        brands_tuples=[(r["brand"],r["units"],r["yoy"]) for r in ranked_ed]

        prev_b64=img_to_b64(prev,"JPEG")

        html_code,ed_h=build_overlay_editor(
            st.session_state.positions, brands_tuples,
            PREV_W, PREV_H, prev_b64
        )
        components.html(html_code, height=ed_h+260, scrolling=False)

        components.html("""
<script>
window.addEventListener("message",function(ev){
  if(!ev.data||ev.data.type!=="tractor_save") return;
  navigator.clipboard.writeText(ev.data.payload).catch(()=>{});
  const tas=window.parent.document.querySelectorAll("textarea");
  tas.forEach(function(ta){
    if(ta.placeholder&&ta.placeholder.includes("Paste layout JSON")){
      const s=Object.getOwnPropertyDescriptor(
        window.parent.HTMLTextAreaElement.prototype,'value').set;
      s.call(ta,ev.data.payload);
      ta.dispatchEvent(new Event('input',{bubbles:true}));
    }
  });
});
</script>""", height=0)

        st.markdown("---")
        st.markdown("#### Apply saved changes")
        st.caption("After clicking **💾 Save layout** above, JSON is auto-copied to clipboard. Paste below and click **Load**.")

        cp,cb=st.columns([5,1])
        with cp:
            paste_json=st.text_area("Layout JSON","",height=100,
                placeholder="Paste layout JSON here (auto-filled after Save)",
                label_visibility="collapsed",key="paste_json_ta")
        with cb:
            st.write(""); st.write("")
            if st.button("📥 Load",use_container_width=True,type="primary"):
                if paste_json.strip():
                    try:
                        new_pos=json.loads(paste_json.strip())
                        if isinstance(new_pos,list) and len(new_pos)==9:
                            for i,p in enumerate(new_pos):
                                old=st.session_state.positions[i]
                                st.session_state.positions[i]={
                                    "x":    int(p.get("x",   old["x"])),
                                    "y":    int(p.get("y",   old["y"])),
                                    "side": p.get("side",    old["side"]),
                                    "angle":int(p.get("angle",old.get("angle",0))),
                                    "flip": bool(p.get("flip",old.get("flip",False))),
                                    "max_w_override":int(p.get("max_w_override",
                                                   old.get("max_w_override",TRACTOR_MAX_W[i]))),
                                    "logo_ox":  int(p.get("logo_ox",  old.get("logo_ox",0))),
                                    "logo_oy":  int(p.get("logo_oy",  old.get("logo_oy",0))),
                                    "label_ox": int(p.get("label_ox", old.get("label_ox",0))),
                                    "label_oy": int(p.get("label_oy", old.get("label_oy",0))),
                                }
                            save_positions(st.session_state.positions)
                            st.session_state.save_msg="✅ Layout saved to positions.json — click Generate to re-render."
                            st.session_state.edit_mode=False
                            st.rerun()
                        else:
                            st.error("❌ Expected 9 items.")
                    except json.JSONDecodeError as e:
                        st.error(f"❌ {e}")
else:
    st.info("👆 Click **Generate Infographic** to create the preview.")
    #Changed