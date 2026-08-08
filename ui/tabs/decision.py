"""
XERCES Decision & Signal Engine Tab Module
Includes ML Signal Classifier (Random Forest / XGBoost with AutoML & Model Persistence), Institutional Decision Engine, AI Committee, Strategy Lab, and Relative Strength.
"""

import streamlit as st
import plotly.express as px
import institutional_ui as inst_ui
from ai_committee.ml_classifier import MLSignalClassifier

def render_decision_tab(df, ticker: str, selected_name: str, fundamentals=None):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 ML SIGNAL CLASSIFIER", "🎯 DECISION ENGINE", "🏛️ AI COMMITTEE VOTE", "🧪 STRATEGY LAB", "📈 RELATIVE STRENGTH"
    ])

    with tab1:
        st.subheader(f"🤖 Machine Learning Signal Classifier — {selected_name} ({ticker})")
        st.caption("Multi-factor Random Forest & XGBoost classifier with AutoML hyperparameter tuning & disk model persistence.")

        m1, m2, m3 = st.columns([2, 1, 1])
        with m1:
            model_choice = st.radio("ML Model Architecture", ["Ensemble (XGBoost + RF)", "Random Forest", "XGBoost"], horizontal=True)

        with m2:
            st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Train & Run Classifier", use_container_width=True):
                with st.spinner("Training multi-factor ML classifier and scoring probability distribution..."):
                    ml_res = MLSignalClassifier.train_and_predict(df, model_type=model_choice, use_disk_cache=False)
                    st.session_state["_last_ml_res"] = ml_res

        with m3:
            st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
            if st.button("⚡ Run AutoML Tuning", use_container_width=True):
                with st.spinner("Running RandomizedSearchCV hyperparameter optimization across grid..."):
                    ml_res = MLSignalClassifier.train_and_predict(df, model_type=model_choice, use_automl=True, use_disk_cache=False)
                    st.session_state["_last_ml_res"] = ml_res
                    st.success("AutoML Hyperparameter optimization complete! Model saved to disk.")

        ml_res = st.session_state.get("_last_ml_res")
        if not ml_res:
            with st.spinner("Initializing ML signal evaluation..."):
                ml_res = MLSignalClassifier.train_and_predict(df)
                st.session_state["_last_ml_res"] = ml_res

        if ml_res.get("error"):
            st.error(ml_res["error"])
        else:
            c1, c2, c3, c4 = st.columns(4)
            sig = ml_res["signal"]
            sig_clr = "#00e87a" if sig == "BUY" else "#ff3355" if sig == "SELL" else "#ffcc00"
            c1.markdown(f'<div class="glass-card"><p class="glass-label">ML Predicted Signal</p><div class="glass-value" style="color:{sig_clr};">{sig}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="glass-card"><p class="glass-label">Signal Confidence</p><div class="glass-value" style="color:#00c8ff;">{ml_res["confidence"]}%</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="glass-card"><p class="glass-label">Model Accuracy (Test)</p><div class="glass-value" style="color:#00e87a;">{ml_res["accuracy"]}%</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="glass-card"><p class="glass-label">Engine Architecture</p><div class="glass-value" style="font-size:0.95rem;color:#ddeeff;">{ml_res["model_used"]}</div></div>', unsafe_allow_html=True)

            # Probabilities distribution
            p1, p2, p3 = st.columns(3)
            p1.metric("BUY Probability", f"{ml_res['buy_prob']}%")
            p2.metric("HOLD Probability", f"{ml_res['hold_prob']}%")
            p3.metric("SELL Probability", f"{ml_res['sell_prob']}%")

            col_fi, col_flags = st.columns([2, 1])
            with col_fi:
                fi_df = ml_res["feature_importances"]
                if not fi_df.empty:
                    fig_fi = px.bar(
                        fi_df.head(10), x="Importance", y="Feature", orientation="h",
                        title="Top Technical Feature Importances",
                        color="Importance", color_continuous_scale="Viridis"
                    )
                    fig_fi.update_layout(template="plotly_dark", height=320, yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_fi, use_container_width=True)

            with col_flags:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("<p class='glass-label'>Squeeze & Divergence Detector</p>", unsafe_allow_html=True)
                sq = "🔥 ACTIVE (Volatility Expansion Imminent)" if ml_res["squeeze_active"] else "⚪ Normal Volatility"
                div = "⚡ ACTIVE RSI Divergence" if ml_res["divergence_active"] else "⚪ No Divergence"
                st.markdown(f"**Bollinger Squeeze:** {sq}")
                st.markdown(f"**RSI Divergence:** {div}")
                st.markdown("---")
                st.caption("💾 Model weights automatically persisted to `models/ml_signal_classifier.joblib` for instant stock scanning.")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        inst_ui.render_decision_engine_tab(df, ticker=ticker, fundamentals=fundamentals)

    with tab3:
        inst_ui.render_ai_committee_tab(ticker=ticker, df=df, fundamentals=fundamentals)

    with tab4:
        inst_ui.render_strategy_lab_tab(df, ticker=ticker)

    with tab5:
        st.subheader("📈 Mansfield Relative Strength (MRS)")
        rs_res = inst_ui.RelativeStrengthEngine.calculate_relative_strength(df, benchmark_symbol="^NSEI")
        r_c1, r_c2 = st.columns(2)
        r_c1.metric("Mansfield RS", f"{rs_res.get('mrs'):+.2f}%", f"Status: {rs_res.get('rs_status')}")
        r_c2.metric("Outperformance vs NIFTY 50", f"{rs_res.get('outperformance_pct'):+.2f}%")
        st.info(f"Asset is **{rs_res.get('rs_status')}** with trend: **{rs_res.get('rs_trend')}**.")
