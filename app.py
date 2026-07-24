import streamlit as st
from dotenv import load_dotenv
from utils.export_utils import generate_pdf, generate_txt
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MeetMind — AI Meeting Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Theme Tokens ───────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":          "#0A0E14",
        "bg_grad":     "radial-gradient(1200px 600px at 10% -10%, #10192A 0%, #0A0E14 55%)",
        "surface":     "#131A24",
        "surface2":    "#1B2431",
        "border":      "#26303F",
        "accent":      "#2DD4BF",
        "accent2":     "#8B7CF6",
        "accent_rgb":  "45,212,191",
        "accent2_rgb": "139,124,246",
        "text":        "#ECF2F8",
        "text_muted":  "#95A2B4",
        "text_dim":    "#7A87A0",
        "success":     "#34D399",
        "success_rgb": "52,211,153",
        "warning":     "#FBBF24",
        "warning_rgb": "251,191,36",
        "error":       "#FB7185",
        "error_rgb":   "251,113,133",
        "card_shadow": "0 10px 30px rgba(0,0,0,0.45)",
        "footer_bg":   "#070A0F",
        "btn_text":    "#08110F",
        "input_bg":    "#131A24",
        "glass_blur":  "saturate(160%) blur(14px)",
    },
    "light": {
        "bg":          "#F5F7FB",
        "bg_grad":     "radial-gradient(1200px 600px at 10% -10%, #EAF6F3 0%, #F5F7FB 55%)",
        "surface":     "#FFFFFF",
        "surface2":    "#F0F3F8",
        "border":      "#DEE4EC",
        "accent":      "#0A7F6E",
        "accent2":     "#6C4FD1",
        "accent_rgb":  "10,127,110",
        "accent2_rgb": "108,79,209",
        "text":        "#121826",
        "text_muted":  "#525C6B",
        "text_dim":    "#6B7585",
        "success":     "#187A4B",
        "success_rgb": "24,122,75",
        "warning":     "#9A6300",
        "warning_rgb": "154,99,0",
        "error":       "#C22A3E",
        "error_rgb":   "194,42,62",
        "card_shadow": "0 8px 24px rgba(23,43,77,0.08)",
        "footer_bg":   "#101624",
        "btn_text":    "#FFFFFF",
        "input_bg":    "#FFFFFF",
        "glass_blur":  "saturate(180%) blur(14px)",
    },
}

# ─── Session State ───────────────────────────────────────────────────────────────
for k, v in {
    "theme": "dark", "result": None,
    "chat_history": [], "processing": False, "active_tab": "analyze",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

T = THEMES[st.session_state.theme]

# Opacity for the animated mesh-gradient background blobs — kept very subtle in
# light mode (a light background shows saturated color much more readily than a
# dark one), and low enough everywhere that text/buttons stay fully readable.
MESH_OPACITY = 0.11 if st.session_state.theme == "dark" else 0.05

# How translucent the glass footer's surface is, per theme. Dark mode reads best
# with a deeper, moodier glass; light mode wants to stay airy and bright. Kept
# fairly transparent so the blur/ambient glow behind it is clearly visible.
FOOTER_ALPHA = "94" if st.session_state.theme == "dark" else "CC"

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body, [data-testid="stApp"] {{
    background: {T["bg_grad"]} !important;
    background-color: {T["bg"]} !important;
    color: {T["text"]} !important;
    font-family: 'Inter', sans-serif;
    transition: background-color 0.35s ease, color 0.35s ease;
}}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{
    transition: background-color 0.35s ease;
}}
[data-testid="stSidebar"] {{
    background-color: {T["surface"]}EE !important;
    -webkit-backdrop-filter: {T["glass_blur"]};
    backdrop-filter: {T["glass_blur"]};
    border-right: 1px solid {T["border"]} !important;
    transition: background-color 0.35s ease, border-color 0.35s ease;
}}
[data-testid="stSidebar"] > div {{ padding-top: 0 !important; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton, [data-testid="stToolbar"] {{ display: none; }}
h1,h2,h3,h4 {{ font-family: 'Space Grotesk', sans-serif !important; color: {T["text"]} !important; }}
::selection {{ background: {T["accent"]}55; color: {T["text"]}; }}
:focus-visible {{ outline: 2px solid {T["accent"]} !important; outline-offset: 2px !important; }}

/* Buttons */
.stButton > button {{
    background: linear-gradient(135deg, {T["accent"]}, {T["accent2"]}) !important;
    background-size: 160% 160% !important;
    color: {T["btn_text"]} !important; border: none !important;
    border-radius: 10px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important; font-size: 0.92rem !important;
    padding: 0.55rem 1.3rem !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease, background-position 0.5s ease !important;
    box-shadow: 0 4px 14px rgba({T["accent_rgb"]},0.28) !important;
    letter-spacing: 0.02em !important;
}}
.stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 26px rgba({T["accent_rgb"]},0.4) !important;
    background-position: 100% 50% !important;
}}
.stButton > button,
.stButton > button p,
.stButton > button span,
.stButton > button div,
.stButton > button [data-testid="stMarkdownContainer"],
.stButton > button [data-testid="stMarkdownContainer"] p {{
    color: {T["btn_text"]} !important;
}}
.stButton > button:active {{ transform: translateY(0) scale(0.98) !important; }}


/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
    background-color: {T["input_bg"]} !important;
    border: 1.5px solid {T["border"]} !important;
    border-radius: 10px !important; color: {T["text"]} !important;
    caret-color: {T["text"]} !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.92rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {T["accent"]} !important;
    box-shadow: 0 0 0 3px rgba({T["accent_rgb"]},0.16) !important;
}}
.stSelectbox > div > div {{
    background-color: {T["input_bg"]} !important;
    border: 1.5px solid {T["border"]} !important;
    border-radius: 10px !important; color: {T["text"]} !important;
    transition: border-color 0.2s !important;
}}
[data-baseweb="select"]:hover > div {{ border-color: {T["accent"]}99 !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {T["border"]}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {T["accent"]}; }}

/* ── Ambient mesh-gradient background ── */
/* Purely decorative, fixed behind all content (z-index:-1) and click-through
   (pointer-events:none) so it can never block reading or interaction. Only
   `transform` is animated — no width/height/top/left/box-shadow — to stay
   GPU-friendly and avoid layout thrash. */
.ambient-background {{
    position: fixed; inset: 0; z-index: -1;
    overflow: hidden; pointer-events: none;
}}
.mesh-blob {{
    position: absolute; border-radius: 50%;
    filter: blur(100px);
    will-change: transform;
}}
.mesh-blob-1 {{
    width: 460px; height: 460px; top: -12%; left: -8%;
    background: {T["accent"]}; opacity: {MESH_OPACITY};
    animation: mesh-float-1 34s ease-in-out infinite;
}}
.mesh-blob-2 {{
    width: 420px; height: 420px; top: 38%; right: -10%;
    background: {T["accent2"]}; opacity: {MESH_OPACITY};
    animation: mesh-float-2 38s ease-in-out infinite;
}}
.mesh-blob-3 {{
    width: 380px; height: 380px; bottom: -14%; left: 28%;
    background: {T["accent"]}; opacity: {MESH_OPACITY * 0.9:.3f};
    animation: mesh-float-3 42s ease-in-out infinite;
}}
.mesh-blob-4 {{
    width: 300px; height: 300px; top: 10%; right: 20%;
    background: {T["accent2"]}; opacity: {MESH_OPACITY * 0.85:.3f};
    animation: mesh-float-4 30s ease-in-out infinite;
}}
.mesh-blob-5 {{
    width: 340px; height: 340px; bottom: 6%; right: 30%;
    background: {T["success"]}; opacity: {MESH_OPACITY * 0.45:.3f};
    animation: mesh-float-2 46s ease-in-out infinite reverse;
}}
@keyframes mesh-float-1 {{
    0%,100% {{ transform: translate(0,0) scale(1); }}
    33%     {{ transform: translate(70px,50px) scale(1.12); }}
    66%     {{ transform: translate(-30px,70px) scale(0.94); }}
}}
@keyframes mesh-float-2 {{
    0%,100% {{ transform: translate(0,0) scale(1); }}
    50%     {{ transform: translate(-80px,-60px) scale(1.16); }}
}}
@keyframes mesh-float-3 {{
    0%,100% {{ transform: translate(0,0) scale(1); }}
    50%     {{ transform: translate(60px,-45px) scale(1.06); }}
}}
@keyframes mesh-float-4 {{
    0%,100% {{ transform: translate(0,0) scale(1); }}
    50%     {{ transform: translate(-40px,55px) scale(0.9); }}
}}

/* ── Components ── */
.meetmind-logo {{
    display: flex; align-items: center; gap: 10px; padding: 20px 16px 12px;
}}
.logo-icon {{
    width: 36px; height: 36px;
    background: linear-gradient(135deg, {T["accent"]}, {T["accent2"]});
    border-radius: 10px; display: flex; align-items: center; justify-content: center;
    font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.1rem;
    color: #fff; flex-shrink: 0;
}}
.logo-name {{
    font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 1.15rem; color: {T["text"]}; letter-spacing: -0.02em;
}}
.logo-tag {{
    font-size: 0.65rem; font-weight: 500; color: {T["accent"]};
    letter-spacing: 0.08em; text-transform: uppercase;
}}
.section-divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, {T["border"]}, transparent);
    margin: 16px 0;
}}

/* Entrance animation, used across cards/panels */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

/* Stat card */
.stat-card {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: 14px; padding: 18px 20px;
    box-shadow: {T["card_shadow"]};
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    animation: fadeInUp 0.45s ease both;
}}
.stat-card:hover {{
    transform: translateY(-3px) scale(1.015);
    box-shadow: 0 12px 30px rgba({T["accent_rgb"]},0.16);
    border-color: {T["accent"]}66;
}}
.stat-label {{
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.1em; color: {T["text_muted"]}; margin-bottom: 6px;
}}
.stat-value {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.6rem; font-weight: 700; line-height: 1;
}}

/* Content card */
.content-card {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: 16px; padding: 24px 28px;
    margin-bottom: 18px; box-shadow: {T["card_shadow"]};
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    animation: fadeInUp 0.5s ease both;
}}
.content-card:hover {{ border-color: {T["accent"]}44; }}
.card-eyebrow {{
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: {T["accent"]}; margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}}
.card-body {{
    font-size: 0.95rem; color: {T["text_muted"]}; line-height: 1.8;
}}

/* Real Streamlit bordered container used for the Source Input card — replaces
   Streamlit's default plain border with the same content-card treatment, and
   properly nests the text input + buttons inside a single real element
   (fixes the empty floating box that an unclosed st.markdown div used to leave). */
div[data-testid="stVerticalBlockBorderWrapper"].st-key-source_input_card {{
    background: {T["surface"]} !important;
    border: 1px solid {T["border"]} !important;
    border-radius: 16px !important;
    box-shadow: {T["card_shadow"]} !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"].st-key-source_input_card:hover {{
    border-color: {T["accent"]}44 !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"].st-key-source_input_card > div > div[data-testid="stVerticalBlock"] {{
    gap: 0.6rem !important;
}}
/* Fallback in case a future Streamlit version places the key class elsewhere */
.st-key-source_input_card {{
    background: {T["surface"]} !important;
    border-radius: 16px !important;
}}
.st-key-source_input_card > div {{
    border-color: {T["border"]} !important;
    box-shadow: {T["card_shadow"]} !important;
}}

/* Animations */
.pulse-container {{
    display: flex; align-items: center; gap: 6px; padding: 10px 0;
}}
.pulse-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {T["accent"]};
    animation: pulse-wave 1.4s ease-in-out infinite;
}}
.pulse-dot:nth-child(2) {{ animation-delay: 0.2s; }}
.pulse-dot:nth-child(3) {{ animation-delay: 0.4s; }}
@keyframes pulse-wave {{
    0%,80%,100% {{ transform: scale(0.7); opacity: 0.4; }}
    40% {{ transform: scale(1.2); opacity: 1; }}
}}
.pulse-label {{
    font-size: 0.86rem; color: {T["text_muted"]};
    font-weight: 500; margin-left: 6px; font-style: italic;
}}

.step-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid {T["border"]}44;
}}
.step-row:last-child {{ border-bottom: none; }}
.step-icon {{
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700; flex-shrink: 0;
}}
.step-pending {{ background:{T["surface2"]}; border:2px solid {T["border"]}; color:{T["text_dim"]}; transition: all 0.3s ease; }}
.step-running {{
    background:rgba({T["accent_rgb"]},0.14); border:2px solid {T["accent"]}; color:{T["accent"]};
    animation: spin-ring 1.4s linear infinite;
}}
.step-done {{ background:rgba({T["success_rgb"]},0.14); border:2px solid {T["success"]}; color:{T["success"]}; animation: pop-in 0.3s ease; }}
@keyframes pop-in {{
    0% {{ transform: scale(0.6); opacity: 0.4; }}
    60% {{ transform: scale(1.12); }}
    100% {{ transform: scale(1); opacity: 1; }}
}}
@keyframes spin-ring {{
    0%   {{ box-shadow: 0 -3px 0 0 {T["accent"]}; }}
    25%  {{ box-shadow: 3px 0 0 0 {T["accent"]}; }}
    50%  {{ box-shadow: 0 3px 0 0 {T["accent"]}; }}
    75%  {{ box-shadow: -3px 0 0 0 {T["accent"]}; }}
    100% {{ box-shadow: 0 -3px 0 0 {T["accent"]}; }}
}}
.step-label {{ font-size: 0.88rem; font-weight: 500; color: {T["text"]}; }}

/* Waveform */
.waveform {{
    display: flex; align-items: flex-end; gap: 3px; height: 32px;
}}
.wave-bar {{
    width: 4px; border-radius: 2px;
    background: linear-gradient(180deg, {T["accent"]}, {T["accent2"]});
    animation: wave-bounce 1.2s ease-in-out infinite;
}}
.wave-bar:nth-child(1) {{ height:60%; animation-delay:0.0s; }}
.wave-bar:nth-child(2) {{ height:90%; animation-delay:0.1s; }}
.wave-bar:nth-child(3) {{ height:40%; animation-delay:0.2s; }}
.wave-bar:nth-child(4) {{ height:75%; animation-delay:0.3s; }}
.wave-bar:nth-child(5) {{ height:55%; animation-delay:0.15s; }}
.wave-bar:nth-child(6) {{ height:85%; animation-delay:0.25s; }}
.wave-bar:nth-child(7) {{ height:35%; animation-delay:0.05s; }}
.wave-bar:nth-child(8) {{ height:70%; animation-delay:0.35s; }}
@keyframes wave-bounce {{
    0%,100% {{ transform:scaleY(0.4); opacity:0.5; }}
    50% {{ transform:scaleY(1); opacity:1; }}
}}

/* Hero */
.hero-banner {{
    background: linear-gradient(135deg, {T["surface"]} 0%, {T["surface2"]} 100%);
    border: 1px solid {T["border"]}; border-radius: 20px;
    padding: 36px 40px; margin-bottom: 28px;
    position: relative; overflow: hidden;
    animation: fadeInUp 0.55s ease both;
}}
.hero-banner::before {{
    content:''; position:absolute; top:-60px; right:-60px;
    width:260px; height:260px;
    background:radial-gradient(circle, {T["accent"]}26 0%, transparent 70%);
    border-radius:50%;
    animation: drift 6s ease-in-out infinite;
}}
.hero-banner::after {{
    content:''; position:absolute; bottom:-80px; left:-40px;
    width:220px; height:220px;
    background:radial-gradient(circle, {T["accent2"]}1F 0%, transparent 70%);
    border-radius:50%;
    animation: drift 7s ease-in-out infinite reverse;
}}
@keyframes drift {{
    0%,100% {{ transform: translate(0,0) scale(1); }}
    50%     {{ transform: translate(-12px,10px) scale(1.06); }}
}}
.hero-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.3rem; font-weight: 700; color: {T["text"]};
    letter-spacing: -0.03em; line-height: 1.18; margin: 0 0 10px;
}}
.hero-title span {{
    background: linear-gradient(90deg, {T["accent"]}, {T["accent2"]}, {T["accent"]});
    background-size: 200% auto;
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: {T["accent"]};
    animation: hero-gradient-shift 6s ease-in-out infinite;
}}
@keyframes hero-gradient-shift {{
    0%,100% {{ background-position: 0% 50%; }}
    50%     {{ background-position: 100% 50%; }}
}}
.hero-sub {{
    font-size: 1.02rem; color: {T["text_muted"]};
    max-width: 520px; line-height: 1.7;
}}

/* Action item rows */
.action-item {{
    display:flex; align-items:flex-start; gap:10px;
    padding:8px 0; border-bottom:1px solid {T["border"]}44;
    transition: padding-left 0.18s ease;
}}
.action-item:hover {{ padding-left: 4px; }}
.action-item:last-child {{ border-bottom:none; }}
.action-dot {{
    width:6px; height:6px; border-radius:50%;
    background:{T["accent"]}; margin-top:6px; flex-shrink:0;
    box-shadow: 0 0 0 3px rgba({T["accent_rgb"]},0.16);
}}
.action-text {{ font-size:0.88rem; color:{T["text_muted"]}; line-height:1.55; }}

/* Chat */
.chat-bubble-user {{
    background: linear-gradient(135deg,{T["accent"]}22,{T["accent2"]}22);
    border:1px solid {T["accent"]}55; border-radius:14px 14px 4px 14px;
    padding:12px 16px; font-size:0.9rem; color:{T["text"]};
    margin-left:18%; line-height:1.55;
    animation: fadeInUp 0.3s ease both;
}}
.chat-bubble-ai {{
    background:{T["surface"]}; border:1px solid {T["border"]};
    border-radius:14px 14px 14px 4px; padding:12px 16px;
    font-size:0.9rem; color:{T["text"]}; margin-right:18%; line-height:1.55;
    box-shadow: {T["card_shadow"]};
    animation: fadeInUp 0.3s ease both;
}}
.chat-role {{
    font-size:0.68rem; font-weight:700; text-transform:uppercase;
    letter-spacing:0.1em; margin-bottom:6px;
}}
.chat-role-user {{ color:{T["accent"]}; }}
.chat-role-ai {{ color:{T["accent2"]}; }}
.typing-indicator {{ display:flex; align-items:center; gap:5px; padding:4px 0; }}
.typing-dot {{
    width:6px; height:6px; background:{T["accent2"]}; border-radius:50%;
    animation: typing 1.0s ease-in-out infinite;
}}
.typing-dot:nth-child(2) {{ animation-delay:0.15s; }}
.typing-dot:nth-child(3) {{ animation-delay:0.3s; }}
@keyframes typing {{
    0%,60%,100% {{ transform:translateY(0); opacity:0.4; }}
    30% {{ transform:translateY(-5px); opacity:1; }}
}}

/* Badges */
.badge {{
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:0.7rem; font-weight:600; letter-spacing:0.06em;
    text-transform:uppercase; transition: transform 0.15s ease;
}}
.badge:hover {{ transform: translateY(-1px); }}
.badge-success {{ background:rgba({T["success_rgb"]},0.14); color:{T["success"]}; border:1px solid rgba({T["success_rgb"]},0.3); }}
.badge-accent  {{ background:rgba({T["accent_rgb"]},0.12); color:{T["accent"]};  border:1px solid rgba({T["accent_rgb"]},0.28); }}
.badge-purple  {{ background:rgba({T["accent2_rgb"]},0.12);color:{T["accent2"]}; border:1px solid rgba({T["accent2_rgb"]},0.28); }}

.transcript-block {{
    background:{T["surface2"]}; border:1px solid {T["border"]};
    border-left:3px solid {T["accent"]}; border-radius:0 10px 10px 0;
    padding:16px 20px; font-family:'JetBrains Mono',monospace;
    font-size:0.78rem; color:{T["text_muted"]}; line-height:1.8;
    max-height:260px; overflow-y:auto; white-space:pre-wrap; word-break:break-word;
}}

/* ── About / scroll sections ── */
.about-section {{
    padding: 64px 0 48px;
    border-top: 1px solid {T["border"]};
}}
.about-section-label {{
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.14em; color: {T["accent"]}; margin-bottom: 12px;
    opacity: 0; transform: translateY(14px);
    animation: about-reveal linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 50%;
}}
.about-section-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.85rem; font-weight: 700; color: {T["text"]};
    letter-spacing: -0.025em; line-height: 1.22; margin-bottom: 14px;
    opacity: 0; transform: translateY(18px);
    animation: about-reveal linear both;
    animation-timeline: view();
    animation-range: entry 3% cover 55%;
}}
.about-section-body {{
    font-size: 0.98rem; color: {T["text_muted"]}; line-height: 1.85;
    max-width: 640px;
    opacity: 0; transform: translateY(18px);
    animation: about-reveal linear both;
    animation-timeline: view();
    animation-range: entry 6% cover 60%;
}}
@keyframes about-reveal {{
    to {{ opacity: 1; transform: translateY(0); }}
}}
@supports not (animation-timeline: view()) {{
    .about-section-label, .about-section-title, .about-section-body {{
        opacity: 1; transform: none; animation: fadeInUp 0.6s ease both;
    }}
}}

/* ── How-it-works: vertical roadmap / timeline with scroll reveal ── */
.roadmap {{
    position: relative;
    padding-left: 64px;
    margin-top: 8px;
}}
/* Static track — always visible, in the theme's border color */
.roadmap-track {{
    position: absolute; left: 19px; top: 6px; bottom: 6px; width: 2px;
    background: {T["border"]};
    border-radius: 2px;
}}
/* Colored fill that grows downward as the section scrolls into view.
   Only `transform` (scaleY) is animated — GPU-friendly, no layout thrash. */
.roadmap-fill {{
    position: absolute; left: 19px; top: 6px; width: 2px; height: 100%;
    background: linear-gradient(to bottom, {T["accent"]}, {T["accent2"]});
    border-radius: 2px;
    transform-origin: top;
    transform: scaleY(0);
    animation: roadmap-grow linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 95%;
}}
@keyframes roadmap-grow {{
    to {{ transform: scaleY(1); }}
}}
@supports not (animation-timeline: view()) {{
    .roadmap-fill {{ transform: scaleY(1); animation: none; }}
}}

/* Each step zigzags in from alternating sides with a slight rotation + scale
   for a livelier reveal than a plain fade. Base (pre-animation) transform is
   set per direction class; the shared keyframe below resets everything to
   neutral, so both directions animate to the same resting state. */
.roadmap-step {{
    position: relative;
    padding-bottom: 40px;
    opacity: 0;
    animation: roadmap-step-reveal linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 42%;
}}
.roadmap-step:last-child {{ padding-bottom: 4px; }}
.roadmap-step.step-in-left  {{ transform: translateY(30px) translateX(-22px) rotate(-1.5deg) scale(0.96); }}
.roadmap-step.step-in-right {{ transform: translateY(30px) translateX(22px)  rotate(1.5deg)  scale(0.96); }}
@keyframes roadmap-step-reveal {{
    to {{ opacity: 1; transform: translateY(0) translateX(0) rotate(0deg) scale(1); }}
}}
@supports not (animation-timeline: view()) {{
    .roadmap-step {{
        opacity: 1; transform: none;
        animation: fadeInUp 0.6s ease both;
    }}
}}

/* Numbered node — sits on the timeline, transitions from a neutral ring into
   the accent gradient with a soft glow once its step has revealed. */
.roadmap-node {{
    position: absolute; left: -64px; top: 0;
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 0.92rem;
    background: {T["surface"]}; border: 2px solid {T["border"]}; color: {T["text_muted"]};
    z-index: 2;
    animation: roadmap-node-activate linear both;
    animation-timeline: view();
    animation-range: entry 5% cover 48%;
}}
@keyframes roadmap-node-activate {{
    to {{
        background: linear-gradient(135deg, {T["accent"]}, {T["accent2"]});
        border-color: {T["accent"]};
        color: #fff;
        box-shadow: 0 0 0 5px rgba({T["accent_rgb"]},0.16), 0 4px 16px rgba({T["accent_rgb"]},0.35);
    }}
}}
@supports not (animation-timeline: view()) {{
    .roadmap-node {{
        animation: none;
        background: linear-gradient(135deg, {T["accent"]}, {T["accent2"]});
        border-color: {T["accent"]}; color: #fff;
        box-shadow: 0 0 0 5px rgba({T["accent_rgb"]},0.16), 0 4px 16px rgba({T["accent_rgb"]},0.35);
    }}
}}
/* Continuous, gentle "radar ping" ring — pure transform/opacity, so it stays
   cheap even though it loops forever. */
.roadmap-node::after {{
    content: ''; position: absolute; inset: -6px; border-radius: 50%;
    border: 2px solid {T["accent"]}; opacity: 0; pointer-events: none;
    animation: roadmap-pulse-ring 2.8s ease-out infinite;
}}
@keyframes roadmap-pulse-ring {{
    0%   {{ transform: scale(0.82); opacity: 0.55; }}
    70%  {{ transform: scale(1.38); opacity: 0; }}
    100% {{ transform: scale(1.38); opacity: 0; }}
}}

.roadmap-content {{
    padding-top: 2px;
    opacity: 0;
    animation: roadmap-content-reveal linear both;
    animation-timeline: view();
    animation-range: entry 8% cover 46%;
}}
@keyframes roadmap-content-reveal {{
    to {{ opacity: 1; }}
}}
@supports not (animation-timeline: view()) {{
    .roadmap-content {{ opacity: 1; animation: none; }}
}}
.how-step-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem; font-weight: 600; color: {T["text"]}; margin-bottom: 6px;
    transition: color 0.2s ease;
}}
.roadmap-step:hover .how-step-title {{ color: {T["accent"]}; }}
.how-step-body {{ font-size: 0.92rem; color: {T["text_muted"]}; line-height: 1.7; max-width: 560px; }}



/* ── Tech stack: floating glass bubbles ── */
.tech-grid {{
    display: flex; flex-wrap: wrap; gap: 18px 20px; margin-top: 14px;
    /* generous gaps keep bubbles from overlapping while they gently drift */
}}
.tech-pill {{
    display: inline-flex; align-items: center; gap: 10px;
    background: {T["surface2"]}CC;
    -webkit-backdrop-filter: {T["glass_blur"]};
    backdrop-filter: {T["glass_blur"]};
    border: 1px solid {T["border"]};
    border-radius: 18px; padding: 14px 22px;
    font-size: 0.95rem; font-weight: 500; color: {T["text"]};
    box-shadow: 0 4px 14px rgba({T["accent_rgb"]},0.06);
    transition: border-color 0.25s ease, background 0.25s ease,
                box-shadow 0.25s ease, transform 0.25s ease;
    will-change: transform;
}}
.tech-pill-dot {{
    width: 9px; height: 9px; border-radius: 50%;
    box-shadow: 0 0 0 4px currentColor22;
    flex-shrink: 0;
}}
/* Four distinct float paths — duration, delay, amplitude and rotation all
   differ so the bubbles never move in lockstep. Only `transform` animates. */
@keyframes floatBubbleA {{
    0%   {{ transform: translate(0,0) rotate(0deg); }}
    25%  {{ transform: translate(9px,-14px) rotate(1deg); }}
    50%  {{ transform: translate(-6px,-20px) rotate(-1deg); }}
    75%  {{ transform: translate(-13px,-7px) rotate(0.5deg); }}
    100% {{ transform: translate(0,0) rotate(0deg); }}
}}
@keyframes floatBubbleB {{
    0%   {{ transform: translate(0,0) rotate(0deg); }}
    30%  {{ transform: translate(-11px,-9px) rotate(-1.2deg); }}
    60%  {{ transform: translate(7px,-18px) rotate(1deg); }}
    100% {{ transform: translate(0,0) rotate(0deg); }}
}}
@keyframes floatBubbleC {{
    0%   {{ transform: translate(0,0) rotate(0deg); }}
    20%  {{ transform: translate(6px,-8px) rotate(0.8deg); }}
    55%  {{ transform: translate(-10px,-16px) rotate(-1deg); }}
    80%  {{ transform: translate(4px,-4px) rotate(0.5deg); }}
    100% {{ transform: translate(0,0) rotate(0deg); }}
}}
@keyframes floatBubbleD {{
    0%   {{ transform: translate(0,0) rotate(0deg); }}
    35%  {{ transform: translate(-8px,-17px) rotate(-0.8deg); }}
    70%  {{ transform: translate(10px,-6px) rotate(1deg); }}
    100% {{ transform: translate(0,0) rotate(0deg); }}
}}
.tech-grid .tech-pill:nth-child(4n+1) {{ animation: floatBubbleA 7.5s ease-in-out infinite; animation-delay: 0s; }}
.tech-grid .tech-pill:nth-child(4n+2) {{ animation: floatBubbleB 8.8s ease-in-out infinite; animation-delay: 0.7s; }}
.tech-grid .tech-pill:nth-child(4n+3) {{ animation: floatBubbleC 6.6s ease-in-out infinite; animation-delay: 1.3s; }}
.tech-grid .tech-pill:nth-child(4n)   {{ animation: floatBubbleD 9.4s ease-in-out infinite; animation-delay: 1.9s; }}
.tech-pill:hover {{
    animation-play-state: paused;
    border-color: {T["accent"]}99;
    background: rgba({T["accent_rgb"]},0.10);
    box-shadow: 0 0 0 4px rgba({T["accent_rgb"]},0.14), 0 10px 24px rgba({T["accent2_rgb"]},0.16);
    transform: scale(1.06) !important;
}}

/* Feature cards grid */
.feature-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px; margin-top: 8px;
}}
.feature-card {{
    background: {T["surface"]}; border: 1px solid {T["border"]};
    border-radius: 14px; padding: 22px 20px;
    transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
    opacity: 0; transform: translateY(24px) scale(0.97);
    animation: feature-card-reveal linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 55%;
}}
@keyframes feature-card-reveal {{
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@supports not (animation-timeline: view()) {{
    .feature-card {{ opacity: 1; transform: none; animation: fadeInUp 0.5s ease both; }}
}}
.feature-card:hover {{
    transform: translateY(-4px) scale(1) !important;
    border-color: {T["accent"]}66;
    box-shadow: 0 14px 32px rgba({T["accent_rgb"]},0.14);
}}
.feature-icon {{
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
    font-weight: 700; color: #fff; margin-bottom: 14px;
    transition: transform 0.22s ease;
}}
.feature-card:hover .feature-icon {{ transform: scale(1.08) rotate(-4deg); }}
.feature-title {{
    font-family: 'Space Grotesk', sans-serif; font-size: 0.98rem;
    font-weight: 600; color: {T["text"]}; margin-bottom: 6px;
}}
.feature-body {{ font-size: 0.86rem; color: {T["text_muted"]}; line-height: 1.65; }}

/* ── Footer: glassmorphism panel ── */
.site-footer {{
    background: {T["surface"]}{FOOTER_ALPHA};
    -webkit-backdrop-filter: saturate(180%) blur(22px);
    backdrop-filter: saturate(180%) blur(22px);
    border: 1px solid {T["border"]};
    padding: 48px 40px 28px;
    margin-top: 64px;
    border-radius: 24px 24px 0 0;
    position: relative; overflow: hidden;
    box-shadow: {T["card_shadow"]}, inset 0 1px 0 rgba(255,255,255,0.07);
}}
/* Two soft ambient glows — teal top-right, violet bottom-left — behind the glass */
.site-footer::before {{
    content:''; position:absolute; top:-100px; right:-60px;
    width:280px; height:280px;
    background:radial-gradient(circle, {T["accent"]}30 0%, transparent 70%);
    border-radius:50%;
}}
.site-footer::after {{
    content:''; position:absolute; bottom:-120px; left:-70px;
    width:260px; height:260px;
    background:radial-gradient(circle, {T["accent2"]}26 0%, transparent 70%);
    border-radius:50%;
}}
.footer-brand {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem; font-weight: 700; color: {T["text"]};
    letter-spacing: -0.02em; margin-bottom: 6px;
}}
.footer-tagline {{
    font-size: 0.82rem; color: {T["text_muted"]}; line-height: 1.6; max-width: 280px;
}}
.footer-col-title {{
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: {T["text_dim"]}; margin-bottom: 14px;
}}
.footer-link {{
    display: block; font-size: 0.84rem; color: {T["text_muted"]};
    text-decoration: none; margin-bottom: 8px;
    transition: color 0.15s ease, transform 0.15s ease;
}}
.footer-link:hover {{ color: {T["accent"]}; transform: translateX(3px); }}
.footer-bottom {{
    border-top: 1px solid {T["border"]};
    margin-top: 36px; padding-top: 20px;
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 10px;
}}
.footer-copy {{
    font-size: 0.78rem; color: {T["text_dim"]};
}}
.footer-made-with {{
    font-size: 0.78rem; color: {T["text_dim"]};
}}
.footer-made-with span {{ color: {T["accent"]}; }}


/* 👇 YAHAN PASTE KARO 👇 */
.footer-grid {{
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: 32px;
    margin-bottom: 8px;
}}
.footer-logo {{
    display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
}}
.footer-divider {{
    height: 1px;
    background: {T["border"]};
    margin-top: 12px;
}}
/* 👆 YAHAN TAK 👆 */

/* Blinking cursor */
.blink {{
    display: inline-block; width: 2px; height: 1em;
    background: {T["accent"]}; margin-left: 2px; vertical-align: text-bottom;
    animation: blink-anim 1s step-end infinite;
}}
@keyframes blink-anim {{
    0%,100% {{ opacity:1; }} 50% {{ opacity:0; }}
}}

/* Overrides */
[data-testid="stMarkdownContainer"] p {{ color:{T["text_muted"]}; line-height:1.65; }}
[data-testid="stExpander"] {{
    border:1px solid {T["border"]} !important;
    border-radius:12px !important; background:{T["surface"]} !important;
    box-shadow: {T["card_shadow"]} !important;
}}
[data-testid="stExpander"] summary {{
    color:{T["text"]} !important;
}}
[data-testid="stExpander"] summary svg {{
    fill:{T["text_muted"]} !important;
}}
.streamlit-expanderHeader {{
    font-family:'Space Grotesk',sans-serif !important;
    font-weight:600 !important; color:{T["text"]} !important;
}}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button * {{
    color: {T["btn_text"]} !important;
}}

/* Placeholder text */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
[data-testid="stChatInput"] textarea::placeholder {{
    color: {T["text_dim"]} !important;
    opacity: 1 !important;
}}

/* Chat input widget */
[data-testid="stChatInput"] {{
    background: {T["surface"]} !important;
    border: 1.5px solid {T["border"]} !important;
    border-radius: 14px !important;
    box-shadow: {T["card_shadow"]} !important;
    transition: border-color 0.2s ease !important;
}}
[data-testid="stChatInput"]:focus-within {{
    border-color: {T["accent"]} !important;
    box-shadow: 0 0 0 3px rgba({T["accent_rgb"]},0.16) !important;
}}
[data-testid="stChatInput"] textarea {{
    background: transparent !important;
    color: {T["text"]} !important;
    caret-color: {T["text"]} !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stChatInput"] button {{
    background: linear-gradient(135deg, {T["accent"]}, {T["accent2"]}) !important;
    border-radius: 8px !important;
}}
[data-testid="stChatInput"] button svg {{
    fill: {T["btn_text"]} !important;
}}

/* Alert boxes (st.warning / st.error / st.success / st.info) */
[data-testid="stAlert"] {{
    background: {T["surface2"]} !important;
    border: 1px solid {T["border"]} !important;
    border-left: 3px solid {T["accent"]} !important;
    border-radius: 10px !important;
    color: {T["text"]} !important;
}}
[data-testid="stAlert"] p {{ color: {T["text"]} !important; }}
[data-testid="stAlert"] svg {{ fill: {T["accent"]} !important; }}
div[data-baseweb="notification"][kind="warning"] {{ border-left-color: {T["warning"]} !important; }}
div[data-baseweb="notification"][kind="error"]   {{ border-left-color: {T["error"]} !important; }}
div[data-baseweb="notification"][kind="success"] {{ border-left-color: {T["success"]} !important; }}

/* Select dropdown popover (rendered in a portal, needs explicit theming) */
div[data-baseweb="popover"] div[data-baseweb="menu"] {{
    background: {T["surface"]} !important;
    border: 1px solid {T["border"]} !important;
    box-shadow: {T["card_shadow"]} !important;
}}
div[data-baseweb="popover"] li {{
    color: {T["text"]} !important;
    background: transparent !important;
}}
div[data-baseweb="popover"] li:hover {{
    background: rgba({T["accent_rgb"]},0.12) !important;
}}
.stSelectbox [data-baseweb="select"] > div {{
    color: {T["text"]} !important;
}}
.stSelectbox svg {{ fill: {T["text_muted"]} !important; }}

/* Links inside markdown content */
[data-testid="stMarkdownContainer"] a {{
    color: {T["accent"]} !important;
}}
/* =========================================
   Export Report Buttons
========================================= */

div.stDownloadButton {{
    width:100%;
}}

div.stDownloadButton > button {{

    width:100% !important;
    height:46px !important;

    border:none !important;
    border-radius:12px !important;

    background:linear-gradient(
        90deg,
        #2D8CFF 0%,
        #5C7CFA 100%
    ) !important;

    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;

    font-family:"Space Grotesk",sans-serif !important;
    font-size:15px !important;
    font-weight:600 !important;
    letter-spacing:0.2px !important;

    display:flex !important;
    justify-content:center !important;
    align-items:center !important;

    transition:all .25s ease !important;
}}

div.stDownloadButton > button * {{
    color:#FFFFFF !important;
    fill:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}}

div.stDownloadButton > button:hover {{

    transform:translateY(-2px);

    background:linear-gradient(
        90deg,
        #227CFF 0%,
        #4F73FA 100%
    ) !important;

    box-shadow:0 10px 22px rgba(45,140,255,.28);
}}

div.stDownloadButton > button:active {{
    transform:translateY(0);
}}

div.stDownloadButton > button:focus {{
    outline:none !important;
    color:#FFFFFF !important;
}}

div.stDownloadButton > button:disabled {{
    opacity:.65;
    cursor:not-allowed;
}}

/* ── Accessibility: honor reduced-motion preference ── */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration:0.01ms !important;
        animation-iteration-count:1 !important;
        transition-duration:0.01ms !important;
        scroll-behavior:auto !important;
    }}
}}
</style>
""", unsafe_allow_html=True)

# ─── Ambient mesh-gradient background layer ────────────────────────────────────
st.markdown("""
<div class="ambient-background">
    <div class="mesh-blob mesh-blob-1"></div>
    <div class="mesh-blob mesh-blob-2"></div>
    <div class="mesh-blob mesh-blob-3"></div>
    <div class="mesh-blob mesh-blob-4"></div>
    <div class="mesh-blob mesh-blob-5"></div>
</div>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────────
WAVE = ''.join(['<div class="wave-bar"></div>'] * 8)
WAVE_PAUSED = ''.join(['<div class="wave-bar" style="animation-play-state:paused;opacity:0.2;"></div>'] * 8)

def badge(text, kind="accent"):
    return f'<span class="badge badge-{kind}">{text}</span>'

def action_rows(text, dot_color=None):
    items = [l.strip() for l in text.split("\n") if l.strip()]
    style = f'style="background:{dot_color};"' if dot_color else ""
    rows = "".join([
        f'<div class="action-item"><div class="action-dot" {style}></div>'
        f'<div class="action-text">{i}</div></div>'
        for i in items
    ])
    return rows, len(items)

def render_pipeline_steps(states, steps):
    rows = ""
    for i, (label, _) in enumerate(steps):
        s = states[i]
        cls = "step-running" if s == "running" else ("step-done" if s == "done" else "step-pending")
        icon = "✓" if s == "done" else str(i + 1)
        rows += f'<div class="step-row"><div class="step-icon {cls}">{icon}</div><div class="step-label">{label}</div></div>'
    return f"""
    <div class="content-card">
        <div class="card-eyebrow">◈ Pipeline Running</div>
        <div class="pulse-container">
            <div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div>
            <span class="pulse-label">Processing your source…</span>
        </div>
        {rows}
    </div>"""


# ─── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="meetmind-logo">
        <div class="logo-icon">M</div>
        <div><div class="logo-name">MeetMind</div><div class="logo-tag">AI Intelligence</div></div>
    </div>
    <div class="section-divider"></div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Light", key="light_btn", use_container_width=True):
            st.session_state.theme = "light"; st.rerun()
    with c2:
        if st.button("Dark", key="dark_btn", use_container_width=True):
            st.session_state.theme = "dark"; st.rerun()

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:{T["text_dim"]};padding:0 4px;margin-bottom:8px;">Navigation</div>', unsafe_allow_html=True)

    if st.button("Analyze Source", key="nav_analyze", use_container_width=True):
        st.session_state.active_tab = "analyze"; st.rerun()
    if st.button("Chat with Meeting", key="nav_chat", use_container_width=True):
        st.session_state.active_tab = "chat"; st.rerun()

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:{T["text_dim"]};padding:0 4px;margin-bottom:8px;">Settings</div>', unsafe_allow_html=True)

    language = st.selectbox("Language", ["english", "hinglish", "hindi"], index=0, label_visibility="collapsed")
    st.markdown(f'<div style="font-size:0.74rem;color:{T["text_muted"]};padding:4px 4px 0;">Transcription language</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if st.session_state.result:
        r = st.session_state.result
        wc = len(r.get("transcript", "").split())
        ai_c = len([l for l in r.get("action_items", "").split("\n") if l.strip()])
        st.markdown(f"""
        <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:{T['text_dim']};margin-bottom:10px;">Session Stats</div>
        <div style="display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;justify-content:space-between;">
                <span style="font-size:0.8rem;color:{T['text_muted']};">Words</span>
                <span style="font-family:'Space Grotesk',sans-serif;font-size:0.85rem;font-weight:600;color:{T['accent']};">{wc:,}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="font-size:0.8rem;color:{T['text_muted']};">Action Items</span>
                <span style="font-family:'Space Grotesk',sans-serif;font-size:0.85rem;font-weight:600;color:{T['accent2']};">{ai_c}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="font-size:0.8rem;color:{T["text_dim"]};font-style:italic;">No session active</div>', unsafe_allow_html=True)


# ─── ANALYZE TAB ─────────────────────────────────────────────────────────────────
if st.session_state.active_tab == "analyze":

    # Hero
    st.markdown(f"""
    <div class="hero-banner">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">
            <div class="waveform">{WAVE}</div>
            {badge("AI-Powered")}
        </div>
        <div class="hero-title">Turn any meeting into<br><span>structured intelligence</span><div class="blink"></div></div>
        <div class="hero-sub" style="margin-top:12px;">Paste a YouTube URL or a local file path. MeetMind transcribes, summarizes, and extracts every decision and action item — instantly.</div>
    </div>
    """, unsafe_allow_html=True)

    # Input
    with st.container(border=True):
        st.markdown('<div class="card-eyebrow">◈ Source Input</div>', unsafe_allow_html=True)
        source_input = st.text_input("source", placeholder="https://youtube.com/watch?v=… or /path/to/recording.mp4", label_visibility="collapsed")
        col_run, col_clear = st.columns([3, 1])
        with col_run:
            run_btn = st.button("Run Analysis", key="run_btn", use_container_width=True)
        with col_clear:
            clear_btn = st.button("Clear", key="clear_btn", use_container_width=True)

    if clear_btn:
        st.session_state.result = None
        st.session_state.chat_history = []
        st.rerun()

    # Pipeline
    if run_btn and source_input.strip():
        steps = [
            ("Downloading & chunking audio",  "process_input"),
            ("Transcribing with Whisper",      "transcribe_all"),
            ("Generating title",               "generate_title"),
            ("Summarizing content",            "summarize"),
            ("Extracting action items",        "extract_action_items"),
            ("Extracting key decisions",       "extract_key_decisions"),
            ("Identifying open questions",     "extract_questions"),
            ("Building RAG index",             "build_rag_chain"),
        ]
        ph = st.empty()
        try:
            from utils.audio_processor import process_input
            from core.transcriber import transcribe_all
            from core.summarizer import summarize, generate_title
            from core.extractor import extract_action_items, extract_key_decisions, extract_questions
            from core.rag_engine import build_rag_chain, ask_question

            

            states = ["pending"] * len(steps)

            states[0] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            chunks = process_input(source_input.strip())
            states[0] = "done"

            states[1] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            transcript = transcribe_all(chunks, language)
            states[1] = "done"

            states[2] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            title = generate_title(transcript)
            states[2] = "done"

            states[3] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            summary = summarize(transcript)
            states[3] = "done"

            states[4] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            action_items = extract_action_items(transcript)
            states[4] = "done"

            states[5] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            decisions = extract_key_decisions(transcript)
            states[5] = "done"

            states[6] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)
            questions = extract_questions(transcript)
            states[6] = "done"

            states[7] = "running"
            ph.markdown(render_pipeline_steps(states, steps), unsafe_allow_html=True)

            print("=" * 60)
            print("Transcript length:", len(transcript) if transcript else 0)
            print("Transcript preview:")
            print(transcript[:500] if transcript else "EMPTY")
            print("=" * 60)

            rag_chain = build_rag_chain(transcript)
            states[7] = "done"

            ph.empty()

            st.session_state.result = {
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
                "rag_chain": rag_chain,
            }

            st.session_state.chat_history = []
            st.rerun()

        except ImportError as e:
            ph.empty()
            st.error(f"Import error: {e}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            ph.empty()
            st.error(f"Pipeline error: {e}")

    elif run_btn:
        st.warning("Please enter a YouTube URL or file path.")

       # Results
    if st.session_state.result:
        r = st.session_state.result

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin:8px 0 22px;">
            {badge("Analysis Complete","success")}
            <span style="font-family:'Space Grotesk',sans-serif;font-size:1.05rem;font-weight:600;color:{T['text']};">{r.get('title','Untitled')}</span>
        </div>
        """, unsafe_allow_html=True)

        wc = len(r.get("transcript", "").split())
        ai_c = len([l for l in r.get("action_items", "").split("\n") if l.strip()])
        dec_c = len([l for l in r.get("key_decisions", "").split("\n") if l.strip()])
        q_c = len([l for l in r.get("open_questions", "").split("\n") if l.strip()])

        for col, lbl, val, col_hex in zip(
            st.columns(4),
            ["Word Count", "Action Items", "Decisions", "Open Questions"],
            [f"{wc:,}", str(ai_c), str(dec_c), str(q_c)],
            [T["accent"], T["accent2"], T["success"], T["warning"]],
        ):
            with col:
                st.markdown(
                    f'<div class="stat-card"><div class="stat-label">{lbl}</div><div class="stat-value" style="color:{col_hex};">{val}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f'<div class="content-card"><div class="card-eyebrow">◈ Summary</div><div class="card-body">{r.get("summary","").replace(chr(10),"<br>")}</div></div>',
            unsafe_allow_html=True,
        )

        col_a, col_d = st.columns(2)

        with col_a:
            rows, cnt = action_rows(r.get("action_items", ""))
            none_html_a = f'<span style="color:{T["text_dim"]}">None detected</span>'
            st.markdown(
                f'<div class="content-card"><div class="card-eyebrow">◈ Action Items</div>{badge(str(cnt) + " tasks")}<br><br>{rows or none_html_a}</div>',
                unsafe_allow_html=True,
            )

        with col_d:
            rows_d, cnt_d = action_rows(r.get("key_decisions", ""), T["accent2"])
            accent2 = T["accent2"]
            text_dim = T["text_dim"]
            none_html_d = f'<span style="color:{text_dim}">None detected</span>'
            st.markdown(
                f'<div class="content-card"><div class="card-eyebrow" style="color:{accent2};">◈ Key Decisions</div>{badge(str(cnt_d) + " decisions", "purple")}<br><br>{rows_d or none_html_d}</div>',
                unsafe_allow_html=True,
            )

        q_items_txt = r.get("open_questions", "")

        if q_items_txt.strip():
            rows_q, _ = action_rows(q_items_txt, T["warning"])
            st.markdown(
                f'<div class="content-card"><div class="card-eyebrow" style="color:{T["warning"]};">◈ Open Questions</div>{rows_q}</div>',
                unsafe_allow_html=True,
            )

        with st.expander("Raw Transcript", expanded=False):
            st.markdown(
                f'<div class="transcript-block">{r.get("transcript","")}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"""
        <div style="margin-top:8px;padding:18px 22px;background:linear-gradient(135deg,{T["accent"]}0D,{T["accent2"]}0D);border:1px solid {T["accent"]}33;border-radius:14px;">
            <div style="font-family:'Space Grotesk',sans-serif;font-weight:600;color:{T['text']};margin-bottom:4px;">
                Ready to chat with this meeting?
            </div>
            <div style="font-size:0.83rem;color:{T['text_muted']};">
                Ask anything — decisions, context, follow-ups — powered by RAG.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

# ==========================
# Chat Interface
# ==========================
if st.session_state.active_tab == "chat":

    st.divider()
    st.header("💬 Chat with Meeting")

    if not st.session_state.result:
        st.warning("Please analyze a meeting first.")
        st.stop()

    rag_chain = st.session_state.result["rag_chain"]

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)

    question = st.chat_input("Ask anything about this meeting...")

    if question:
        st.session_state.chat_history.append(("user", question))

        answer = ask_question(rag_chain, question)

        st.session_state.chat_history.append(("assistant", answer))

        st.rerun()

        # ==========================
        # Export Meeting Report
        # ==========================
if st.session_state.result:
     r = st.session_state.result

     st.divider()
     st.subheader("Export Meeting Report")
     st.caption("Download your meeting summary for offline viewing or sharing.")

     pdf_data = generate_pdf(r)
     txt_data = generate_txt(r)
 
     col1, col2 = st.columns(2, gap="medium")

     with col1:
        st.download_button(
            "Download PDF",
            pdf_data,
            file_name="meeting_report.pdf",
            mime="application/pdf",
        )

     with col2:
        st.download_button(
            "Download TXT",
            txt_data,
            file_name="meeting_report.txt",
            mime="text/plain",
        )
     st.markdown("<div style='height:18px'></div>",unsafe_allow_html=True)

     if st.button("Open Chat Interface",key="goto_chat"):
        st.session_state.active_tab="chat"
        st.rerun()
# ═══════════════════════════════════════════════════════════════════════════════
# ─── SCROLLABLE ABOUT / HOW-IT-WORKS / TECH SECTIONS ──────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

# ── What is MeetMind ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="about-section">
    <div class="about-section-label">About the Project</div>
    <div class="about-section-title">What is MeetMind?</div>
    <div class="about-section-body">
        MeetMind is an end-to-end AI pipeline that converts any audio — a YouTube recording, a Zoom call, a local MP4 —
        into a structured knowledge artifact. You get a clean transcript, an AI-written summary, extracted action items,
        key decisions, and open questions, all in under a minute. Then you can ask follow-up questions in plain language
        and get grounded answers backed by the actual meeting content.
    </div>
    <br>
    <div class="about-section-body">
        Built as a B.Tech project exploring how modern LLM pipelines can make institutional knowledge instantly
        accessible — no more scrubbing through hour-long recordings or hunting through dense meeting notes.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Features grid ─────────────────────────────────────────────────────────────
feat_accent = T["accent"]
feat_purple = T["accent2"]
feat_green  = T["success"]
feat_warn   = T["warning"]

st.markdown(f"""
<div style="padding-bottom: 48px; border-top: 1px solid {T['border']}; padding-top: 48px;">
    <div class="about-section-label">Core Capabilities</div>
    <div class="about-section-title">Everything a meeting produces,<br>automatically extracted</div>
    <div class="feature-grid" style="margin-top:28px;">
        <div class="feature-card">
            <div class="feature-icon" style="background:linear-gradient(135deg,{feat_accent},{feat_purple});">TR</div>
            <div class="feature-title">Auto Transcription</div>
            <div class="feature-body">Whisper-powered speech-to-text that handles accented English, Hinglish, and background noise. Works on YouTube links and local files alike.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon" style="background:linear-gradient(135deg,{feat_purple},{feat_warn});">AI</div>
            <div class="feature-title">LLM Summarization</div>
            <div class="feature-body">A compact, coherent summary generated by a large language model — not keyword extraction. Captures intent, not just words.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon" style="background:linear-gradient(135deg,{feat_green},{feat_accent});">EX</div>
            <div class="feature-title">Structured Extraction</div>
            <div class="feature-body">Action items, key decisions, and open questions — each surfaced as a clean list, ready to paste into Notion, Jira, or your email.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon" style="background:linear-gradient(135deg,{feat_warn},{feat_purple});">RAG</div>
            <div class="feature-title">RAG-powered Chat</div>
            <div class="feature-body">Ask natural-language questions about your meeting. The retrieval-augmented system finds the right context before the LLM answers — no hallucination.</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── How it works ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="about-section">
    <div class="about-section-label">PIPELINE WALKTHROUGH</div>
    <div class="about-section-title">How It Works</div>
</div>
""", unsafe_allow_html=True)

steps = [
    (
        "01",
        "Audio Acquisition & Preprocessing",
        "The application accepts either a YouTube URL or a local file. "
        "For YouTube, yt-dlp extracts the audio. Pydub then splits it into overlapping 60-second chunks."
    ),
    (
        "02",
        "Speech-to-Text",
        "Each chunk is transcribed using Whisper. The transcripts are merged while removing overlap."
    ),
    (
        "03",
        "LLM Analysis",
        "The transcript is processed by GPT-4o/Groq/Ollama to generate the title, summary, action items, decisions and questions."
    ),
    (
        "04",
        "RAG Index",
        "Sentence embeddings are generated and stored in FAISS. LangChain manages retrieval."
    ),
    (
        "05",
        "Interactive Q&A",
        "Relevant transcript chunks are retrieved and provided to the LLM so answers stay grounded."
    )
]

roadmap_steps_html = "".join([
    f"""<div class="roadmap-step {'step-in-left' if i % 2 == 0 else 'step-in-right'}">
        <div class="roadmap-node">{num}</div>
        <div class="roadmap-content">
            <div class="how-step-title">{title}</div>
            <div class="how-step-body">{body}</div>
        </div>
    </div>"""
    for i, (num, title, body) in enumerate(steps)
])

st.markdown(f"""
<div class="roadmap">
    <div class="roadmap-track"></div>
    <div class="roadmap-fill"></div>
    {roadmap_steps_html}
</div>
""", unsafe_allow_html=True)

# ── Tech Stack ────────────────────────────────────────────────────────────────
tech_stacks = [
    ("#00D4AA", "Python 3.11",         "Core language"),
    ("#7C5CFC", "OpenAI Whisper",       "Speech-to-text"),
    ("#D29922", "LangChain",            "LLM orchestration"),
    ("#3FB950", "FAISS",                "Vector search"),
    ("#F85149", "yt-dlp",               "YouTube download"),
    ("#00D4AA", "pydub",                "Audio processing"),
    ("#7C5CFC", "Sentence Transformers","Embeddings"),
    ("#D29922", "GPT-4o / Groq",        "Language model"),
    ("#3FB950", "Streamlit",            "UI framework"),
    ("#00D4AA", "python-dotenv",        "Config management"),
]

_t_text = T["text"]
_t_muted = T["text_muted"]
pills_html = "".join([
    '<div class="tech-pill"><div class="tech-pill-dot" style="background:' + c + ';"></div><div><div style="font-weight:600;font-size:0.92rem;color:' + _t_text + ';">' + name + '</div><div style="font-size:0.8rem;color:' + _t_muted + ';">' + role + '</div></div></div>'
    for c, name, role in tech_stacks
])

st.markdown(f"""
<div style="padding: 48px 0; border-top: 1px solid {T['border']};">
    <div class="about-section-label">Tech Stack</div>
    <div class="about-section-title">Built with</div>
    <div class="about-section-body" style="margin-bottom:24px;">
        Every layer of the stack is open-source or freely accessible via API, making this
        deployable on a laptop or a free-tier cloud instance.
    </div>
    <div class="tech-grid">{pills_html}</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ─── FOOTER ───────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
footer_html = f"""
<div class="site-footer">
    <div class="footer-grid">
        <div>
            <div class="footer-logo">
                <div class="logo-icon">M</div>
                <div class="footer-brand">MeetMind</div>
            </div>
            <p class="footer-tagline">AI-powered meeting intelligence that converts meeting recordings into searchable insights, summaries, action items and interactive Q&amp;A.</p>
        </div>
        <div>
            <div class="footer-col-title">Project</div>
            <a class="footer-link" href="#">Overview</a>
            <a class="footer-link" href="#">Architecture</a>
            <a class="footer-link" href="#">Documentation</a>
            <a class="footer-link" href="#">Release Notes</a>
        </div>
        <div>
            <div class="footer-col-title">Technology</div>
            <a class="footer-link" href="https://openai.com/research/whisper" target="_blank">Whisper</a>
            <a class="footer-link" href="https://python.langchain.com/" target="_blank">LangChain</a>
            <a class="footer-link" href="https://faiss.ai/" target="_blank">FAISS</a>
            <a class="footer-link" href="https://streamlit.io/" target="_blank">Streamlit</a>
        </div>
        <div>
            <div class="footer-col-title">Resources</div>
            <a class="footer-link" href="#">GitHub</a>
            <a class="footer-link" href="#">Project Report</a>
            <a class="footer-link" href="#">Demo Video</a>
            <a class="footer-link" href="#">Contact</a>
        </div>
    </div>
    <div class="footer-divider"></div>
    <div class="footer-bottom">
        <span class="footer-copy">&copy; 2025 MeetMind &bull; 2026 Project</span>
        <span class="footer-made-with">Built with Python &bull; Streamlit &bull; Whisper &bull; LangChain &bull; FAISS &bull; GPT-4o</span>
    </div>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)