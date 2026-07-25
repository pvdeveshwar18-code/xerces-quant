"""
XERCES+ — Enhancement Module
Adds: Watchlist, Alerts, Sector Heatmap, Compare, AI Analyst, Journal, PDF/Excel Export
Author: E1 (Emergent) — 2026
Non-destructive: all existing app.py features remain intact.
"""

import os
import io
import json
import asyncio
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf

# ── Persistent storage paths ────────────────────────────────────────────────
def _resolve_data_dir() -> Path:
    """Pick a writable directory that works locally, in Docker, and on Streamlit Cloud."""
    # 1. Explicit env override
    env_dir = os.environ.get("XERCES_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    # 2. Alongside this module (works everywhere the code is checked out)
    try:
        here = Path(__file__).resolve().parent / "data"
        here.mkdir(parents=True, exist_ok=True)
        return here
    except Exception:
        pass
    # 3. Current working directory
    try:
        cwd = Path.cwd() / "data"
        cwd.mkdir(parents=True, exist_ok=True)
        return cwd
    except Exception:
        pass
    # 4. Last-resort: OS temp dir (ephemeral but always writable)
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "xerces_data"
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp

DATA_DIR = _resolve_data_dir()
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
JOURNAL_FILE   = DATA_DIR / "journal.csv"
ALERTS_FILE    = DATA_DIR / "alerts.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

# ──────────────────────────────────────────────────────────────────────────
# 1. WATCHLIST — persistent JSON file
# ──────────────────────────────────────────────────────────────────────────
def load_watchlist() -> list:
    if WATCHLIST_FILE.exists():
        try:
            return json.loads(WATCHLIST_FILE.read_text())
        except Exception:
            return []
    return []

def save_watchlist(items: list):
    WATCHLIST_FILE.write_text(json.dumps(items, indent=2))

def add_to_watchlist(ticker: str, name: str):
    wl = load_watchlist()
    if not any(w["ticker"] == ticker for w in wl):
        wl.append({"ticker": ticker, "name": name,
                   "added": datetime.datetime.now().isoformat()})
        save_watchlist(wl)
        return True
    return False

def remove_from_watchlist(ticker: str):
    wl = [w for w in load_watchlist() if w["ticker"] != ticker]
    save_watchlist(wl)

# ──────────────────────────────────────────────────────────────────────────
# 2. ALERTS — persistent JSON, evaluated on each page load
# ──────────────────────────────────────────────────────────────────────────
def load_alerts() -> list:
    if ALERTS_FILE.exists():
        try:
            return json.loads(ALERTS_FILE.read_text())
        except Exception:
            return []
    return []

def save_alerts(items: list):
    ALERTS_FILE.write_text(json.dumps(items, indent=2))

def add_alert(ticker: str, name: str, kind: str, op: str, value: float):
    """kind: 'price' or 'rsi' ; op: '>' or '<'"""
    alerts = load_alerts()
    alerts.append({
        "id": f"{ticker}_{kind}_{op}_{value}_{int(datetime.datetime.now().timestamp())}",
        "ticker": ticker, "name": name, "kind": kind, "op": op,
        "value": float(value), "created": datetime.datetime.now().isoformat(),
        "triggered": False, "triggered_at": None, "last_val": None
    })
    save_alerts(alerts)

def delete_alert(alert_id: str):
    alerts = [a for a in load_alerts() if a["id"] != alert_id]
    save_alerts(alerts)

def evaluate_alerts(price_lookup):
    """price_lookup(ticker) → dict{price, rsi} or None. Returns list of newly-triggered alerts."""
    alerts = load_alerts()
    newly_triggered = []
    for a in alerts:
        if a.get("triggered"):
            continue
        data = price_lookup(a["ticker"])
        if not data:
            continue
        current = data.get("price") if a["kind"] == "price" else data.get("rsi")
        if current is None:
            continue
        a["last_val"] = float(current)
        trig = (a["op"] == ">" and current > a["value"]) or \
               (a["op"] == "<" and current < a["value"])
        if trig:
            a["triggered"] = True
            a["triggered_at"] = datetime.datetime.now().isoformat()
            newly_triggered.append(a)
    save_alerts(alerts)
    return newly_triggered

# ──────────────────────────────────────────────────────────────────────────
# 3. TRADE JOURNAL — CSV persistent
# ──────────────────────────────────────────────────────────────────────────
JOURNAL_COLS = ["Date", "Ticker", "Side", "Qty", "Entry", "Exit",
                "P&L (₹)", "P&L %", "Strategy", "Notes"]

def load_journal() -> pd.DataFrame:
    if JOURNAL_FILE.exists():
        try:
            df = pd.read_csv(JOURNAL_FILE)
            for c in JOURNAL_COLS:
                if c not in df.columns:
                    df[c] = ""
            return df[JOURNAL_COLS]
        except Exception:
            pass
    return pd.DataFrame(columns=JOURNAL_COLS)

def save_journal(df: pd.DataFrame):
    df.to_csv(JOURNAL_FILE, index=False)

# ──────────────────────────────────────────────────────────────────────────
# 4. AI ANALYST — emergentintegrations (Claude Sonnet 4.6)
# ──────────────────────────────────────────────────────────────────────────
def _get_llm_key() -> str:
    """Read LLM key from env var first, then Streamlit secrets (for cloud deploys)."""
    key = os.environ.get("EMERGENT_LLM_KEY")
    if key:
        return key
    try:
        return st.secrets["EMERGENT_LLM_KEY"]
    except Exception:
        return "sk-emergent-2191f894997De47509"

EMERGENT_LLM_KEY = _get_llm_key()

def _run_async(coro):
    """Run an async coroutine from sync Streamlit code."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)

def _build_context(ctx: dict) -> str:
    """Serialize stock analysis context into a compact string for the LLM."""
    lines = [
        f"Stock: {ctx.get('name')} ({ctx.get('ticker')})",
        f"Current Price: ₹{ctx.get('price', 0):,.2f}",
        f"1D Change: {ctx.get('change_1d', 0):+.2f}%",
        f"Signal: {ctx.get('signal', 'HOLD')} (Strength: {ctx.get('strength', 50)}/100)",
        f"RSI(14): {ctx.get('rsi', 50):.1f}",
        f"MACD: {ctx.get('macd', 0):.3f}  Signal: {ctx.get('macd_signal', 0):.3f}",
        f"SMA20: ₹{ctx.get('sma20', 0):,.2f}  SMA50: ₹{ctx.get('sma50', 0):,.2f}  SMA200: ₹{ctx.get('sma200', 0):,.2f}",
        f"ATR(14): ₹{ctx.get('atr', 0):,.2f}  Volatility(ann): {ctx.get('vol', 0)*100:.1f}%",
    ]
    if ctx.get("fundamentals"):
        f = ctx["fundamentals"]
        lines.append("Fundamentals: " + " | ".join(
            f"{k}: {v:.2f}" for k, v in f.items() if v is not None
        ))
    if ctx.get("news"):
        lines.append("Recent Headlines:")
        for h in ctx["news"][:5]:
            lines.append(f"  - {h}")
    return "\n".join(lines)

async def _ai_chat_async(session_id: str, user_prompt: str, context: dict, model: str = "claude-sonnet-4-6"):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    system_msg = (
        "You are XERCES AI — a sharp, concise, data-driven Indian equity market analyst. "
        "You explain technical signals, fundamentals, and news in plain English. "
        "You give balanced views (bull case + bear case), acknowledge uncertainty, "
        "and remind users this is analysis, not SEBI-registered advice. "
        "Format: use short paragraphs, ₹ for prices, and bullet points for lists. "
        "Never fabricate numbers — only use the provided context or user-supplied data."
    )
    provider = "anthropic" if model.startswith("claude") else ("gemini" if model.startswith("gemini") else "openai")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_msg,
    ).with_model(provider, model)

    ctx_str = _build_context(context) if context else ""
    full_prompt = (f"[LIVE CONTEXT]\n{ctx_str}\n\n[USER QUESTION]\n{user_prompt}"
                   if ctx_str else user_prompt)
    resp = await chat.send_message(UserMessage(text=full_prompt))
    return resp

def ai_chat(session_id: str, user_prompt: str, context: dict = None, model: str = "claude-sonnet-4-6") -> str:
    try:
        return _run_async(_ai_chat_async(session_id, user_prompt, context or {}, model))
    except Exception as e:
        return f"⚠️ AI Analyst error: {e}"

def ai_summarize_news(headlines: list, ticker: str, model: str = "claude-sonnet-4-6") -> str:
    if not headlines:
        return "No headlines to summarize."
    joined = "\n".join(f"- {h}" for h in headlines[:15])
    prompt = (
        f"Summarize the following recent headlines for {ticker} into 3 crisp bullets: "
        f"(1) Overall narrative, (2) Bullish signals, (3) Bearish/risk signals. "
        f"Also give a one-line impact rating: STRONG BULLISH / MILD BULLISH / NEUTRAL / MILD BEARISH / STRONG BEARISH.\n\n"
        f"HEADLINES:\n{joined}"
    )
    return ai_chat(f"news_{ticker}", prompt, context={}, model=model)

def ai_trade_thesis(context: dict, model: str = "claude-sonnet-4-6") -> str:
    prompt = (
        "Write a concise 1-page TRADE THESIS for this stock. Include:\n"
        "1. Setup (what the technicals + fundamentals say)\n"
        "2. Entry / Stop / Target (use ATR-based rationale)\n"
        "3. Bull Case (3 bullets)\n"
        "4. Bear Case (3 bullets)\n"
        "5. Position sizing suggestion (use 1-2% risk)\n"
        "6. Time horizon (short/medium/long)\n"
        "End with a clear rating: STRONG BUY / BUY / HOLD / SELL / STRONG SELL."
    )
    return ai_chat(f"thesis_{context.get('ticker','X')}", prompt, context, model)

# ──────────────────────────────────────────────────────────────────────────
# 5. SECTOR HEATMAP
# ──────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def compute_sector_performance(sectors_dict: dict, max_per_sector: int = 6) -> pd.DataFrame:
    """Compute avg 1-day return per sector from a sample of stocks."""
    rows = []
    for sector, stocks in sectors_dict.items():
        tickers = [f"{s}.NS" for _, s in stocks[:max_per_sector]]
        try:
            df = yf.download(tickers, period="5d", interval="1d",
                             auto_adjust=True, progress=False, timeout=15,
                             group_by="ticker", threads=True)
            if df is None or df.empty:
                continue
            perf = []
            for t in tickers:
                try:
                    if isinstance(df.columns, pd.MultiIndex):
                        if t in df.columns.get_level_values(0):
                            sub = df[t]
                        elif t in df.columns.get_level_values(1):
                            sub = df.xs(t, axis=1, level=1)
                        else:
                            continue
                    else:
                        sub = df
                    cl = sub["Close"].dropna()
                    if len(cl) >= 2:
                        chg = (float(cl.iloc[-1]) - float(cl.iloc[-2])) / float(cl.iloc[-2]) * 100
                        perf.append(chg)
                except Exception:
                    continue
            if perf:
                rows.append({"Sector": sector, "Avg 1D %": round(float(np.mean(perf)), 2),
                             "Best %": round(float(np.max(perf)), 2),
                             "Worst %": round(float(np.min(perf)), 2),
                             "Stocks Sampled": len(perf)})
        except Exception:
            continue
    return pd.DataFrame(rows).sort_values("Avg 1D %", ascending=False) if rows else pd.DataFrame()

# ──────────────────────────────────────────────────────────────────────────
# 6. COMPARE — correlation + normalized returns
# ──────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def compare_stocks(tickers: list, period: str = "1y") -> tuple:
    """Returns (normalized_df, correlation_matrix, stats_df)"""
    if not tickers or len(tickers) < 2:
        return None, None, None
    try:
        df = yf.download(tickers, period=period, interval="1d",
                         auto_adjust=True, progress=False, timeout=15,
                         group_by="ticker", threads=True)
        if df is None or df.empty:
            return None, None, None
        close = {}
        for t in tickers:
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    if t in df.columns.get_level_values(0):
                        close[t] = df[t]["Close"].dropna()
                    elif t in df.columns.get_level_values(1):
                        close[t] = df.xs(t, axis=1, level=1)["Close"].dropna()
                else:
                    close[t] = df["Close"].dropna()
            except Exception:
                continue
        if len(close) < 2:
            return None, None, None
        close_df = pd.DataFrame(close).dropna()
        if close_df.empty:
            return None, None, None
        # Normalize each series to 100 at start
        norm_df = close_df.divide(close_df.iloc[0]).multiply(100)
        returns = close_df.pct_change().dropna()
        corr = returns.corr().round(3)
        stats = pd.DataFrame({
            "Return %":  ((close_df.iloc[-1] / close_df.iloc[0]) - 1) * 100,
            "Volatility (ann)": returns.std() * np.sqrt(252) * 100,
            "Sharpe (0% rf)": (returns.mean() * 252) / (returns.std() * np.sqrt(252) + 1e-9),
            "Max Drawdown %": ((close_df / close_df.cummax() - 1).min()) * 100,
        }).round(2)
        return norm_df, corr, stats
    except Exception:
        return None, None, None

# ──────────────────────────────────────────────────────────────────────────
# 7. INTRADAY 5-min chart
# ──────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_intraday(ticker: str, interval: str = "5m", period: str = "5d"):
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False, timeout=10)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return None

# ──────────────────────────────────────────────────────────────────────────
# 8. PDF REPORT
# ──────────────────────────────────────────────────────────────────────────
def build_pdf_report(ctx: dict, thesis_text: str = "", news_summary: str = "") -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                     TableStyle, PageBreak)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1x", fontName="Helvetica-Bold", fontSize=22,
                              textColor=colors.HexColor("#00c8ff"), spaceAfter=6))
    styles.add(ParagraphStyle(name="H2x", fontName="Helvetica-Bold", fontSize=13,
                              textColor=colors.HexColor("#0a5ea6"),
                              spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle(name="Bodyx", fontName="Helvetica", fontSize=10,
                              leading=13, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="Metax", fontName="Helvetica-Oblique", fontSize=8,
                              textColor=colors.HexColor("#666666")))

    story = []
    story.append(Paragraph(f"XERCES // {ctx.get('name','')} ({ctx.get('ticker','')})", styles["H1x"]))
    story.append(Paragraph(
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M IST')} · "
        f"Signal: <b>{ctx.get('signal','HOLD')}</b> · Strength: {ctx.get('strength',50)}/100",
        styles["Metax"]))
    story.append(Spacer(1, 0.4*cm))

    # KPI table
    kpi_rows = [
        ["Current Price", f"Rs {ctx.get('price', 0):,.2f}"],
        ["1D Change",     f"{ctx.get('change_1d', 0):+.2f}%"],
        ["RSI(14)",       f"{ctx.get('rsi', 50):.1f}"],
        ["MACD",          f"{ctx.get('macd', 0):.3f}"],
        ["SMA 20 / 50 / 200",
         f"Rs {ctx.get('sma20',0):,.0f} / Rs {ctx.get('sma50',0):,.0f} / Rs {ctx.get('sma200',0):,.0f}"],
        ["ATR(14)",       f"Rs {ctx.get('atr', 0):,.2f}"],
        ["Annual Volatility", f"{ctx.get('vol', 0)*100:.1f}%"],
    ]
    t = Table(kpi_rows, colWidths=[5*cm, 11*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eef6ff")),
        ("TEXTCOLOR",  (0,0), (0,-1), colors.HexColor("#0a5ea6")),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",   (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("GRID",       (0,0), (-1,-1), 0.25, colors.HexColor("#d0dbe6")),
        ("ROWBACKGROUNDS", (1,0), (1,-1), [colors.white, colors.HexColor("#f7fafd")]),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
    ]))
    story.append(t)

    if ctx.get("fundamentals"):
        story.append(Paragraph("Fundamentals", styles["H2x"]))
        rows = [[k, f"{v:.2f}" if v is not None else "N/A"]
                for k, v in ctx["fundamentals"].items()]
        ft = Table(rows, colWidths=[6*cm, 10*cm])
        ft.setStyle(TableStyle([
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",  (0,0), (-1,-1), 9),
            ("GRID",      (0,0), (-1,-1), 0.25, colors.HexColor("#d0dbe6")),
        ]))
        story.append(ft)

    if thesis_text:
        story.append(Paragraph("AI Trade Thesis", styles["H2x"]))
        for para in thesis_text.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.replace("\n", "<br/>"), styles["Bodyx"]))
                story.append(Spacer(1, 0.15*cm))

    if news_summary:
        story.append(Paragraph("News Summary", styles["H2x"]))
        story.append(Paragraph(news_summary.replace("\n", "<br/>"), styles["Bodyx"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        "Disclaimer: XERCES is a research and analysis tool. Not SEBI registered. "
        "Not investment advice. Please consult a qualified advisor before trading.",
        styles["Metax"]))

    doc.build(story)
    return buf.getvalue()

# ──────────────────────────────────────────────────────────────────────────
# 9. EXCEL EXPORT
# ──────────────────────────────────────────────────────────────────────────
def build_excel_bytes(sheets: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()
