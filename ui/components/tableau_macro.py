"""
XERCES Macro Overview Tab Component
Embeds the interactive Tableau Macro Dashboard (Indian stock market.html).
"""

import os
import streamlit as st
import streamlit.components.v1 as components

TABLEAU_HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Indian stock market.html")

def render_tableau_macro_dashboard():
    """
    Renders the interactive Tableau Indian Stock Market dashboard inside Streamlit.
    """
    st.markdown("""
    <div style="background:rgba(7,18,32,0.65);border:1px solid rgba(0,200,255,0.15);padding:14px;border-radius:6px;margin-bottom:12px;">
        <h3 style="font-family:'Orbitron',sans-serif;color:#00c8ff;margin:0;font-size:1.2rem;">
            🏛️ MACRO MARKET OVERVIEW — TABLEAU DASHBOARD
        </h3>
        <p style="font-family:'Space Mono',monospace;color:#6a90aa;font-size:11px;margin-top:4px;margin-bottom:0;">
            [ INTERACTIVE MACRO TELEMETRY // SECTOR MAPS & MARKET BREADTH ]
        </p>
    </div>
    """, unsafe_allow_html=True)

    html_content = None
    if os.path.exists(TABLEAU_HTML_PATH):
        try:
            with open(TABLEAU_HTML_PATH, "r", encoding="utf-8") as f:
                html_content = f.read()
        except Exception:
            pass

    if not html_content:
        # Fallback embed code if local file reading is missing
        html_content = """
        <div class='tableauPlaceholder' id='viz1770011682018' style='position: relative; width: 100%; height: 850px;'>
            <noscript><a href='#'><img alt='Dashboard 1 ' src='https://public.tableau.com/static/images/In/Indianstockmarket/Dashboard1/1_rss.png' style='border: none' /></a></noscript>
            <object class='tableauViz' style='display:none; width: 100%; height: 850px;'>
                <param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' />
                <param name='embed_code_version' value='3' />
                <param name='site_root' value='' />
                <param name='name' value='Indianstockmarket/Dashboard1' />
                <param name='tabs' value='no' />
                <param name='toolbar' value='yes' />
                <param name='static_image' value='https://public.tableau.com/static/images/In/Indianstockmarket/Dashboard1/1.png' />
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
            vizElement.style.width='100%';
            vizElement.style.height='850px';
            var scriptElement = document.createElement('script');
            scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';
            vizElement.parentNode.insertBefore(scriptElement, vizElement);
        </script>
        """

    # Wrap in responsive div container
    wrapper_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 0; background-color: #020813; color: #e2e8f0; font-family: sans-serif; }}
            .tableauViz {{ margin: 0 auto; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    components.html(wrapper_html, height=880, scrolling=True)
