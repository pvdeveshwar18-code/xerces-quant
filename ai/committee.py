import os
import streamlit as st
from utils.helpers import sentiment_score

# Pull helper chat functions from original xerces_plus or implement directly to avoid circular dependency
def _get_llm_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if key: return key
    try: return st.secrets["EMERGENT_LLM_KEY"]
    except Exception: return ""

def _get_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if key: return key
    try: return st.secrets["GEMINI_API_KEY"]
    except Exception: return ""

# Last backend metadata tracking
_LAST_BACKEND = {"name": "none", "model": "none", "reason": ""}

def get_last_backend() -> dict:
    return dict(_LAST_BACKEND)

def _is_quota_or_rate_error(err: Exception) -> bool:
    msg = str(err).lower()
    return any(k in msg for k in ["quota", "rate limit", "resource_exhausted", "429", "exceeded", "daily limit", "too many requests"])

def _build_context(ctx: dict) -> str:
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
        lines.append("Fundamentals: " + " | ".join(f"{k}: {v:.2f}" for k, v in f.items() if v is not None))
    if ctx.get("news"):
        lines.append("Recent Headlines:")
        for h in ctx["news"][:5]:
            lines.append(f"  - {h}")
    return "\n".join(lines)

_SYSTEM_MSG = (
    "You are XERCES AI — a sharp, concise, data-driven Indian equity market analyst. "
    "You explain technical signals, fundamentals, and news in plain English. "
    "You give balanced views, acknowledge uncertainty, and remind users this is not financial advice."
)

def _gemini_chat(session_id: str, user_prompt: str, context: dict, model_name: str = "gemini-2.5-flash") -> str:
    if not _get_gemini_key():
        raise RuntimeError("GEMINI_API_KEY not set")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=_get_gemini_key())
    ctx_str = _build_context(context) if context else ""
    full_prompt = f"[LIVE CONTEXT]\n{ctx_str}\n\n[USER QUESTION]\n{user_prompt}" if ctx_str else user_prompt
    resp = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_MSG,
            temperature=0.7,
        ),
    )
    return resp.text or ""

def _emergent_chat(session_id: str, user_prompt: str, context: dict, model: str = "claude-sonnet-4-6") -> str:
    import asyncio
    import nest_asyncio
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    async def run_chat():
        provider = "anthropic" if model.startswith("claude") else ("gemini" if model.startswith("gemini") else "openai")
        chat = LlmChat(
            api_key=_get_llm_key(),
            session_id=session_id,
            system_message=_SYSTEM_MSG,
        ).with_model(provider, model)
        ctx_str = _build_context(context) if context else ""
        full_prompt = f"[LIVE CONTEXT]\n{ctx_str}\n\n[USER QUESTION]\n{user_prompt}" if ctx_str else user_prompt
        return await chat.send_message(UserMessage(text=full_prompt))

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            nest_asyncio.apply()
            return loop.run_until_complete(run_chat())
    except RuntimeError:
        pass
    return asyncio.run(run_chat())

def ai_chat(session_id: str, user_prompt: str, context: dict = None, model: str = "auto") -> str:
    ctx = context or {}
    gemini_key = _get_gemini_key()
    emergent_key = _get_llm_key()

    if model.startswith(("claude", "gpt")) or model == "gemini-3-flash-preview":
        try:
            out = _emergent_chat(session_id, user_prompt, ctx, model)
            _LAST_BACKEND.update({"name": "Emergent", "model": model, "reason": "forced"})
            return out
        except Exception as e:
            _LAST_BACKEND.update({"name": "error", "model": model, "reason": str(e)})
            return f"⚠️ AI Analyst error: {e}"

    if model.startswith("gemini-2"):
        try:
            out = _gemini_chat(session_id, user_prompt, ctx, model)
            _LAST_BACKEND.update({"name": "Gemini (FREE)", "model": model, "reason": "forced"})
            return out
        except Exception as e:
            _LAST_BACKEND.update({"name": "error", "model": model, "reason": str(e)})
            return f"⚠️ Gemini error: {e}"

    # Auto Cascade
    if gemini_key:
        try:
            out = _gemini_chat(session_id, user_prompt, ctx, "gemini-2.5-flash")
            _LAST_BACKEND.update({"name": "Gemini (FREE)", "model": "gemini-2.5-flash", "reason": "primary"})
            return out
        except Exception as e:
            if _is_quota_or_rate_error(e):
                try:
                    out = _emergent_chat(session_id, user_prompt, ctx, "claude-sonnet-4-6")
                    _LAST_BACKEND.update({"name": "Emergent (backup)", "model": "claude-sonnet-4-6", "reason": "Gemini quota exceeded → fallback"})
                    return out
                except Exception as e2:
                    _LAST_BACKEND.update({"name": "error", "model": "both failed", "reason": f"{e} | {e2}"})
                    return f"⚠️ Both backends failed. Gemini: {e}. Emergent: {e2}"
            _LAST_BACKEND.update({"name": "error", "model": "gemini-2.5-flash", "reason": str(e)})
            return f"⚠️ Gemini error (not quota): {e}"
            
    if not emergent_key:
        _LAST_BACKEND.update({"name": "error", "model": "none", "reason": "no API keys"})
        return "⚠️ AI Analyst unavailable. Set GEMINI_API_KEY or EMERGENT_LLM_KEY."

    try:
        out = _emergent_chat(session_id, user_prompt, ctx, "claude-sonnet-4-6")
        _LAST_BACKEND.update({"name": "Emergent", "model": "claude-sonnet-4-6", "reason": "no GEMINI_API_KEY set"})
        return out
    except Exception as e:
        _LAST_BACKEND.update({"name": "error", "model": "emergent", "reason": str(e)})
        return f"⚠️ AI Analyst error: {e}"

# ── Phase 7: AI Investment Committee ──
def run_investment_committee(context: dict, model: str = "auto") -> str:
    """
    Run simulated AI Investment Committee featuring 5 independent analysts:
    Value, Growth, Technical, Macro, and Risk.
    """
    prompt = (
        "Act as the XERCES AI Investment Committee, composed of 5 independent Wall Street/Dalal Street analysts:\n"
        "1. **Value Analyst**: Evaluates fundamentals like P/E, P/B, ROE, ROCE, Debt/Equity, and Dividend Yield. Looks for margin of safety.\n"
        "2. **Growth Analyst**: Evaluates trend strength, EPS/price momentum, potential for multi-bagger scale expansion.\n"
        "3. **Technical Analyst**: Evaluates moving averages (20/50/200 SMA), RSI, MACD, support/resistance, volume action.\n"
        "4. **Macro & Flow Analyst**: Evaluates sector index trend, general indices (NIFTY 50), institutional (FII/DII) flows and market structure.\n"
        "5. **Risk Analyst**: Evaluates volatility, drawdown, ATR-based protection, and exposure checks.\n\n"
        "Please read the provided stock context carefully and generate a discussion meeting transcript. Format your response exactly as follows:\n\n"
        "### 🏛️ XERCES AI Investment Committee Proceedings\n\n"
        "#### 1. Analyst Reports\n"
        "- **Value Analyst Report**: [Report and Vote: STRONG BUY / BUY / HOLD / SELL / STRONG SELL]\n"
        "- **Growth Analyst Report**: [Report and Vote]\n"
        "- **Technical Analyst Report**: [Report and Vote]\n"
        "- **Macro & Flow Analyst Report**: [Report and Vote]\n"
        "- **Risk Analyst Report**: [Report and Vote]\n\n"
        "#### 2. Committee Tally & Final Verdict\n"
        "- **Vote Tally**: [e.g., 3 BUY, 1 HOLD, 1 SELL]\n"
        "- **Final Committee Consensus**: [STRONG BUY / BUY / HOLD / SELL / STRONG SELL]\n"
        "- **Key Discussion Synthesis**: [Summarize the debate, noting any major disagreements or caveats]"
    )
    ticker = context.get("ticker", "Stock")
    return ai_chat(f"committee_{ticker}", prompt, context, model)
