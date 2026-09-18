import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

TABLEAU_HTML = """
<div class='tableauPlaceholder' id='viz1770011682018' style='position: relative; width: 100%; height: 750px;'>
    <noscript>
        <a href='#'><img alt='Dashboard 1 ' src='https:&#47;&#47;public.tableau.com&#47;static&#47;images&#47;In&#47;Indianstockmarket&#47;Dashboard1&#47;1_rss.png' style='border: none' /></a>
    </noscript>
    <object class='tableauViz' style='display:none; width: 100%; height: 750px;'>
        <param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' /> 
        <param name='embed_code_version' value='3' /> 
        <param name='site_root' value='' />
        <param name='name' value='Indianstockmarket&#47;Dashboard1' />
        <param name='tabs' value='no' />
        <param name='toolbar' value='yes' />
        <param name='static_image' value='https:&#47;&#47;public.tableau.com&#47;static&#47;images&#47;In&#47;Indianstockmarket&#47;Dashboard1&#47;1.png' /> 
        <param name='animate_transition' value='yes' />
        <param name='display_static_image' value='yes' />
        <param name='display_spinner' value='yes' />
        <param name='display_overlay' value='yes' />
        <param name='display_count' value='yes' />
        <param name='language' value='en-US' />
    </object>
</div>
<script type='text/javascript'>
    var divElement = document.getElementById('viz1770011682018');
    var vizElement = divElement.getElementsByTagName('object')[0];
    vizElement.style.width = '100%';
    vizElement.style.height = '750px';
    var scriptElement = document.createElement('script');
    scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';
    vizElement.parentNode.insertBefore(scriptElement, vizElement);
</script>
"""

def render_macro_tab(idx_data: dict[str, pd.DataFrame]):
    """Render Macro Overview with interactive Tableau Indian Stock Market dashboard."""
    st.markdown('<p class="section-header">[ 🌐 INDIAN MACRO OVERVIEW & TABLEAU DASHBOARD ]</p>', unsafe_allow_html=True)
    st.caption("Interactive macro analytics and market distribution dashboard for Indian Equities.")

    # Live Market Index Summary Cards
    INDEX_META = [
        ("^NSEI","NIFTY 50","#00e87a"), ("^NSEBANK","BANK NIFTY","#00c8ff"),
        ("^BSESN","SENSEX","#ffcc00"),  ("^CRSMID","NIFTY MIDCAP","#ff6b35"),
        ("^CNXSC","NIFTY SMALLCAP","#7c6ef8"), ("^INDIAVIX","INDIA VIX","#ff3355"),
    ]
    
    cols = st.columns(6)
    for col, (sym, name, clr) in zip(cols, INDEX_META):
        try:
            idf  = idx_data.get(sym)
            if idf is None or len(idf) < 2:
                col.warning(name); continue
            cv   = float(idf["Close"].iloc[-1])
            pv   = float(idf["Close"].iloc[-2])
            chg  = (cv - pv) / pv * 100
            flip = sym == "^INDIAVIX"
            cclr = ("#ff3355" if chg >= 0 else "#00e87a") if flip else ("#00e87a" if chg >= 0 else "#ff3355")
            arrow= "▲" if chg >= 0 else "▼"
            col.markdown(f"""<div class="glass-card">
                <p class="glass-label" style="color:{clr};">{name}</p>
                <div class="glass-value" style="font-size:1.1rem;">{cv:,.2f}</div>
                <p style="font-size:11px;color:{cclr};margin:2px 0;font-weight:600;">{arrow} {abs(chg):.2f}%</p>
            </div>""", unsafe_allow_html=True)
        except Exception:
            col.warning(name)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-header">[ 📊 INTERACTIVE TABLEAU MACRO ANALYTICS ]</p>', unsafe_allow_html=True)

    # Embed Tableau Dashboard
    components.html(TABLEAU_HTML, height=780, scrolling=True)
