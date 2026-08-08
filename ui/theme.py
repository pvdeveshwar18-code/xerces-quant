"""
XERCES Styling & Design System Theme
"""

import streamlit as st

def apply_theme():
    st.set_page_config(page_title="XERCES // QUANT ENGINE", page_icon="⚡", layout="wide")
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
    html,body,[class*="css"]{font-family:'Inter',sans-serif;}
    .stApp{background:radial-gradient(circle at 50% 0%,#0a192f 0%,#020813 100%) !important;color:#e2e8f0 !important;}
    section[data-testid="stSidebar"]{background-color:rgba(3,11,24,0.97) !important;border-right:1px solid rgba(0,200,255,0.15) !important;}
    .xerces-title{font-family:'Orbitron',sans-serif;font-weight:900;font-size:2.2rem;background:linear-gradient(90deg,#00c8ff,#00e87a);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:3px;margin:0;}
    .telemetry-tag{font-family:'Space Mono',monospace;color:#4a7090;font-size:11px;letter-spacing:1px;}
    .section-header{font-family:'Orbitron',sans-serif;color:#00c8ff;font-size:12px;letter-spacing:1px;margin-top:12px;margin-bottom:8px;}
    .glass-card{background:rgba(7,18,32,0.65);border:1px solid rgba(0,200,255,0.15);border-radius:6px;padding:12px 16px;margin-bottom:10px;backdrop-filter:blur(4px);}
    .glass-label{font-family:'Space Mono',monospace;color:#6a90aa;font-size:10px;margin:0;text-transform:uppercase;letter-spacing:1px;}
    .glass-value{font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:700;margin-top:2px;}
    div[data-baseweb="tab-list"]{gap:3px;}
    button[data-baseweb="tab"]{font-family:'Space Mono',monospace !important;border-radius:4px !important;background:rgba(10,25,40,0.4) !important;color:#5a80a0 !important;border:1px solid rgba(0,200,255,0.05) !important;padding:0.35rem 0.75rem !important;font-size:11px !important;}
    button[data-baseweb="tab"][aria-selected="true"]{border-color:#00c8ff !important;color:#00c8ff !important;background:rgba(13,32,53,0.75) !important;}
    .signal-buy{color:#00e87a;font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.4rem;}
    .signal-sell{color:#ff3355;font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.4rem;}
    .signal-hold{color:#ffcc00;font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.4rem;}
    </style>
    """, unsafe_allow_html=True)
