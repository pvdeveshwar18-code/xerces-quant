import streamlit as st
from data.loader import fetch_news

BULL_KW = {"surge","rally","grow","growth","jump","rise","gain","profit","record","bullish","beat",
            "positive","expand","outperform","buy","upgrade","strong","boom","breakout","upside"}
BEAR_KW = {"slump","fall","decline","drop","loss","plunge","negative","bearish","miss","sell",
            "downgrade","weak","crash","warn","crisis","debt","cut","lower","pressure","concern"}

def sentiment_score(items):
    if not items:
        return 0.0, "NEUTRAL"
    total = 0
    for it in items:
        tl = it["title"].lower()
        words = set(tl.split())
        bull = len(words & BULL_KW)
        bear = len(words & BEAR_KW)
        for bw in BULL_KW:
            if f"not {bw}" in tl or f"no {bw}" in tl:
                bull -= 2
        total += (bull - bear)
    avg = total / len(items)
    cat = "BULLISH" if avg > 0.2 else "BEARISH" if avg < -0.2 else "NEUTRAL"
    return round(avg, 3), cat

def render_news_tab(selected_name: str, selected_ticker: str):
    """Render News Headlines & Keyword Sentiment Scoring tab."""
    st.markdown(f'<p class="section-header">[ NEWS & SENTIMENT — {selected_name} ]</p>', unsafe_allow_html=True)
    with st.spinner("Fetching headlines..."):
        items = fetch_news(selected_ticker, selected_name)

    if items:
        score, cat = sentiment_score(items)
        sent_clr = {"BULLISH": "#00e87a", "BEARISH": "#ff3355", "NEUTRAL": "#ffcc00"}[cat]
        ns1, ns2 = st.columns([1, 2])
        with ns1:
            st.markdown(f"""<div class="glass-card" style="text-align:center;padding:20px 12px;">
                <p class="glass-label">Sentiment</p>
                <div style="font-family:'Orbitron',sans-serif;font-size:1.8rem;font-weight:900;color:{sent_clr};margin:8px 0;">{cat}</div>
                <p style="font-size:10px;color:#6a90aa;margin:0;">Score: {score:+.3f} | {len(items)} headlines</p>
            </div>""", unsafe_allow_html=True)
        with ns2:
            bull_cnt = sum(1 for it in items if any(w in it["title"].lower().split() for w in BULL_KW))
            bear_cnt = sum(1 for it in items if any(w in it["title"].lower().split() for w in BEAR_KW))
            st.markdown(f"""<div class="glass-card">
                <p class="glass-label" style="margin-bottom:8px;">Keyword Breakdown</p>
                <div style="font-family:'Space Mono',monospace;font-size:12px;">
                    Bullish headlines: <span style="color:#00e87a;font-weight:700;">{bull_cnt}</span> &nbsp;|&nbsp;
                    Bearish headlines: <span style="color:#ff3355;font-weight:700;">{bear_cnt}</span>
                </div>
                <p style="font-size:11px;color:#6a90aa;margin-top:6px;line-height:1.6;">
                Financial keyword scoring with negation detection. Bullish terms: surge, rally, beat, upgrade...
                Bearish terms: drop, warn, miss, downgrade, loss...
                </p>
            </div>""", unsafe_allow_html=True)

        for it in items:
            tl = it["title"].lower()
            b = any(w in tl.split() for w in BULL_KW)
            r = any(w in tl.split() for w in BEAR_KW)
            ic = "🟢" if b and not r else "🔴" if r and not b else "⚪"
            st.markdown(f"""<div class="glass-card" style="margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <a href="{it['link']}" target="_blank" style="color:#ddeeff;text-decoration:none;font-weight:600;font-size:12px;">
                        {ic} {it['title']}
                    </a>
                    <span style="color:#6a90aa;font-size:10px;white-space:nowrap;margin-left:12px;">{it.get('source','')} · {it.get('pubDate', it.get('date', ''))[:16]}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info(f"No recent news found for {selected_name}.")
