"""
Ather EV Market Intelligence - real-time Streamlit dashboard
============================================================
Run:   pip install -r requirements.txt
       streamlit run ather_dashboard.py

Folder layout:
    ather_dashboard.py
    ather_ev_market_intelligence_100k_synthetic.csv
    requirements.txt
    assets/            <- OPTIONAL: drop your own photos here (see IMAGES below)

REAL-TIME MODES (sidebar -> "Live data"):
    1. CSV file (auto-sync)  - the dashboard re-reads the CSV whenever the file changes
                               (any script / ETL job / API puller can keep appending rows).
    2. Live simulator        - generates new sales records every few seconds so you can
                               see the whole dashboard update live (great for demos).
    3. Remote URL / API      - point it at a CSV or JSON URL; it is re-fetched on every refresh.

IMAGES: built-in vector artwork (scooters, skyline, logo) works offline. To use real
photos, put files named hero.jpg (city/skyline banner), scooter.png (transparent scooter
cut-out) and logo.png inside an  assets/  folder next to this script.
"""
import base64
import io
import mimetypes
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================ CONFIG ============================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ather_ev_market_intelligence_100k_synthetic.csv"
ASSETS = BASE_DIR / "assets"

# EV Sales Dashboard Theme
EV_THEME = {
    "background": "#0B1220",
    "card": "#111C2E",
    "primary": "#00D9FF",       # Electric Cyan
    "secondary": "#39FF88",     # EV Green
    "highlight": "#B7FF00",     # Lime
    "positive": "#22C55E",
    "warning": "#F59E0B",
    "negative": "#EF4444",
    "text": "#F8FAFC",
    "muted_text": "#94A3B8",
    "grid": "#263449"
}

# Chart colors
EV_COLORS = ["#00D9FF", "#39FF88", "#B7FF00", "#6366F1", "#F59E0B", "#EF4444"]

# Legacy variables mapped to new theme
TEAL, CYAN, BLUE, PURPLE, YELLOW, ORANGE, GREEN = (
    EV_THEME["primary"], EV_THEME["primary"], "#6366F1", "#8B5CF6",
    EV_THEME["highlight"], EV_THEME["warning"], EV_THEME["secondary"])
PALETTE = EV_COLORS
CARD_BG, PAGE_BG, BORDER = EV_THEME["card"], EV_THEME["background"], EV_THEME["grid"]

# Sustainability assumptions (rough estimates - edit to taste)
ICE_KG_PER_KM = 0.051      # petrol scooter ~45 km/l x 2.3 kg CO2/l
GRID_KG_PER_KWH = 0.71     # approx. Indian grid emission factor
ANNUAL_KM = 8000           # assumed km driven per scooter per year
ICE_KM_PER_LITRE = 45
KG_CO2_PER_TREE_YEAR = 21

CITY_COORDS = {
    "Ahmedabad": (23.03, 72.58), "Surat": (21.17, 72.83), "Vadodara": (22.31, 73.18),
    "Bengaluru": (12.97, 77.59), "Mysuru": (12.30, 76.64), "Delhi": (28.61, 77.21),
    "Kochi": (9.93, 76.27), "Indore": (22.72, 75.86), "Mumbai": (19.08, 72.88),
    "Nagpur": (21.15, 79.09), "Pune": (18.52, 73.86), "Jaipur": (26.91, 75.79),
    "Chennai": (13.08, 80.27), "Coimbatore": (11.02, 76.96), "Hyderabad": (17.39, 78.49),
    "Lucknow": (26.85, 80.95), "Kolkata": (22.57, 88.36), "Chandigarh": (30.73, 76.78),
}
MODEL_COLORS = {
    "Ather 450X": (EV_THEME["primary"], "#FFFFFF"),
    "Ather 450S": (EV_THEME["secondary"], "#FFFFFF"),
    "Ather 450 Apex": ("#8B5CF6", EV_THEME["highlight"]),
    "Ather Rizta S": ("#6366F1", "#FFFFFF"),
    "Ather Rizta Z": (EV_THEME["highlight"], EV_THEME["card"]),
}
SRC_CSV, SRC_SIM, SRC_URL = "CSV file (auto-sync)", "Live simulator", "Remote URL / API"
PAGES = ["Overview", "Models", "Cities", "Charging", "Trends", "Customer Insights", "Sustainability"]
PAGE_ICONS = {"Overview": "🏠", "Models": "🛵", "Cities": "📍", "Charging": "🔌", "Trends": "📈",
              "Customer Insights": "👤", "Sustainability": "🌿"}
DERIVED = ["SalesDate", "Year", "Month", "Revenue", "Battery", "PriceBand", "kWh_per_km", "CO2_saved_kg_yr"]

st.set_page_config(page_title="Ather EV Market Intelligence", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")


# ============================ HELPERS ============================
def html(s: str) -> str:
    """Collapse indentation so Markdown never treats HTML as a code block."""
    return " ".join(line.strip() for line in s.strip().splitlines())


def show(fig, key):
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:                      # older Streamlit
        st.plotly_chart(fig, use_container_width=True, key=key)


def table(df, height=None):
    try:
        if height is None:
            st.dataframe(df, width="stretch")
        else:
            st.dataframe(df, width="stretch", height=height)
    except TypeError:
        if height is None:
            st.dataframe(df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True, height=height)


def style(fig, h=330):
    fig.update_layout(
        height=h,
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font_color=EV_THEME["text"],
        font_family="Inter, system-ui, sans-serif",
        margin=dict(l=10, r=10, t=45, b=10),
        colorway=PALETTE,
        title_font_size=16,
        title_font_weight=700,
        legend_title_text="",
        legend=dict(
            bgcolor="rgba(17,28,46,0.8)",
            bordercolor=EV_THEME["grid"],
            borderwidth=1
        )
    )
    fig.update_xaxes(gridcolor=BORDER, zeroline=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zeroline=False, linecolor=BORDER)
    return fig


# ============================ IMAGES ============================
def svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def asset_uri(name: str):
    """Return a data-URI for assets/<name>.(jpg|jpeg|png|webp) if the user supplied one."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = ASSETS / f"{name}.{ext}"
        if p.exists():
            mime = mimetypes.guess_type(p.name)[0] or "image/png"
            return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return None


def scooter_svg(body=None, accent="#FFFFFF") -> str:
    if body is None:
        body = EV_THEME["primary"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 150">
<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{body}"/>
<stop offset="1" stop-color="{body}" stop-opacity=".75"/></linearGradient>
<filter id="glow"><feGaussianBlur stdDeviation="2" result="coloredBlur"/>
<feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<ellipse cx="130" cy="138" rx="105" ry="6" fill="#000" opacity=".3"/>
<path d="M28 100 C 26 74 56 66 92 70 L 140 74 C 158 76 168 86 166 102 L 118 102 L 104 112 L 74 108 Z" fill="url(#g)" filter="url(#glow)"/>
<path d="M112 74 L 150 78 L 150 98 L 118 98 Z" fill="{accent}" opacity=".2"/>
<rect x="60" y="58" width="72" height="12" rx="6" fill="{EV_THEME['background']}" stroke="{accent}" stroke-opacity=".4"/>
<path d="M170 100 L 186 46" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>
<path d="M170 44 L 196 40" stroke="{accent}" stroke-width="6" stroke-linecap="round"/>
<path d="M176 56 L 200 52 L 198 64 L 178 66 Z" fill="url(#g)"/>
<circle cx="202" cy="52" r="5" fill="{EV_THEME['highlight']}" filter="url(#glow)"/>
<path d="M180 118 C 186 84 214 84 220 118" fill="none" stroke="{body}" stroke-width="6" stroke-linecap="round"/>
<g><circle cx="52" cy="112" r="22" fill="{EV_THEME['background']}" stroke="{body}" stroke-width="5"/>
<circle cx="52" cy="112" r="9" fill="{body}" filter="url(#glow)"/>
<circle cx="204" cy="112" r="22" fill="{EV_THEME['background']}" stroke="{body}" stroke-width="5"/>
<circle cx="204" cy="112" r="9" fill="{body}" filter="url(#glow)"/></g>
</svg>"""


def skyline_svg() -> str:
    import random
    rnd = random.Random(7)
    parts, x = [], 0
    colors = [EV_THEME["primary"], EV_THEME["secondary"], EV_THEME["highlight"]]
    while x < 1200:
        w, h = rnd.randint(28, 70), rnd.randint(50, 190)
        parts.append(f'<rect x="{x}" y="{220 - h}" width="{w}" height="{h}" fill="{EV_THEME["card"]}" opacity=".9"/>')
        for wy in range(220 - h + 8, 214, 14):
            for wx in range(x + 6, x + w - 6, 12):
                if rnd.random() > 0.55:
                    window_color = rnd.choice(colors)
                    parts.append(f'<rect x="{wx}" y="{wy}" width="4" height="6" fill="{window_color}" opacity=".6"/>')
        x += w + rnd.randint(2, 10)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 220" preserveAspectRatio="xMaxYMax slice">'
            f'<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{EV_THEME["background"]}"/>'
            f'<stop offset="1" stop-color="#05080F"/></linearGradient></defs>'
            '<rect width="1200" height="220" fill="url(#s)"/>' + "".join(parts) + "</svg>")


def logo_svg() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{EV_THEME['primary']}"/>
<stop offset="1" stop-color="{EV_THEME['secondary']}"/></linearGradient>
<filter id="glow2"><feGaussianBlur stdDeviation="1.5"/></filter></defs>
<circle cx="32" cy="32" r="29" fill="none" stroke="url(#lg)" stroke-width="4"/>
<path d="M32 14 L48 46 L40 46 L32 29 L24 46 L16 46 Z" fill="#fff"/>
<circle cx="32" cy="40" r="4" fill="{EV_THEME['highlight']}" filter="url(#glow2)"/></svg>"""


def leaf_svg() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="leaf-grad" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{EV_THEME['secondary']}"/>
<stop offset="1" stop-color="{EV_THEME['positive']}"/></linearGradient></defs>
<path d="M10 54 C 8 24 30 8 56 8 C 58 36 40 56 14 54 Z" fill="url(#leaf-grad)"/>
<path d="M12 52 C 24 36 34 28 48 18" stroke="{EV_THEME['background']}" stroke-width="3" fill="none"/></svg>"""


ICONS = {
    "scooter": '<circle cx="6" cy="17" r="3"/><circle cx="18" cy="17" r="3"/><path d="M6 17h6l3-8h3M15 9l1 8M9 13h3"/>',
    "gauge": '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-5"/>',
    "rupee": '<path d="M7 5h10M7 9h10M7 5c6 0 6 8 0 8l7 6"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "pin": '<path d="M12 22s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    "plug": '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>',
    "trophy": '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H4v2a3 3 0 0 0 4 3M16 6h4v2a3 3 0 0 1-4 3M12 13v4M8 21h8"/>',
    "leaf": '<path d="M5 20C4 10 10 4 20 4c0 10-6 16-15 16zM5 20c4-5 7-8 11-11"/>',
    "drop": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "grid": '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
}


def icon_uri(name: str, color: str = "#FFFFFF") -> str:
    return svg_uri(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
                   f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def icon_img(name: str, color: str = "#FFFFFF") -> str:
    """Icon as <img>; falls back to plain text/emoji for unknown names."""
    return f'<img src="{icon_uri(name, color)}"/>' if name in ICONS else name


# ============================ CSS ============================
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
.stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .banner, .kpi, .ins, .mcard, .sec,
.closing, .legend-row, .page-title, .side-art {{font-family:'Inter','Segoe UI',system-ui,sans-serif;}}
.page-title {{font-size:24px; font-weight:800; letter-spacing:.3px; border-left:5px solid {EV_THEME['primary']};
  padding-left:16px; margin:2px 0 16px; line-height:1.2; text-transform:uppercase; color:{EV_THEME['text']};}}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{visibility:hidden;}}
header[data-testid="stHeader"] {{background:transparent;}}
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] {{visibility:visible !important;}}
[data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button,
[data-testid="stExpandSidebarButton"] {{color:{EV_THEME['primary']} !important; background:{EV_THEME['card']};
  border:1px solid {EV_THEME['grid']}; border-radius:12px;}}
.stApp {{background: linear-gradient(135deg, {EV_THEME['background']} 0%, #0A0E1A 50%, {EV_THEME['background']} 100%);
  color:{EV_THEME['text']};}}
.block-container {{padding-top:1rem; padding-bottom:2rem; max-width:1600px;}}
section[data-testid="stSidebar"] {{background:{EV_THEME['background']};
  border-right:2px solid {EV_THEME['grid']};}}
h1,h2,h3,h4 {{color:{EV_THEME['text']};}}
.banner {{position:relative; border-radius:20px; border:2px solid {EV_THEME['grid']}; overflow:hidden;
  background-size:cover; background-position:right center; padding:16px 32px 0; margin-bottom:20px;
  box-shadow:0 8px 32px rgba(0,217,255,0.15);}}
.b-row {{display:flex; align-items:center; gap:24px; min-height:140px;}}
.banner .logo {{height:80px; width:80px; flex:none; filter:drop-shadow(0 4px 12px rgba(0,217,255,0.4));}}
.b-text {{flex:1; min-width:0; padding-bottom:6px;}}
.b-title {{font-size:clamp(26px,2.8vw,42px); font-weight:900; letter-spacing:.8px; line-height:1.1;
  white-space:nowrap; text-shadow:0 2px 8px rgba(0,0,0,0.3);}}
.b-title span {{color:{EV_THEME['primary']}; text-shadow:0 0 20px {EV_THEME['primary']};}}
.b-sub {{font-size:14px; letter-spacing:.5px; color:{EV_THEME['muted_text']}; margin-top:8px; font-weight:500;}}
.b-sub2 {{font-size:13.5px; color:{EV_THEME['secondary']}; margin-top:3px; font-weight:600;}}
.b-tag {{display:flex; align-items:center; gap:12px; flex:none; font-size:16px; font-style:italic;
  color:{EV_THEME['text']}; line-height:1.35; padding-bottom:6px;}}
.b-tag img {{height:32px; filter:drop-shadow(0 2px 8px rgba(57,255,136,0.4));}}
.b-tag b {{font-weight:700;}}
.b-scooter {{height:138px; flex:none; align-self:flex-end; margin-bottom:-2px;
  filter:drop-shadow(0 4px 16px rgba(0,217,255,0.3));}}
@media (max-width:900px) {{.b-scooter {{display:none;}}}}
.live {{display:inline-block; margin-top:12px; font-weight:600; padding:5px 16px; border-radius:24px;
  font-size:12px; background:{EV_THEME['card']}; border:2px solid {EV_THEME['primary']};
  color:{EV_THEME['primary']}; box-shadow:0 4px 12px rgba(0,217,255,0.3);}}
.live i {{display:inline-block; width:8px; height:8px; border-radius:50%; background:{EV_THEME['primary']};
  margin-right:8px; animation:pulse 1.4s infinite; box-shadow:0 0 8px {EV_THEME['primary']};}}
@keyframes pulse {{0%{{box-shadow:0 0 0 0 rgba(0,217,255,.7)}} 70%{{box-shadow:0 0 0 10px rgba(0,217,255,0)}}
  100%{{box-shadow:0 0 0 0 rgba(0,217,255,0)}}}}
.kpi {{display:flex; gap:14px; align-items:center;
  background:linear-gradient(135deg,{EV_THEME['card']},#0D1424);
  border:2px solid {EV_THEME['grid']}; border-radius:16px; padding:16px; height:140px;
  box-sizing:border-box; overflow:hidden; transition:all 0.3s ease;
  box-shadow:0 4px 16px rgba(0,0,0,0.3);}}
.kpi:hover {{transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,217,255,0.2);}}
.kpi-ic {{width:56px; height:56px; border-radius:50%; border:3px solid; display:flex; align-items:center;
  justify-content:center; flex:none; box-shadow:0 4px 12px rgba(0,0,0,0.2);}}
.kpi-ic img {{width:28px; height:28px;}}
.kpi-body {{flex:1; min-width:0;}}
.kpi .t {{color:{EV_THEME['muted_text']}; font-size:13px; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;}}
.kpi .v {{font-size:clamp(20px,2vw,32px); font-weight:900; line-height:1.2; white-space:nowrap;
  color:{EV_THEME['text']};}}
.kpi-row {{display:flex; justify-content:space-between; align-items:center; gap:8px; min-width:0;}}
.kpi .d {{font-size:13px; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  min-width:0;}}
.kpi .d small {{color:{EV_THEME['muted_text']}; font-weight:400;}}
.kpi img.sp {{flex:none; width:88px; height:35px;}}
@media (max-width:1350px) {{.kpi .d small {{display:none;}} .b-tag {{display:none;}}}}
.ins {{display:flex; gap:12px; align-items:center; line-height:1.4; background:{EV_THEME['card']};
  border:2px solid {EV_THEME['grid']}; border-radius:14px; padding:12px 14px; margin-bottom:12px;
  font-size:14px; transition:all 0.3s ease;}}
.ins:hover {{border-color:{EV_THEME['primary']}; box-shadow:0 4px 12px rgba(0,217,255,0.2);}}
.ins .ic {{width:42px; height:42px; border-radius:12px; flex:none; display:flex; align-items:center;
  justify-content:center; background:{EV_THEME['primary']}22; border:2px solid {EV_THEME['primary']}55;}}
.ins .ic img {{width:22px; height:22px;}}
.sec {{display:flex; align-items:center; gap:12px; font-size:19px; font-weight:800; margin:8px 0 12px;
  text-transform:uppercase; letter-spacing:0.5px; color:{EV_THEME['text']};}}
.sec img {{width:24px; height:24px;}}
.sec:after {{content:""; flex:1; height:2px; background:linear-gradient(90deg,{EV_THEME['grid']},transparent);}}
.bar {{height:8px; background:{EV_THEME['grid']}; border-radius:6px; margin:10px 0 5px; overflow:hidden;}}
.bar span {{display:block; height:100%; border-radius:6px; transition:width 0.6s ease;}}
.mcard .s2 {{font-size:12px; color:{EV_THEME['muted_text']};}}
.closing {{display:flex; align-items:center; gap:18px; border-radius:16px; border:2px solid {EV_THEME['grid']};
  padding:20px 28px; margin-top:20px; background-size:cover; background-position:right center;
  box-shadow:0 4px 16px rgba(0,0,0,0.3);}}
.cl-leaf {{height:50px; filter:drop-shadow(0 2px 8px rgba(57,255,136,0.4));}}
.cl-t {{font-size:24px; font-weight:800; color:{EV_THEME['secondary']};}}
.cl-s {{color:{EV_THEME['muted_text']}; font-size:14px;}}
.cl-logo {{margin-left:auto; display:flex; align-items:center; gap:12px; font-size:26px; font-weight:900;
  letter-spacing:3px;}}
.cl-logo img {{height:42px;}}
.legend-row {{display:flex; justify-content:space-between; font-size:13.5px; padding:4px 0;
  color:{EV_THEME['muted_text']}; font-weight:500;}}
.legend-row i {{display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:10px;}}
.mcard {{background:{EV_THEME['card']}; border:2px solid {EV_THEME['grid']}; border-radius:16px;
  padding:12px 14px; text-align:center; transition:all 0.3s ease;}}
.mcard:hover {{transform:translateY(-4px); box-shadow:0 8px 24px rgba(0,217,255,0.2);}}
.mcard img {{width:100%; height:100px; object-fit:contain;}}
.mcard .n {{font-weight:800; font-size:16px;}}
.mcard .s {{font-size:13px; color:{EV_THEME['muted_text']}; line-height:1.6;}}
.side-art {{text-align:center; margin-top:24px;}}
.side-art img {{width:90%;}}
.side-art .tag {{color:{EV_THEME['primary']}; font-style:italic; font-size:15px; font-weight:600;}}
.foot {{color:{EV_THEME['muted_text']}; font-size:12px; margin-top:16px; text-align:center;}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)


# ============================ DATA ============================
@st.cache_data(show_spinner=False)
def load_csv(path: str, mtime: float) -> pd.DataFrame:
    """mtime is part of the cache key -> the file is re-read automatically when it changes."""
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data(show_spinner=False, ttl=10)
def load_remote(url: str) -> pd.DataFrame:
    return pd.read_json(url) if url.lower().split("?")[0].endswith(".json") else pd.read_csv(url)


def enrich(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["SalesDate"] = pd.to_datetime(d["SalesMonth"] + "-01")
    d["Year"], d["Month"] = d["SalesDate"].dt.year, d["SalesDate"].dt.month
    d["Revenue"] = d["ExShowroomPrice_INR"] * d["UnitsSold"]
    d["Battery"] = d["BatteryCapacity_kWh"].map(lambda x: f"{x:.1f} kWh")
    d["PriceBand"] = pd.cut(d["ExShowroomPrice_INR"], [0, 125000, 145000, 165000, 1e9],
                            labels=["<1.25L", "1.25-1.45L", "1.45-1.65L", ">1.65L"])
    d["kWh_per_km"] = d["BatteryCapacity_kWh"] / d["CertifiedRange_km"]
    d["CO2_saved_kg_yr"] = d["UnitsSold"] * ANNUAL_KM * (ICE_KG_PER_KM - d["kWh_per_km"] * GRID_KG_PER_KWH)
    return d


def simulate_tick(base: pd.DataFrame, n: int):
    """Append n fake 'just sold' records (resampled from history) to the session's live buffer."""
    now = datetime.now()
    rows = base.sample(n, replace=True).copy()
    start = int(base["RecordID"].max()) + 1
    live = st.session_state.get("live")
    if live is not None and len(live):
        start = int(live["RecordID"].max()) + 1
    rows["RecordID"] = np.arange(start, start + n)
    rows["SalesMonth"] = now.strftime("%Y-%m")
    rows["ModelYear"] = now.year
    rows["UnitsSold"] = np.random.choice([1, 1, 1, 2, 2, 3], n)
    rows["CustomerRating"] = (rows["CustomerRating"] + np.random.normal(0, 0.25, n)).clip(1, 5).round(1)
    rows["EventTime"] = now
    live = rows if live is None else pd.concat([live, rows], ignore_index=True)
    st.session_state["live"] = live.tail(20000)


def get_data(source: str, url: str, sim_n: int, tick: bool):
    """Returns (enriched dataframe, status text, live-feed dataframe)."""
    base = load_csv(str(CSV_PATH), CSV_PATH.stat().st_mtime)
    status = "AUTO-SYNC · file modified " + datetime.fromtimestamp(CSV_PATH.stat().st_mtime).strftime("%d %b %H:%M:%S")
    raw, feed = base, None
    if source == SRC_URL and url:
        try:
            remote = load_remote(url)
            missing = set(base.columns[:15]) - set(remote.columns)
            if missing:
                raise ValueError(f"missing columns: {sorted(missing)}")
            raw, status = remote, "LIVE API · fetched " + datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.sidebar.error(f"URL failed ({e}). Showing CSV instead.")
    elif source == SRC_SIM:
        if tick:
            simulate_tick(base, sim_n)
        live = st.session_state.get("live")
        if live is not None and len(live):
            raw = pd.concat([base, live], ignore_index=True)
            feed = live.tail(10).iloc[::-1]
        status = f"LIVE SIMULATOR · {0 if live is None else len(live):,} new records · " \
                 + datetime.now().strftime("%H:%M:%S")
    if feed is None:
        feed = raw.tail(10).iloc[::-1]
    return enrich(raw), status, feed


# ============================ UI PIECES ============================
def banner(status: str):
    hero = asset_uri("hero") or svg_uri(skyline_svg())
    scooter = asset_uri("scooter") or svg_uri(scooter_svg(TEAL, "#FFFFFF"))
    logo = asset_uri("logo") or svg_uri(logo_svg())
    st.markdown(html(f"""
    <div class="banner" style="background-image:linear-gradient(90deg,{PAGE_BG} 0%,rgba(7,26,36,.92) 40%,
         rgba(7,26,36,.25) 100%),url('{hero}')">
      <div class="b-row">
        <img class="logo" src="{logo}"/>
        <div class="b-text">
          <div class="b-title">EV MARKET <span>INTELLIGENCE</span></div>
          <div class="b-sub">Performance &nbsp;|&nbsp; Customers &nbsp;|&nbsp; Cities &nbsp;|&nbsp; Sustainability</div>
          <div class="b-sub2">Insights from Ather Electric Vehicles</div>
          <div class="live"><i></i>{status}</div>
        </div>
        <div class="b-tag"><img src="{svg_uri(leaf_svg())}"/><div><b>Better Mobility</b><br>for a Cleaner Tomorrow</div></div>
        <img class="b-scooter" src="{scooter}"/>
      </div>
    </div>"""), unsafe_allow_html=True)


def spark(vals, color, w=160, h=64):
    """Smoothed (3-point average) trend line with soft area fill and an end dot."""
    v = pd.Series([float(x) for x in vals])
    if len(v) < 3:
        return ""
    v = v.rolling(3, min_periods=1).mean().tail(12).tolist()
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    pad = 8
    xs = [pad + i * (w - 2 * pad) / (len(v) - 1) for i in range(len(v))]
    ys = [h - pad - (y - lo) / rng * (h - 2 * pad) for y in v]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{h - 2} {line} {xs[-1]:.1f},{h - 2}"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" '
           f'stop-opacity=".35"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
           f'<polygon points="{area}" fill="url(#a)"/>'
           f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" '
           f'stroke-linejoin="round"/><circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="4.5" fill="{color}"/></svg>')
    return f'<img class="sp" src="{svg_uri(svg)}"/>'


def kpi(col, icon, title, value, d, series, color):
    if d is None:
        dtxt = f'<span class="d" style="color:{EV_THEME["muted_text"]}">n/a</span>'
    else:
        c = EV_THEME["positive"] if d >= 0 else EV_THEME["negative"]
        dtxt = f'<span class="d" style="color:{c}">{"▲" if d >= 0 else "▼"} {abs(d):.1%} <small>vs last yr</small></span>'
    col.markdown(html(f"""<div class="kpi"><div class="kpi-ic" style="background:{color}33;border-color:{color}">{icon_img(icon, color)}</div>
      <div class="kpi-body"><div class="t">{title}</div><div class="v">{value}</div>
      <div class="kpi-row">{dtxt}{spark(series, color)}</div></div></div>"""), unsafe_allow_html=True)


def insight(icon, text):
    st.markdown(html(f'<div class="ins"><span class="ic">{icon_img(icon, EV_THEME["primary"])}</span><span>{text}</span></div>'),
                unsafe_allow_html=True)


def section(title: str, icon: str = "grid"):
    st.markdown(html(f'<div class="sec"><img src="{icon_uri(icon, EV_THEME["primary"])}"/>{title}</div>'), unsafe_allow_html=True)


def model_cards(df):
    g = df.groupby("Model").agg(Price=("ExShowroomPrice_INR", "mean"), Range=("CertifiedRange_km", "mean"),
                                Units=("UnitsSold", "sum"), Rating=("CustomerRating", "mean")).reset_index()
    g = g.sort_values("Units", ascending=False)
    tot = g.Units.sum() or 1
    for col, (_, r) in zip(st.columns(len(g)), g.iterrows()):
        body, acc = MODEL_COLORS.get(r.Model, (TEAL, "#FFFFFF"))
        pct = r.Units / tot
        col.markdown(html(f"""<div class="mcard"><img src="{svg_uri(scooter_svg(body, acc))}"/>
          <div class="n">{r.Model}</div>
          <div class="s">₹ {r.Price:,.0f} · {r.Range:.0f} km · ⭐ {r.Rating:.2f}</div>
          <div class="bar"><span style="width:{pct * 100:.0f}%;background:{body}"></span></div>
          <div class="s2">{int(r.Units):,} units · {pct:.0%} share</div></div>"""), unsafe_allow_html=True)


def closing_banner():
    hero = asset_uri("hero") or svg_uri(skyline_svg())
    logo = asset_uri("logo") or svg_uri(logo_svg())
    st.markdown(html(f"""<div class="closing" style="background-image:linear-gradient(90deg,rgba(7,26,36,.96),
        rgba(7,26,36,.55)),url('{hero}')"><img class="cl-leaf" src="{svg_uri(leaf_svg())}"/>
        <div><div class="cl-t">More EVs. Less Emissions.</div>
        <div class="cl-s">Every electric scooter on the road moves our cities toward cleaner, quieter streets.</div></div>
        <div class="cl-logo"><img src="{logo}"/><span>ATHER</span></div></div>"""), unsafe_allow_html=True)


def india_map(df, h=330, title="Vehicle Locations"):
    c = df.groupby("City", as_index=False).UnitsSold.sum()
    c["lat"] = c.City.map(lambda x: CITY_COORDS.get(x, (None, None))[0])
    c["lon"] = c.City.map(lambda x: CITY_COORDS.get(x, (None, None))[1])
    c = c.dropna(subset=["lat", "lon"])
    fig = px.scatter_geo(c, lat="lat", lon="lon", size="UnitsSold", hover_name="City", size_max=28,
                         color="UnitsSold", color_continuous_scale=[[0, EV_THEME["card"]],
                         [0.5, EV_THEME["primary"]], [1, EV_THEME["secondary"]]], title=title)
    fig.update_geos(visible=False, showcountries=True, countrycolor=EV_THEME["primary"],
                    showland=True, landcolor=EV_THEME["card"],
                    showocean=True, oceancolor=CARD_BG, lonaxis_range=[67, 98], lataxis_range=[6, 37],
                    bgcolor=CARD_BG)
    fig.update_layout(coloraxis_showscale=False)
    return style(fig, h)


# ============================ DASHBOARD BODY ============================
def render(page, flt, source, url, sim_n, tick):
    K = iter(range(1000))
    key = lambda: f"c{page}{next(K)}"          # noqa: E731  unique chart keys

    df_all, status, feed = get_data(source, url, sim_n, tick)
    banner(status)
    last = df_all["SalesDate"].max()

    df = df_all
    for col, sel in flt.items():
        if sel:
            df = df[df[col].isin(sel)]
    if df.empty:
        st.warning("No data for these filters.")
        return

    def ytd(frame, year):
        return frame[(frame.Year == year) & (frame.Month <= last.month)]

    def delta(fn):
        try:
            cur, prev = fn(ytd(df, last.year)), fn(ytd(df, last.year - 1))
        except Exception:
            return None
        return None if (not prev or pd.isna(prev) or pd.isna(cur)) else (cur - prev) / prev

    units = int(df.UnitsSold.sum())
    st.markdown(f'<div class="page-title">{page}</div>', unsafe_allow_html=True)

    # ---------------- KPI strip (Overview only) ----------------
    if page == "Overview":
        c1, c2, c3, c4 = st.columns(4)
        kpi(c1, "scooter", "Total Units Sold", f"{units:,}", delta(lambda x: x.UnitsSold.sum()),
            df.groupby("SalesDate").UnitsSold.sum().tail(14), TEAL)
        kpi(c2, "gauge", "Average Range", f"{df.CertifiedRange_km.mean():.0f} km",
            delta(lambda x: x.CertifiedRange_km.mean()), df.groupby("SalesDate").CertifiedRange_km.mean().tail(14), CYAN)
        kpi(c3, "rupee", "Avg Ex-Showroom Price", f"₹ {df.ExShowroomPrice_INR.mean():,.0f}",
            delta(lambda x: x.ExShowroomPrice_INR.mean()), df.groupby("SalesDate").ExShowroomPrice_INR.mean().tail(14), PURPLE)
        kpi(c4, "star", "Avg Customer Rating", f"{df.CustomerRating.mean():.2f} / 5",
            delta(lambda x: x.CustomerRating.mean()), df.groupby("SalesDate").CustomerRating.mean().tail(14), YELLOW)
        st.write("")

    # ---------------- Overview ----------------
    if page == "Overview":
        section("Model Lineup", "scooter")
        model_cards(df)
        st.write("")
        section("Market Performance", "bolt")
        left, right = st.columns([4, 1.45])
        m = df.groupby("Model", as_index=False).UnitsSold.sum().sort_values("UnitsSold", ascending=False)
        with left:
            a, b = st.columns(2)
            with a:
                show(style(px.bar(m, x="Model", y="UnitsSold", text_auto=",", title="Units Sold by Model")
                           .update_traces(marker_color=EV_THEME["primary"])), key())
            with b:
                c = df.groupby("City", as_index=False).UnitsSold.sum().nlargest(8, "UnitsSold").sort_values("UnitsSold")
                show(style(px.bar(c, x="UnitsSold", y="City", orientation="h", text_auto=",",
                                  title="Top 8 Cities by Units").update_traces(marker_color=EV_THEME["secondary"])), key())
            mo = df.groupby("SalesDate", as_index=False).UnitsSold.sum()
            mo["Rolling 3M"] = mo.UnitsSold.rolling(3).mean()
            fig = go.Figure([go.Scatter(x=mo.SalesDate, y=mo.UnitsSold, name="Units", mode="lines+markers",
                                        line_color=EV_THEME["primary"], marker=dict(size=6)),
                             go.Scatter(x=mo.SalesDate, y=mo["Rolling 3M"], name="3-month avg",
                                        line=dict(color=EV_THEME["highlight"], dash="dash", width=3))])
            fig.update_layout(title="Monthly Units Sold")
            show(style(fig), key())

            a, b, c3 = st.columns(3)
            with a:
                r = df.groupby("Model", as_index=False).CertifiedRange_km.mean().sort_values("CertifiedRange_km")
                show(style(px.bar(r, x="CertifiedRange_km", y="Model", orientation="h", text_auto=".0f",
                                  title="Average Range by Model (km)").update_traces(marker_color=EV_THEME["primary"])), key())
            with b:
                bt = df.groupby("Battery", as_index=False).UnitsSold.sum()
                show(style(px.pie(bt, names="Battery", values="UnitsSold", hole=.6,
                                  title="Battery Capacity Distribution")), key())
            with c3:
                show(india_map(df), key())

        with right:
            section("Key Insights", "bolt")
            top = m.iloc[0]
            top2 = df.groupby("City").UnitsSold.sum().nlargest(2)
            home = df[df.ChargingType.isin(["Home Charging", "Home + Public"])].UnitsSold.sum() / units
            d_price = delta(lambda x: x.ExShowroomPrice_INR.mean())
            insight("trophy", f"<b>{top.Model}</b> is the top-selling model with {top.UnitsSold / units:.0%} of units.")
            if len(top2) == 2:
                insight("pin", f"<b>{top2.index[0]}</b> and <b>{top2.index[1]}</b> together contribute "
                              f"{top2.sum() / units:.0%} of sales.")
            if d_price is not None:
                insight("rupee", f"Average price {'rose' if d_price >= 0 else 'fell'} {abs(d_price):.1%} vs the same "
                             f"period last year.")
            insight("plug", f"{home:.0%} of units are charged at home (alone or with public charging).")
            this_m = df[df.SalesDate == last].UnitsSold.sum()
            insight("bolt", f"<b>{this_m:,}</b> units recorded in {last:%B %Y} so far.")
            st.markdown("##### Top States")
            s = df.groupby("State").UnitsSold.sum().sort_values(ascending=False)
            top_s, others = s.head(5), s.iloc[5:].sum()
            rows = "".join(f'<div class="legend-row"><span><i style="background:{PALETTE[i]}"></i>{n}</span>'
                           f'<span>{v / units:.0%}</span></div>' for i, (n, v) in enumerate(top_s.items()))
            rows += f'<div class="legend-row"><span><i style="background:{EV_THEME["muted_text"]}"></i>Others</span>' \
                    f'<span>{others / units:.0%}</span></div>'
            st.markdown(html(rows), unsafe_allow_html=True)

        section("Vehicle Data" + (" · latest records" if source == SRC_SIM else ""), "grid")
        table(feed.drop(columns=DERIVED + ([] if source == SRC_SIM else ["EventTime"]), errors="ignore"), 290)
        if st.toggle("Prepare filtered CSV download", key="dl_toggle"):
            buf = df.drop(columns=DERIVED, errors="ignore").to_csv(index=False).encode()
            st.download_button("⬇ Download filtered data (CSV)", buf, "ather_filtered.csv", key="dl_btn")
        closing_banner()

    # ---------------- Models ----------------
    elif page == "Models":
        g = df.groupby("Model").agg(Price=("ExShowroomPrice_INR", "mean"), Range=("CertifiedRange_km", "mean"),
                                    Units=("UnitsSold", "sum"), Rating=("CustomerRating", "mean")).reset_index()
        model_cards(df)
        st.write("")
        a, b = st.columns(2)
        with a:
            show(style(px.scatter(g, x="Price", y="Range", size="Units", color="Model", size_max=55,
                                  title="Price vs Range (bubble = units)")), key())
        with b:
            g["Price per km"] = g.Price / g.Range
            show(style(px.bar(g.sort_values("Price per km"), x="Model", y="Price per km", text_auto=".0f",
                              title="Price per km of range (₹)").update_traces(marker_color="#8B5CF6")), key())
        my = df.pivot_table(index="Model", columns="Year", values="UnitsSold", aggfunc="sum")
        show(style(px.imshow(my, text_auto=",", color_continuous_scale=[[0, EV_THEME["card"]],
                   [0.5, EV_THEME["primary"]], [1, EV_THEME["secondary"]]], aspect="auto",
                             title="Units by Model and Year")), key())
        a, b = st.columns(2)
        with a:
            bb = df.groupby(["Model", "Battery"], as_index=False).UnitsSold.sum()
            show(style(px.bar(bb, x="Model", y="UnitsSold", color="Battery", title="Battery mix by model")
                       .update_layout(barnorm="percent")), key())
        with b:
            pb = df.groupby("PriceBand", observed=True, as_index=False).UnitsSold.sum()
            show(style(px.bar(pb, x="PriceBand", y="UnitsSold", title="Units by price band")
                       .update_traces(marker_color=EV_THEME["secondary"])), key())

    # ---------------- Cities ----------------
    elif page == "Cities":
        cs = df.groupby(["State", "City"], as_index=False).agg(Units=("UnitsSold", "sum"),
                                                              Price=("ExShowroomPrice_INR", "mean"),
                                                              Rating=("CustomerRating", "mean"))
        a, b = st.columns(2)
        with a:
            show(india_map(df, 420, "Sales footprint across India"), key())
        with b:
            show(style(px.treemap(cs, path=["State", "City"], values="Units", title="State → City",
                                  color_discrete_sequence=PALETTE), 420), key())
        q = df.assign(Q=df.SalesDate.dt.to_period("Q").astype(str)).groupby(["Q", "City"], as_index=False).UnitsSold.sum()
        top5 = df.groupby("City").UnitsSold.sum().nlargest(5).index
        show(style(px.line(q[q.City.isin(top5)], x="Q", y="UnitsSold", color="City", markers=True,
                           title="Top 5 cities by quarter"), 380), key())
        cs["Share %"] = (cs.Units / cs.Units.sum() * 100).round(1)
        table(cs.sort_values("Units", ascending=False).round(2))

    # ---------------- Charging ----------------
    elif page == "Charging":
        a, b = st.columns(2)
        with a:
            ch = df.groupby("ChargingType", as_index=False).UnitsSold.sum()
            show(style(px.pie(ch, names="ChargingType", values="UnitsSold", hole=.6, title="Charging type")), key())
        with b:
            cm = df.groupby(["Model", "ChargingType"], as_index=False).UnitsSold.sum()
            show(style(px.bar(cm, x="Model", y="UnitsSold", color="ChargingType", title="Charging mix by model")
                       .update_layout(barnorm="percent")), key())
        cc = df.groupby(["City", "ChargingType"], as_index=False).UnitsSold.sum()
        show(style(px.bar(cc, x="City", y="UnitsSold", color="ChargingType", title="Charging mix by city")
                   .update_layout(barnorm="percent"), 380), key())
        ct = df.groupby(["SalesDate", "ChargingType"], as_index=False).UnitsSold.sum()
        ct["Share"] = ct.UnitsSold / ct.groupby("SalesDate").UnitsSold.transform("sum")
        show(style(px.line(ct, x="SalesDate", y="Share", color="ChargingType", title="Charging share over time")
                   .update_yaxes(tickformat=".0%"), 340), key())

    # ---------------- Trends ----------------
    elif page == "Trends":
        mo = df.groupby("SalesDate", as_index=False).UnitsSold.sum()
        mo["Rolling 3M"] = mo.UnitsSold.rolling(3).mean()
        fig = go.Figure([go.Bar(x=mo.SalesDate, y=mo.UnitsSold, name="Units", marker_color=EV_THEME["secondary"]),
                         go.Scatter(x=mo.SalesDate, y=mo["Rolling 3M"], name="3-month avg",
                                    line=dict(color=EV_THEME["highlight"], width=3))])
        fig.update_layout(title="Monthly units sold")
        show(style(fig, 360), key())
        a, b = st.columns(2)
        with a:
            yy = df.groupby(["Year", "Month"], as_index=False).UnitsSold.sum()
            yy["Year"] = yy.Year.astype(str)
            show(style(px.line(yy, x="Month", y="UnitsSold", color="Year", markers=True,
                               title="Year-over-year seasonality")), key())
        with b:
            pr = df.groupby("SalesDate", as_index=False).ExShowroomPrice_INR.mean()
            show(style(px.line(pr, x="SalesDate", y="ExShowroomPrice_INR", title="Average ex-showroom price (₹)")
                       .update_traces(line_color="#8B5CF6")), key())
        mm = df.groupby(["SalesDate", "Model"], as_index=False).UnitsSold.sum()
        show(style(px.area(mm, x="SalesDate", y="UnitsSold", color="Model", title="Model contribution over time"), 380), key())

    # ---------------- Customer Insights ----------------
    elif page == "Customer Insights":
        a, b, c = st.columns(3)
        with a:
            show(style(px.histogram(df, x="CustomerRating", nbins=20, title="Rating distribution")
                       .update_traces(marker_color=EV_THEME["highlight"])), key())
        with b:
            w = df.groupby(["Model", "WarrantyYears"], as_index=False).UnitsSold.sum()
            w["WarrantyYears"] = w.WarrantyYears.astype(str) + " yrs"
            show(style(px.bar(w, x="Model", y="UnitsSold", color="WarrantyYears", title="Warranty by model")), key())
        with c:
            rc = df.groupby("City", as_index=False).CustomerRating.mean().sort_values("CustomerRating")
            show(style(px.bar(rc, x="CustomerRating", y="City", orientation="h", text_auto=".2f",
                              title="Average rating by city").update_xaxes(range=[3.5, 5])
                       .update_traces(marker_color=EV_THEME["primary"])), key())
        rm = df.groupby("Model", as_index=False).CustomerRating.mean()
        show(style(px.bar(rm, x="Model", y="CustomerRating", text_auto=".2f", title="Average rating by model")
                   .update_yaxes(range=[3.5, 5]).update_traces(marker_color=EV_THEME["primary"])), key())
        rt = df.groupby("SalesDate", as_index=False).CustomerRating.mean()
        show(style(px.line(rt, x="SalesDate", y="CustomerRating", title="Average rating over time")
                   .update_traces(line_color=EV_THEME["highlight"])), key())

    # ---------------- Sustainability ----------------
    else:
        tot_kg = df.CO2_saved_kg_yr.sum()
        litres = units * ANNUAL_KM / ICE_KM_PER_LITRE
        a, b, c = st.columns(3)
        kpi(a, "leaf", "CO₂ avoided / year (est.)", f"{tot_kg / 1000:,.0f} t", None, [], EV_THEME["positive"])
        kpi(b, "drop", "Petrol saved / year (est.)", f"{litres / 1e6:,.2f} M litres", None, [], EV_THEME["warning"])
        kpi(c, "leaf", "Tree equivalent (est.)", f"{tot_kg / KG_CO2_PER_TREE_YEAR:,.0f}", None, [], EV_THEME["secondary"])
        st.caption(f"Estimates only: {ANNUAL_KM:,} km/yr per scooter, petrol scooter {ICE_KG_PER_KM} kg CO₂/km, "
                   f"grid {GRID_KG_PER_KWH} kg CO₂/kWh, energy use = battery kWh ÷ certified range. Edit the "
                   f"constants at the top of the file.")
        a, b = st.columns(2)
        with a:
            sm = df.groupby("Model", as_index=False).CO2_saved_kg_yr.sum()
            sm["Tonnes"] = sm.CO2_saved_kg_yr / 1000
            show(style(px.bar(sm.sort_values("Tonnes"), x="Tonnes", y="Model", orientation="h", text_auto=",.0f",
                              title="CO₂ avoided per year by model (tonnes)").update_traces(marker_color=EV_THEME["positive"])), key())
        with b:
            cm = df.groupby("SalesDate", as_index=False).CO2_saved_kg_yr.sum()
            cm["Cumulative t/yr"] = cm.CO2_saved_kg_yr.cumsum() / 1000
            show(style(px.area(cm, x="SalesDate", y="Cumulative t/yr",
                               title="Fleet's cumulative annual CO₂ avoidance (tonnes)")
                       .update_traces(line_color=EV_THEME["secondary"], fillcolor=f"rgba(57,255,136,0.3)")), key())
        sc = df.groupby("City", as_index=False).CO2_saved_kg_yr.sum().nlargest(10, "CO2_saved_kg_yr")
        sc["Tonnes"] = sc.CO2_saved_kg_yr / 1000
        show(style(px.bar(sc, x="City", y="Tonnes", text_auto=",.0f", title="Top 10 cities by CO₂ avoided (t/yr)")
                   .update_traces(marker_color=EV_THEME["primary"]), 360), key())

    st.markdown('<div class="foot">Source: Ather EV Market Intelligence Dataset &nbsp;|&nbsp; '
                'Note: this is a synthetic dataset for educational purposes only.</div>', unsafe_allow_html=True)


# ============================ SIDEBAR + RUN ============================
raw_for_filters = load_csv(str(CSV_PATH), CSV_PATH.stat().st_mtime)

with st.sidebar:
    st.markdown(html(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                     f'<img src="{asset_uri("logo") or svg_uri(logo_svg())}" height="40"/>'
                     f'<span style="font-size:26px;font-weight:800;letter-spacing:2px">ATHER</span></div>'
                     f'<div style="color:{EV_THEME["primary"]};font-size:11px;font-weight:600;letter-spacing:1px">CLEAN ENERGY. SMARTER MOBILITY.</div>'),
                unsafe_allow_html=True)
    page = st.radio("Navigate", PAGES, format_func=lambda p: f"{PAGE_ICONS[p]}  {p}", label_visibility="collapsed")
        st.write(raw_for_filters.columns.tolist())
    st.stop()
    st.markdown("### 🔽 Filters")
    f_model = st.multiselect("Model", sorted(raw_for_filters.Model.unique()))
    f_year = st.multiselect("Year", sorted(set(pd.to_datetime(raw_for_filters.SalesMonth + "-01").dt.year)))
    f_state = st.multiselect("State", sorted(raw_for_filters.State.unique()))
    f_charge = st.multiselect("Charging type", sorted(raw_for_filters.ChargingType.unique()))

    st.markdown("### 🔴 Live data")
    source = st.radio("Data source", [SRC_CSV, SRC_SIM, SRC_URL], label_visibility="collapsed")
    url = st.text_input("CSV / JSON URL", placeholder="https://.../sales.csv") if source == SRC_URL else ""
    interval = st.slider("Refresh every (seconds)", 2, 60, 5)
    sim_n = st.slider("New records per tick", 1, 200, 25) if source == SRC_SIM else 0
    paused = st.toggle("Pause auto-refresh", value=False)
    if source == SRC_SIM and st.button("Reset simulated data"):
        st.session_state.pop("live", None)

    st.markdown(html(f'<div class="side-art"><img src="{asset_uri("scooter") or svg_uri(scooter_svg(EV_THEME["primary"]))}"/>'
                     f'<div class="tag">Ather Electric Scooters<br>Built for a Sustainable Future</div></div>'),
                unsafe_allow_html=True)

filters = {"Model": f_model, "Year": f_year, "State": f_state, "ChargingType": f_charge}
runner = st.fragment(run_every=None if paused else interval)(render)
runner(page, filters, source, url, sim_n, not paused)
