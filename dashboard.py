import os
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

try:
    from alpaca.trading.client import TradingClient
except Exception:
    TradingClient = None


# ============================================================
# ALPHAPILOT AI — SIMPLE PROFESSIONAL DASHBOARD
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="AlphaPilot AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRADE_HISTORY = BASE_DIR / "agents" / "trade_history.csv"
TRADE_LOG = BASE_DIR / "logs" / "trades.csv"


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* =========================
       MAIN APP
       ========================= */

    .stApp {
        background: #0b1220;
        color: #f8fafc;
    }

    .main .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }


    /* =========================
       SIDEBAR
       ========================= */

    section[data-testid="stSidebar"] {
        background: #111827 !important;
        border-right: 1px solid #263244 !important;
    }

    section[data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }

    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #e2e8f0 !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #334155 !important;
    }

    /* Sidebar success box */
    section[data-testid="stSidebar"] div[data-testid="stAlert"] {
        background: #10251d !important;
        border: 1px solid #1f6047 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stAlert"] * {
        color: #6ee7b7 !important;
    }


    /* =========================
       HEADER
       ========================= */

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
    }

    .brand {
        font-size: 38px;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: -1px;
    }

    .brand-accent {
        color: #60a5fa !important;
    }

    .tagline {
        margin-top: 5px;
        color: #cbd5e1 !important;
        font-size: 14px;
    }

    .online {
        background: #10251d;
        border: 1px solid #1f6047;
        color: #6ee7b7 !important;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }


    /* =========================
       SECTION TITLES
       ========================= */

    .section-title {
        color: #ffffff !important;
        font-size: 22px;
        font-weight: 800;
        margin-top: 25px;
        margin-bottom: 4px;
    }

    .section-subtitle {
        color: #94a3b8 !important;
        font-size: 13px;
        margin-bottom: 16px;
    }


    /* =========================
       METRIC CARDS
       ========================= */

    .metric-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 12px;
        padding: 20px;
        min-height: 125px;
    }

    .metric-label {
        color: #94a3b8 !important;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .5px;
    }

    .metric-value {
        color: #ffffff !important;
        font-size: 28px;
        font-weight: 800;
        margin-top: 8px;
    }

    .metric-sub {
        color: #64748b !important;
        font-size: 12px;
        margin-top: 5px;
    }


    /* =========================
       PIPELINE
       ========================= */

    .pipeline-box {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 12px;
        padding: 18px;
        overflow-x: auto;
    }

    .pipeline {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 900px;
    }

    .pipeline-step {
        background: #172033;
        border: 1px solid #334155;
        color: #e2e8f0 !important;
        border-radius: 9px;
        padding: 12px 14px;
        min-width: 120px;
        text-align: center;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.5;
    }

    .pipeline-arrow {
        color: #64748b !important;
        font-size: 18px;
    }


    /* =========================
       STATUS CARDS
       ========================= */

    .status-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 12px;
        padding: 20px;
        min-height: 180px;
    }

    .status-title {
        color: #ffffff !important;
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 14px;
    }

    .status-text {
        color: #cbd5e1 !important;
        font-size: 13px;
        line-height: 1.8;
    }

    .blue {
        color: #60a5fa !important;
        font-weight: 800;
    }

    .green {
        color: #34d399 !important;
        font-weight: 800;
    }

    .yellow {
        color: #fbbf24 !important;
        font-weight: 800;
    }


    /* =========================
       EMPTY POSITION
       ========================= */

    .empty-position {
        background: #111827;
        border: 1px dashed #475569;
        border-radius: 12px;
        padding: 35px;
        text-align: center;
    }

    .empty-title {
        color: #ffffff !important;
        font-size: 17px;
        font-weight: 800;
    }

    .empty-text {
        color: #94a3b8 !important;
        font-size: 13px;
        margin-top: 6px;
    }


    /* =========================
       BUTTON
       ========================= */

    .stButton > button {
        width: 100%;
        background: #172033 !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
        font-weight: 700;
    }

    .stButton > button:hover {
        border-color: #60a5fa !important;
        color: #60a5fa !important;
    }


    /* =========================
       DATAFRAME
       ========================= */

    [data-testid="stDataFrame"] {
        border: 1px solid #263244;
        border-radius: 10px;
        overflow: hidden;
    }


    /* =========================
       STREAMLIT TEXT
       ========================= */

    .stMarkdown,
    .stText,
    p {
        color: #e2e8f0;
    }


    /* =========================
       FOOTER
       ========================= */

    .footer {
        border-top: 1px solid #263244;
        margin-top: 35px;
        padding-top: 20px;
        text-align: center;
        color: #64748b !important;
        font-size: 12px;
        line-height: 1.8;
    }


    /* =========================
       HIDE DEFAULT MENU
       ========================= */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns([7, 2])

with header_left:

    st.markdown(
        """
        <div class="brand">
            🚀 <span class="brand-accent">AlphaPilot</span> AI
        </div>

        <div class="tagline">
            AI-Powered Paper Trading & Options Monitoring System
        </div>
        """,
        unsafe_allow_html=True,
    )


with header_right:

    st.markdown(
        """
        <div style="text-align:right; margin-top:10px;">
            <span class="online">
                ● PAPER SYSTEM ONLINE
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-size:25px;
            font-weight:800;
            color:#ffffff;
            margin-bottom:3px;
        ">
            🚀 AlphaPilot AI
        </div>

        <div style="
            color:#cbd5e1;
            font-size:12px;
            margin-bottom:20px;
        ">
            Trading Control Center
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("### 🟢 System Status")

    st.success("SYSTEM ONLINE")

    st.markdown(
        """
        <div style="
            background:#172033;
            border:1px solid #334155;
            border-radius:9px;
            padding:13px;
            margin-top:10px;
            margin-bottom:20px;
        ">

            <div style="
                color:#94a3b8;
                font-size:11px;
                text-transform:uppercase;
                font-weight:700;
            ">
                Trading Environment
            </div>

            <div style="
                color:#ffffff;
                font-size:14px;
                font-weight:800;
                margin-top:6px;
            ">
                🧪 PAPER TRADING
            </div>

            <div style="
                color:#94a3b8;
                font-size:11px;
                margin-top:5px;
            ">
                No real money is being used.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🔄 Trading Pipeline")

    st.markdown(
        """
        <div style="
            color:#e2e8f0;
            font-size:13px;
            line-height:2.2;
        ">

        <b style="color:#60a5fa;">01</b>
        📊 Market Analysis

        <br>

        <b style="color:#60a5fa;">02</b>
        🤖 AI Signal

        <br>

        <b style="color:#60a5fa;">03</b>
        ⚙️ Options Selection

        <br>

        <b style="color:#60a5fa;">04</b>
        🛡️ Risk Checks

        <br>

        <b style="color:#60a5fa;">05</b>
        💹 Paper Entry

        <br>

        <b style="color:#60a5fa;">06</b>
        👁️ Position Monitoring

        <br>

        <b style="color:#60a5fa;">07</b>
        🚪 Exit

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    if st.button("🔄 Refresh Dashboard"):
        st.rerun()

    st.markdown("---")

    st.caption("AlphaPilot AI v1.0")
    st.caption("Paper Trading Environment")


# ============================================================
# CSV LOADER
# ============================================================

def load_csv(path):

    try:

        if not path.exists():
            return pd.DataFrame()

        return pd.read_csv(path)

    except Exception as e:

        st.warning(f"Unable to read {path.name}: {e}")

        return pd.DataFrame()


trade_history = load_csv(TRADE_HISTORY)
trade_log = load_csv(TRADE_LOG)


# ============================================================
# TRADE DATA
# ============================================================

if not trade_history.empty:
    trades = trade_history.copy()

elif not trade_log.empty:
    trades = trade_log.copy()

else:
    trades = pd.DataFrame()


# ============================================================
# ALPACA CONNECTION
# ============================================================

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

trading_client = None

if TradingClient is not None and API_KEY and SECRET_KEY:

    try:

        trading_client = TradingClient(
            API_KEY,
            SECRET_KEY,
            paper=True,
        )

    except Exception:

        trading_client = None


# ============================================================
# ACCOUNT
# ============================================================

account = None
positions = []

if trading_client:

    try:
        account = trading_client.get_account()
    except Exception:
        account = None

    try:
        positions = trading_client.get_all_positions()
    except Exception:
        positions = []


# ============================================================
# EQUITY
# ============================================================

equity_value = None

if account:

    try:
        equity_value = float(account.equity)
    except Exception:
        equity_value = None


# ============================================================
# TRADING OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-title">📡 Trading Overview</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Real-time overview of the AlphaPilot paper-trading environment'
    '</div>',
    unsafe_allow_html=True,
)


m1, m2, m3, m4 = st.columns(4)


with m1:

    st.markdown(
        """
        <div class="metric-card">

            <div class="metric-label">
                Trading Mode
            </div>

            <div class="metric-value">
                PAPER
            </div>

            <div class="metric-sub">
                Risk-free simulation
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with m2:

    equity_text = (
        f"${equity_value:,.2f}"
        if equity_value is not None
        else "N/A"
    )

    st.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-label">
                Account Equity
            </div>

            <div class="metric-value">
                {equity_text}
            </div>

            <div class="metric-sub">
                Alpaca paper account
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with m3:

    st.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-label">
                Open Positions
            </div>

            <div class="metric-value">
                {len(positions)}
            </div>

            <div class="metric-sub">
                Active positions
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with m4:

    st.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-label">
                Completed Trades
            </div>

            <div class="metric-value">
                {len(trades)}
            </div>

            <div class="metric-sub">
                Recorded executions
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PIPELINE
# ============================================================

st.markdown(
    '<div class="section-title">🔄 AlphaPilot Pipeline</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'End-to-end automated trading workflow'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="pipeline-box">

        <div class="pipeline">

            <div class="pipeline-step">
                📊<br>
                Market Analysis
            </div>

            <div class="pipeline-arrow">→</div>

            <div class="pipeline-step">
                🤖<br>
                AI Signal
            </div>

            <div class="pipeline-arrow">→</div>

            <div class="pipeline-step">
                ⚙️<br>
                Options Selection
            </div>

            <div class="pipeline-arrow">→</div>

            <div class="pipeline-step">
                🛡️<br>
                Risk Checks
            </div>

            <div class="pipeline-arrow">→</div>

            <div class="pipeline-step">
                💹<br>
                Paper Entry
            </div>

            <div class="pipeline-arrow">→</div>

            <div class="pipeline-step">
                👁️<br>
                Monitoring
            </div>

            <div class="pipeline-arrow">→</div>

            <div class="pipeline-step">
                🚪<br>
                Exit
            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CURRENT POSITION
# ============================================================

st.markdown(
    '<div class="section-title">📊 Current Position</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Live position information from the Alpaca paper account'
    '</div>',
    unsafe_allow_html=True,
)


if positions:

    position_rows = []

    for position in positions:

        try:

            position_rows.append(
                {
                    "Symbol": str(position.symbol),
                    "Qty": float(position.qty),
                    "Entry": f"${float(position.avg_entry_price):.2f}",
                    "Current": f"${float(position.current_price):.2f}",
                    "Market Value": f"${float(position.market_value):,.2f}",
                    "Unrealized P&L": f"${float(position.unrealized_pl):,.2f}",
                    "P&L %": f"{float(position.unrealized_plpc) * 100:.2f}%",
                }
            )

        except Exception:
            continue

    if position_rows:

        st.dataframe(
            pd.DataFrame(position_rows),
            width="stretch",
            hide_index=True,
        )

    else:

        st.markdown(
            """
            <div class="empty-position">

                <div class="empty-title">
                    ⚠️ Position Data Unavailable
                </div>

                <div class="empty-text">
                    Alpaca returned a position but
                    the details could not be displayed.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

else:

    st.markdown(
        """
        <div class="empty-position">

            <div class="empty-title">
                📭 No Open Positions
            </div>

            <div class="empty-text">
                AlphaPilot is currently waiting for
                a qualified trading signal.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DECISION ENGINE
# ============================================================

st.markdown(
    '<div class="section-title">🤖 AlphaPilot Decision Engine</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Signals, market analysis and risk controls'
    '</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)


with c1:

    st.markdown(
        """
        <div class="status-card">

            <div class="status-title">
                📊 Market Analysis
            </div>

            <div class="status-text">

                <span class="blue">
                    ● ACTIVE
                </span>

                <br><br>

                SMA20 vs SMA50<br>
                RSI Momentum<br>
                MACD Direction<br>
                Volume Analysis<br>
                Market Conditions

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with c2:

    if positions:

        signal_status = (
            '<span class="green">'
            '🟢 POSITION ACTIVE'
            '</span>'
        )

        signal_description = (
            "AlphaPilot currently has an active "
            "paper-trading position."
        )

    else:

        signal_status = (
            '<span class="yellow">'
            '🟡 WAITING FOR SIGNAL'
            '</span>'
        )

        signal_description = (
            "No active position. AlphaPilot is "
            "waiting for a qualified trade setup."
        )

    st.markdown(
        f"""
        <div class="status-card">

            <div class="status-title">
                🤖 AI Signal
            </div>

            <div class="status-text">

                {signal_status}

                <br><br>

                {signal_description}

                <br><br>

                Confidence threshold enabled.

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with c3:

    st.markdown(
        """
        <div class="status-card">

            <div class="status-title">
                🛡️ Risk Manager
            </div>

            <div class="status-text">

                <span class="green">
                    🟢 ACTIVE
                </span>

                <br><br>

                Stop Loss Protection<br>
                Take Profit Protection<br>
                Duplicate Exit Protection<br>
                Position Monitoring

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# TRADE HISTORY
# ============================================================

st.markdown(
    '<div class="section-title">📜 Trade History</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Recorded executions from the AlphaPilot trading engine'
    '</div>',
    unsafe_allow_html=True,
)

if trades.empty:

    st.info(
        "No completed trades have been recorded yet."
    )

else:

    st.dataframe(
        trades,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# PERFORMANCE
# ============================================================

st.markdown(
    '<div class="section-title">📈 Performance Analysis</div>',
    unsafe_allow_html=True,
)

pnl_column = None

possible_columns = [
    "pnl",
    "PnL",
    "P&L",
    "profit",
    "profit_loss",
    "realized_pl",
    "realized_pnl",
]

for column in possible_columns:

    if column in trades.columns:

        pnl_column = column
        break


if pnl_column is None:

    st.info(
        "Performance statistics will appear after "
        "trades containing P&L data are logged."
    )

else:

    pnl = pd.to_numeric(
        trades[pnl_column],
        errors="coerce",
    ).dropna()

    if pnl.empty:

        st.info(
            "P&L column exists but does not contain "
            "numeric values yet."
        )

    else:

        total_pnl = float(pnl.sum())
        winning = int((pnl > 0).sum())
        total = len(pnl)

        win_rate = (
            winning / total * 100
            if total > 0
            else 0
        )

        avg_pnl = float(pnl.mean())

        p1, p2, p3, p4 = st.columns(4)

        with p1:
            st.metric(
                "Total P&L",
                f"${total_pnl:,.2f}",
            )

        with p2:
            st.metric(
                "Win Rate",
                f"{win_rate:.1f}%",
            )

        with p3:
            st.metric(
                "Winning Trades",
                winning,
            )

        with p4:
            st.metric(
                "Average P&L",
                f"${avg_pnl:,.2f}",
            )

        chart_df = pd.DataFrame(
            {
                "Trade": range(1, len(pnl) + 1),
                "P&L": pnl.values,
            }
        )

        chart_df["Cumulative P&L"] = (
            chart_df["P&L"].cumsum()
        )

        fig = px.line(
            chart_df,
            x="Trade",
            y="Cumulative P&L",
            markers=True,
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"),
            margin=dict(
                l=20,
                r=20,
                t=25,
                b=20,
            ),
            xaxis=dict(
                title="Trade",
                gridcolor="#263244",
            ),
            yaxis=dict(
                title="Cumulative P&L ($)",
                gridcolor="#263244",
            ),
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )


# ============================================================
# DATA SOURCES
# ============================================================

st.markdown(
    '<div class="section-title">📁 System Data Sources</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Files currently being used by the dashboard'
    '</div>',
    unsafe_allow_html=True,
)

d1, d2 = st.columns(2)


with d1:

    if TRADE_HISTORY.exists():

        st.success("✅ agents/trade_history.csv")

    else:

        st.warning("⚠️ agents/trade_history.csv not found")


with d2:

    if TRADE_LOG.exists():

        st.success("✅ logs/trades.csv")

    else:

        st.warning("⚠️ logs/trades.csv not found")


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">

        🚀 AlphaPilot AI
        &nbsp;•&nbsp;
        Paper Trading System
        &nbsp;•&nbsp;
        Market Analysis → AI Signal → Options →
        Risk → Execution → Monitoring

        <br>

        Built for demonstration and educational purposes.

    </div>
    """,
    unsafe_allow_html=True,
)