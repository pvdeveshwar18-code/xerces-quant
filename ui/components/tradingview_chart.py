"""
XERCES TradingView Lightweight Chart Component
Integrates responsive HTML5 TradingView widget for intraday & daily technical viewing.
"""

import streamlit as st
import streamlit.components.v1 as components

def render_tradingview_chart(symbol: str, height: int = 600, interval: str = "D"):
    """
    Renders an HTML5 TradingView Chart Widget for the given NSE/BSE symbol.
    """
    clean = symbol.replace(".NS", "").replace(".BO", "").upper()

    # Determine TradingView exchange prefix
    if symbol.endswith(".BO"):
        tv_symbol = f"BSE:{clean}"
    elif "^" in symbol:
        if symbol == "^NSEI": tv_symbol = "NSE:NIFTY"
        elif symbol == "^NSEBANK": tv_symbol = "NSE:BANKNIFTY"
        elif symbol == "^BSESN": tv_symbol = "BSE:SENSEX"
        elif symbol == "^CNXSC": tv_symbol = "NSE:NIFTY_SMALLCAP_100"
        else: tv_symbol = f"NSE:{clean}"
    else:
        tv_symbol = f"NSE:{clean}"

    tv_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            body {{ margin: 0; padding: 0; background-color: #0a192f; }}
            #tv_chart_container {{ width: 100%; height: {height}px; }}
        </style>
    </head>
    <body>
        <div class="tradingview-widget-container" id="tv_chart_container">
            <div id="tradingview_embed_chart" style="height:{height}px;width:100%;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
                "autosize": true,
                "symbol": "{tv_symbol}",
                "interval": "{interval}",
                "timezone": "Asia/Kolkata",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#0a192f",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_embed_chart",
                "hide_side_toolbar": false,
                "details": true,
                "hotlist": true,
                "calendar": true,
                "studies": [
                    "RSI@tv-basicstudies",
                    "MACD@tv-basicstudies",
                    "MASimple@tv-basicstudies"
                ]
            }});
            </script>
        </div>
    </body>
    </html>
    """

    components.html(tv_html, height=height + 20, scrolling=False)
