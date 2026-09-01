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
# ALPHAPILOT AI DASHBOARD
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
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 16px;
        color: #777;
        margin-bottom: 25px;
    }

    .status-box {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🚀 AlphaPilot AI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">AI-Powered Paper Trading & Options Monitoring Dashboard</div>',
    unsafe_allow_html=True,
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ AlphaPilot")

st.sidebar.markdown("### System")

st.sidebar.success("🟢 PAPER TRADING")

st.sidebar.markdown(
    """
    **Pipeline**

    Market Analysis  
    ↓  
    AI Signal  
    ↓  
    Options Selection  
    ↓  
    Risk Checks  
    ↓  
    Paper Entry  
    ↓  
    Position Monitoring  
    ↓  
    Exit
    """
)

refresh = st.sidebar.button("🔄 Refresh Dashboard")

if refresh:
    st.rerun()


# ============================================================
# LOAD TRADE DATA
# ============================================================

def load_csv(path):

    try:

        if not path.exists():
            return pd.DataFrame()

        df = pd.read_csv(path)

        return df

    except Exception as e:

        st.warning(f"Unable to read {path.name}: {e}")

        return pd.DataFrame()


trade_history = load_csv(TRADE_HISTORY)
trade_log = load_csv(TRADE_LOG)


# ============================================================
# COMBINE AVAILABLE TRADE DATA
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

if (
    TradingClient is not None
    and API_KEY
    and SECRET_KEY
):

    try:

        trading_client = TradingClient(
            API_KEY,
            SECRET_KEY,
            paper=True,
        )

    except Exception:

        trading_client = None


# ============================================================
# ACCOUNT INFORMATION
# ============================================================

account = None
positions = []

if trading_client is not None:

    try:

        account = trading_client.get_account()

    except Exception:

        account = None

    try:

        positions = trading_client.get_all_positions()

    except Exception:

        positions = []


# ============================================================
# TOP METRICS
# ============================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Trading Mode",
        "PAPER",
    )


with col2:

    if account is not None:

        try:
            equity = float(account.equity)
            st.metric(
                "Account Equity",
                f"",
            )

        except Exception:

            st.metric(
                "Account Equity",
                "N/A",
            )

    else:

        st.metric(
            "Account Equity",
            "N/A",
        )


with col3:

    st.metric(
        "Open Positions",
        len(positions),
    )


with col4:

    if trades.empty:

        st.metric(
            "Completed Trades",
            0,
        )

    else:

        st.metric(
            "Completed Trades",
            len(trades),
        )


st.divider()


# ============================================================
# CURRENT POSITION
# ============================================================

st.subheader("📊 Current Position")


if positions:

    position_rows = []

    for position in positions:

        try:

            symbol = str(position.symbol)

            qty = float(position.qty)

            entry = float(position.avg_entry_price)

            current = float(position.current_price)

            market_value = float(position.market_value)

            unrealized = float(position.unrealized_pl)

            unrealized_pct = float(
                position.unrealized_plpc
            ) * 100

            position_rows.append(
                {
                    "Symbol": symbol,
                    "Quantity": qty,
                    "Entry Price": entry,
                    "Current Price": current,
                    "Market Value": market_value,
                    "Unrealized P&L": unrealized,
                    "P&L %": unrealized_pct,
                }
            )

        except Exception:
            continue


    if position_rows:

        position_df = pd.DataFrame(
            position_rows
        )

        st.dataframe(
            position_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Open positions exist, but position details could not be displayed."
        )

else:

    st.info(
        "No open positions detected."
    )


# ============================================================
# ALPHAPILOT SIGNAL STATUS
# ============================================================

st.divider()

st.subheader("🤖 AlphaPilot Decision Engine")

signal_col1, signal_col2, signal_col3 = st.columns(3)


with signal_col1:

    st.markdown("### Market Analysis")

    st.info(
        "Technical indicators → SMA20 → SMA50 → RSI → MACD → Volume"
    )


with signal_col2:

    st.markdown("### AI Signal")

    if positions:

        st.success("🟢 POSITION ACTIVE")

    else:

        st.warning("🟡 WAITING FOR SIGNAL")


with signal_col3:

    st.markdown("### Risk Manager")

    st.success(
        "🛡️ Stop Loss / Take Profit ACTIVE"
    )


# ============================================================
# TRADE HISTORY
# ============================================================

st.divider()

st.subheader("📜 Trade History")


if trades.empty:

    st.info(
        "No completed trades found yet."
    )

else:

    display_trades = trades.copy()

    st.dataframe(
        display_trades,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# PERFORMANCE ANALYSIS
# ============================================================

st.divider()

st.subheader("📈 Performance Analysis")


if trades.empty:

    st.info(
        "Performance statistics will appear after trades are logged."
    )

else:

    pnl_column = None

    possible_columns = [
        "pnl",
        "PnL",
        "profit",
        "profit_loss",
        "realized_pl",
        "realized_pnl",
    ]

    for column in possible_columns:

        if column in trades.columns:

            pnl_column = column
            break


    if pnl_column is not None:

        pnl = pd.to_numeric(
            trades[pnl_column],
            errors="coerce",
        ).dropna()

        if not pnl.empty:

            total_pnl = pnl.sum()

            winning = (pnl > 0).sum()

            losing = (pnl < 0).sum()

            total = len(pnl)

            win_rate = (
                winning / total * 100
                if total > 0
                else 0
            )

            p1, p2, p3 = st.columns(3)

            with p1:

                st.metric(
                    "Total P&L",
                    f"",
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


            chart_df = pd.DataFrame(
                {
                    "Trade": range(
                        1,
                        len(pnl) + 1,
                    ),
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
                title="Cumulative P&L",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        else:

            st.info(
                "P&L column exists but contains no numeric values."
            )

    else:

        st.info(
            "No recognized P&L column found in the trade log."
        )


# ============================================================
# DATA SOURCES
# ============================================================

st.divider()

st.subheader("📁 Data Sources")

source1, source2 = st.columns(2)


with source1:

    if TRADE_HISTORY.exists():

        st.success(
            f"✅ {TRADE_HISTORY.relative_to(BASE_DIR)}"
        )

    else:

        st.warning(
            f"⚠️ {TRADE_HISTORY.relative_to(BASE_DIR)} not found"
        )


with source2:

    if TRADE_LOG.exists():

        st.success(
            f"✅ {TRADE_LOG.relative_to(BASE_DIR)}"
        )

    else:

        st.warning(
            f"⚠️ {TRADE_LOG.relative_to(BASE_DIR)} not found"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "AlphaPilot AI • Paper Trading System • "
    "Market Analysis → Signal → Options → Risk → Execution → Monitoring"
)
