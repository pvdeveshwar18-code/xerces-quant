"""
Integrations Hub for Open-Source Financial & Quant Trading Frameworks.
Provides references, API connection wrappers, and integration architecture for Xerces.
"""

OPEN_SOURCE_FRAMEWORKS = [
    {
        "name": "HKUDS Vibe-Trading",
        "category": "Multi-Agent AI & Alpha Factors",
        "github": "https://github.com/HKUDS/Vibe-Trading",
        "license": "Open Source",
        "features": [
            "Swarm of specialized AI agents (Macro, Quant, Risk, Catalyst)",
            "Alpha Zoo containing 450+ quantitative factors",
            "Shadow Account behavioral trade diagnostics",
            "Model Context Protocol (MCP) server support"
        ],
        "xerces_role": "Upstream AI Strategy Copilot & Factor Mining Engine",
        "command": "git clone https://github.com/HKUDS/Vibe-Trading && pip install -e ."
    },
    {
        "name": "OpenBB SDK",
        "category": "Market Data & Financial Intelligence",
        "github": "https://github.com/OpenBB-finance/OpenBB",
        "license": "AGPL-3.0",
        "features": [
            "Unified Python API connecting 100+ financial data providers",
            "Fundamental analysis, macro indicators, and option chains",
            "Terminal UI & Python SDK for seamless data feeding"
        ],
        "xerces_role": "Primary Market Data Provider & Financial Terminal Backend",
        "command": "pip install openbb"
    },
    {
        "name": "Microsoft Qlib",
        "category": "AI-Oriented Quant Platform",
        "github": "https://github.com/microsoft/qlib",
        "license": "MIT",
        "features": [
            "Full-pipeline quantitative ML & data processing engine",
            "Market dynamics modeling & neural network backtesting",
            "High-performance C++ data format for rapid factor computation"
        ],
        "xerces_role": "Machine Learning Model Training & Historical Backtesting",
        "command": "pip install pyqlib"
    },
    {
        "name": "FinRL & FinGPT (AI4Finance)",
        "category": "Deep RL & Financial LLM Sentiment",
        "github": "https://github.com/AI4Finance-Foundation/FinRL",
        "license": "MIT",
        "features": [
            "Deep Reinforcement Learning trading environments (DDPG, PPO, SAC)",
            "Financial sentiment scoring from news feeds and SEC filings",
            "Real-time market simulation gym environments"
        ],
        "xerces_role": "Reinforcement Learning Agent Training & Sentiment Ingestion",
        "command": "pip install finrl fingpt"
    },
    {
        "name": "NautilusTrader",
        "category": "High-Performance Execution Engine",
        "github": "https://github.com/nautechsystems/nautilus_trader",
        "license": "LGPL-3.0",
        "features": [
            "Event-driven Rust-core backtesting and live trading engine",
            "Sub-millisecond latency for order routing and risk management",
            "Native support for FIX protocol and Crypto exchanges (CCXT)"
        ],
        "xerces_role": "Institutional High-Frequency Execution & Low-Latency Routing",
        "command": "pip install nautilus_trader"
    }
]

def get_framework_integrations() -> list:
    """Returns the list of integrated open-source sources."""
    return OPEN_SOURCE_FRAMEWORKS
