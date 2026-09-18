import datetime
import pytz
import io
import json
import pandas as pd

IST = pytz.timezone("Asia/Kolkata")

BULL_KW = {"surge", "rally", "grow", "growth", "jump", "rise", "gain", "profit", "record", "bullish", "beat",
           "positive", "expand", "outperform", "buy", "upgrade", "strong", "boom", "breakout", "upside"}
BEAR_KW = {"slump", "fall", "decline", "drop", "loss", "plunge", "negative", "bearish", "miss", "sell",
           "downgrade", "weak", "crash", "warn", "crisis", "debt", "cut", "lower", "pressure", "concern"}

def ist_now() -> datetime.datetime:
    """Get the current time in IST (Indian Standard Time)."""
    return datetime.datetime.now(IST)

def market_status() -> tuple[str, str]:
    """Check if the Indian stock market (NSE) is currently open. Returns (status_text, hex_color)."""
    now = ist_now()
    if now.weekday() >= 5:
        return "🔴 NSE CLOSED", "#ff3355"
    ot = now.replace(hour=9, minute=15, second=0, microsecond=0)
    ct = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if ot <= now <= ct:
        return "🟢 NSE OPEN", "#00e87a"
    return "🔴 NSE CLOSED", "#ff3355"

def sentiment_score(items: list) -> tuple[float, str]:
    """Calculate average news sentiment score based on keyword matching."""
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

def build_pdf_report(ctx: dict, thesis_text: str = "", news_summary: str = "") -> bytes:
    """Generate a PDF report using reportlab for a specific stock."""
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
    
    # Custom Styles
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

def build_excel_bytes(sheets: dict) -> bytes:
    """Generate a multi-sheet Excel file from pandas dataframes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()
