# ============================================================
# AlphaPilot AI - Professional Paper Trading Dashboard
# ============================================================
# Real Alpaca paper-account data
# No fake performance data
# No fake trades
# No live-money execution
# ============================================================

import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

# ------------------------------------------------------------
# Optional Alpaca import
# ------------------------------------------------------------
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderSide, QueryOrderStatus
except Exception:
    TradingClient = None
    OrderSide = None
    QueryOrderStatus = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AlphaPilot AI",
    page_icon="🤖",
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
# ENVIRONMENT
# ============================================================

load_dotenv(BASE_DIR / ".env")


# ============================================================
# CUSTOM STREAMLIT CSS
# ============================================================
# CSS only for visual styling.
# No HTML dashboard cards are generated through st.markdown.
# ============================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #0b1120;
    }

    /* Main content */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }

    /* Sidebar title */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #f8fafc;
    }

    /* Normal text */
    p, label, span {
        color: #cbd5e1;
    }

    /* Headings */
    h1, h2, h3 {
        color: #f8fafc !important;
    }

    /* Metric */
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border: 1px solid #1e293b;
        border-radius: 10px;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        border: 1px solid #1e293b;
        border-radius: 10px;
        background-color: #0f172a;
    }

    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #334155;
        background-color: #111827;
        color: #e2e8f0;
    }

    .stButton > button:hover {
        border-color: #64748b;
        color: #ffffff;
    }

    /* Divider */
    hr {
        border-color: #1e293b;
    }

    /* Small text */
    .small-muted {
        color: #64748b;
        font-size: 0.82rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def get_secret(name: str):
    """
    Read secret from Streamlit Cloud secrets first,
    then fall back to environment variables.
    """

    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass

    return os.getenv(name)


def money(value):
    """Format numeric value as USD."""
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def percent(value):
    """Format percentage."""
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "0.00%"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def normalize_columns(df):
    """
    Normalize CSV column names so different logger versions
    can still be displayed safely.
    """

    if df is None or df.empty:
        return df

    df = df.copy()

    df.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in df.columns
    ]

    return df


# ============================================================
# ALPACA CONNECTION
# ============================================================

API_KEY = get_secret("ALPACA_API_KEY")
SECRET_KEY = get_secret("ALPACA_SECRET_KEY")

trading_client = None
alpaca_error = None

if TradingClient is not None and API_KEY and SECRET_KEY:

    try:
        trading_client = TradingClient(
            API_KEY,
            SECRET_KEY,
            paper=True,
        )

    except Exception as exc:
        alpaca_error = str(exc)

elif not API_KEY or not SECRET_KEY:
    alpaca_error = "Alpaca API credentials are not configured."


# ============================================================
# LOAD TRADE HISTORY
# ============================================================

def load_trade_history():

    if TRADE_HISTORY.exists():

        try:
            df = pd.read_csv(TRADE_HISTORY)
            return normalize_columns(df)

        except Exception:
            pass

    if TRADE_LOG.exists():

        try:
            df = pd.read_csv(TRADE_LOG)
            return normalize_columns(df)

        except Exception:
            pass

    return pd.DataFrame()


trade_history = load_trade_history()


# ============================================================
# ALPACA ACCOUNT DATA
# ============================================================

account = None
positions = []
orders = []

if trading_client is not None:

    try:
        account = trading_client.get_account()
    except Exception as exc:
        alpaca_error = f"Account error: {exc}"

    try:
        positions = trading_client.get_all_positions()
    except Exception:
        positions = []

    try:
        if QueryOrderStatus is not None:
            orders = trading_client.get_orders(
                filter=QueryOrderStatus.ALL
            )
        else:
            orders = trading_client.get_orders()

    except Exception:
        orders = []


# ============================================================
# ACCOUNT VALUES
# ============================================================

if account is not None:

    equity = safe_float(account.equity)

    last_equity = safe_float(
        getattr(account, "last_equity", equity)
    )

    cash = safe_float(
        getattr(account, "cash", 0)
    )

    buying_power = safe_float(
        getattr(account, "buying_power", 0)
    )

    day_change = equity - last_equity

else:

    equity = 0.0
    last_equity = 0.0
    cash = 0.0
    buying_power = 0.0
    day_change = 0.0


# ============================================================
# TRADE STATISTICS
# ============================================================

completed_trades = 0
winning_trades = 0
losing_trades = 0
total_pnl = 0.0
average_pnl = 0.0
win_rate = 0.0


def calculate_trade_stats(df):

    if df is None or df.empty:
        return 0, 0, 0, 0.0, 0.0, 0.0

    pnl_column = None

    possible_columns = [
        "pnl",
        "profit_loss",
        "profit",
        "realized_pnl",
        "realized_profit",
        "net_pnl",
    ]

    for column in possible_columns:
        if column in df.columns:
            pnl_column = column
            break

    if pnl_column is None:
        return 0, 0, 0, 0.0, 0.0, 0.0

    pnl_values = pd.to_numeric(
        df[pnl_column],
        errors="coerce"
    ).dropna()

    if pnl_values.empty:
        return 0, 0, 0, 0.0, 0.0, 0.0

    completed = len(pnl_values)

    wins = int((pnl_values > 0).sum())
    losses = int((pnl_values < 0).sum())

    total = float(pnl_values.sum())
    average = float(pnl_values.mean())

    win_percentage = (
        (wins / completed) * 100
        if completed > 0
        else 0.0
    )

    return (
        completed,
        wins,
        losses,
        total,
        average,
        win_percentage,
    )


(
    completed_trades,
    winning_trades,
    losing_trades,
    total_pnl,
    average_pnl,
    win_rate,
) = calculate_trade_stats(trade_history)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🤖 AlphaPilot AI")

    st.caption("Autonomous AI Paper-Trading System")

    st.divider()

    st.subheader("Trading Mode")

    st.success("PAPER TRADING")

    st.caption(
        "Real market/account data • No live-money execution"
    )

    st.divider()

    st.subheader("Trading Pipeline")

    pipeline_options = [
        "01 · Market Analysis",
        "02 · AI Signal",
        "03 · Options Selection",
        "04 · Risk Checks",
        "05 · Paper Entry",
        "06 · Monitoring",
        "07 · Exit",
    ]

    selected_stage = st.radio(
        "Navigate",
        pipeline_options,
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    st.subheader("Connection")

    if trading_client is not None:

        st.success("Alpaca Connected")

    else:

        st.error("Alpaca Not Connected")

    if alpaca_error:
        with st.expander("Connection details"):
            st.caption(str(alpaca_error))

    st.divider()

    st.caption(
        f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


# ============================================================
# HEADER
# ============================================================

st.title("🤖 AlphaPilot AI")

st.caption(
    "AI-powered autonomous options paper-trading system"
)

header_col1, header_col2 = st.columns([4, 1])

with header_col1:

    st.markdown(
        """
        **Market Analysis → AI Signal → Options Selection → "
        "Risk Checks → Paper Entry → Monitoring → Exit**
        """
    )

with header_col2:

    if trading_client is not None:
        st.success("● LIVE DATA")
    else:
        st.error("● OFFLINE")


# ============================================================
# ACCOUNT OVERVIEW
# ============================================================

st.header("Trading Overview")

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:
    st.metric(
        "Account Equity",
        money(equity),
        delta=money(day_change),
    )

with metric2:
    st.metric(
        "Cash",
        money(cash),
    )

with metric3:
    st.metric(
        "Buying Power",
        money(buying_power),
    )

with metric4:
    st.metric(
        "Open Positions",
        len(positions),
    )


metric5, metric6, metric7, metric8 = st.columns(4)

with metric5:
    st.metric(
        "Total P&L",
        money(total_pnl),
    )

with metric6:
    st.metric(
        "Win Rate",
        percent(win_rate),
    )

with metric7:
    st.metric(
        "Completed Trades",
        completed_trades,
    )

with metric8:
    st.metric(
        "Average P&L",
        money(average_pnl),
    )


# ============================================================
# PIPELINE STATUS
# ============================================================

st.divider()

st.header("Autonomous Trading Pipeline")

pipeline_cols = st.columns(7)

pipeline_labels = [
    ("01", "Market", "📊"),
    ("02", "Signal", "🧠"),
    ("03", "Options", "⚙️"),
    ("04", "Risk", "🛡️"),
    ("05", "Entry", "🚀"),
    ("06", "Monitor", "👁️"),
    ("07", "Exit", "🏁"),
]

for col, (number, label, icon) in zip(
    pipeline_cols,
    pipeline_labels
):

    with col:

        st.markdown(f"### {icon} {number}")

        st.caption(label)

        if f"{number}" in selected_stage:
            st.success("Selected")
        else:
            st.info("Pipeline")


# ============================================================
# CURRENT POSITIONS
# ============================================================

st.divider()

st.header("Current Positions")

if positions:

    position_rows = []

    for position in positions:

        position_rows.append(
            {
                "Symbol": getattr(position, "symbol", ""),
                "Qty": safe_float(
                    getattr(position, "qty", 0)
                ),
                "Side": str(
                    getattr(position, "side", "")
                ).replace("PositionSide.", ""),
                "Avg Entry": money(
                    getattr(position, "avg_entry_price", 0)
                ),
                "Current Price": money(
                    getattr(position, "current_price", 0)
                ),
                "Market Value": money(
                    getattr(position, "market_value", 0)
                ),
                "Unrealized P&L": money(
                    getattr(position, "unrealized_pl", 0)
                ),
                "P&L %": percent(
                    getattr(position, "unrealized_plpc", 0)
                ),
            }
        )

    position_df = pd.DataFrame(position_rows)

    st.dataframe(
        position_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No open positions currently exist in the Alpaca paper account."
    )


# ============================================================
# STAGE 01 - MARKET ANALYSIS
# ============================================================

st.divider()

st.header("01 · 📊 Market Analysis")

if selected_stage.startswith("01"):

    st.success("Market Analysis stage selected.")

st.markdown(
    """
    AlphaPilot begins by collecting market information before considering
    any trade.

    The analysis layer can evaluate:

    - Price movement
    - SMA20
    - SMA50
    - RSI
    - MACD
    - Trading volume
    - Overall market conditions
    - SPY market environment

    The purpose of this stage is to avoid making an options decision
    before the underlying market has been evaluated.
    """
)

market_col1, market_col2 = st.columns(2)

with market_col1:

    st.subheader("Market Data")

    st.info(
        "Market-analysis values are taken from the trading/data pipeline "
        "when available. The dashboard does not invent indicator values."
    )

with market_col2:

    st.subheader("Decision Principle")

    st.write(
        "Analyze the underlying market first, then allow the AI signal "
        "engine to determine whether a trade should be considered."
    )


# ============================================================
# STAGE 02 - AI SIGNAL
# ============================================================

st.divider()

st.header("02 · 🧠 AI Signal")

if selected_stage.startswith("02"):

    st.success("AI Signal stage selected.")

st.markdown(
    """
    AlphaPilot combines multiple technical signals before generating a
    trading decision.

    Typical signal inputs include:

    - Price vs SMA20
    - SMA20 vs SMA50
    - RSI momentum
    - MACD direction
    - Volume
    - Market conditions
    - Confidence threshold
    """
)

signal_col1, signal_col2 = st.columns(2)

with signal_col1:

    st.subheader("Signal Output")

    st.info(
        "BUY SIGNAL or NO TRADE"
    )

with signal_col2:

    st.subheader("Confidence Gate")

    st.info(
        "A trade should only proceed when the configured confidence "
        "requirement is satisfied."
    )


# ============================================================
# STAGE 03 - OPTIONS SELECTION
# ============================================================

st.divider()

st.header("03 · ⚙️ Options Selection")

if selected_stage.startswith("03"):

    st.success("Options Selection stage selected.")

st.markdown(
    """
    After an underlying-market signal is generated, AlphaPilot evaluates
    available options contracts.

    The selection process can consider:

    - Strike price distance
    - Expiration
    - Open interest
    - Contract suitability
    - Selection score
    - Risk/reward characteristics
    """
)

options_col1, options_col2 = st.columns(2)

with options_col1:

    st.subheader("Underlying")

    st.metric(
        "Primary Underlying",
        "SPY",
    )

with options_col2:

    st.subheader("Selection Status")

    st.info(
        "Contract selection is performed by the options-strategy layer."
    )


# ============================================================
# STAGE 04 - RISK CHECKS
# ============================================================

st.divider()

st.header("04 · 🛡️ Risk Checks")

if selected_stage.startswith("04"):

    st.success("Risk Checks stage selected.")

risk_col1, risk_col2, risk_col3 = st.columns(3)

with risk_col1:

    st.subheader("Position Risk")

    st.write(
        "Position sizing and account exposure should be checked "
        "before entry."
    )

with risk_col2:

    st.subheader("Stop Loss")

    st.write(
        "Stop-loss rules are evaluated before and during a trade."
    )

with risk_col3:

    st.subheader("Take Profit")

    st.write(
        "Take-profit conditions are monitored after entry."
    )


# ============================================================
# STAGE 05 - PAPER ENTRY
# ============================================================

st.divider()

st.header("05 · 🚀 Paper Entry")

if selected_stage.startswith("05"):

    st.success("Paper Entry stage selected.")

entry_col1, entry_col2 = st.columns(2)

with entry_col1:

    st.subheader("Execution Environment")

    st.success(
        "Alpaca Paper Trading"
    )

    st.caption(
        "No live-money order execution is performed by this dashboard."
    )

with entry_col2:

    st.subheader("Order Activity")

    if orders:

        recent_orders = []

        for order in orders[:10]:

            recent_orders.append(
                {
                    "Symbol": getattr(order, "symbol", ""),
                    "Side": str(
                        getattr(order, "side", "")
                    ).replace("OrderSide.", ""),
                    "Type": str(
                        getattr(order, "order_type", "")
                    ).replace("OrderType.", ""),
                    "Qty": getattr(order, "qty", ""),
                    "Status": str(
                        getattr(order, "status", "")
                    ).replace("OrderStatus.", ""),
                }
            )

        orders_df = pd.DataFrame(recent_orders)

        st.dataframe(
            orders_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No order records are currently available."
        )


# ============================================================
# STAGE 06 - MONITORING
# ============================================================

st.divider()

st.header("06 · 👁️ Monitoring")

if selected_stage.startswith("06"):

    st.success("Monitoring stage selected.")

monitor_col1, monitor_col2 = st.columns(2)

with monitor_col1:

    st.subheader("Open Position Monitoring")

    if positions:

        for position in positions:

            symbol = getattr(position, "symbol", "Unknown")

            unrealized = safe_float(
                getattr(position, "unrealized_pl", 0)
            )

            unrealized_pct = safe_float(
                getattr(position, "unrealized_plpc", 0)
            )

            st.metric(
                symbol,
                money(unrealized),
                delta=percent(unrealized_pct),
            )

    else:

        st.info(
            "There are currently no positions to monitor."
        )

with monitor_col2:

    st.subheader("Monitoring Rules")

    st.write(
        """
        AlphaPilot can monitor:

        • Current market price  
        • Position P&L  
        • Stop-loss condition  
        • Take-profit condition  
        • Exit signal  
        • Position status
        """
    )


# ============================================================
# STAGE 07 - EXIT
# ============================================================

st.divider()

st.header("07 · 🏁 Exit")

if selected_stage.startswith("07"):

    st.success("Exit stage selected.")

st.markdown(
    """
    The exit stage closes a paper position when the configured exit
    conditions are satisfied.

    Possible exit triggers include:

    - Stop loss
    - Take profit
    - AI reversal
    - Market-condition change
    - Risk-control condition
    - Manual paper-account intervention
    """
)

if positions:

    st.warning(
        "Open position(s) are currently present. Exit decisions should "
        "be generated by the monitoring/risk logic."
    )

else:

    st.success(
        "No open positions currently require an automated exit."
    )


# ============================================================
# TRADE HISTORY
# ============================================================

st.divider()

st.header("Trade History")

if not trade_history.empty:

    st.caption(
        f"Source: "
        f"{TRADE_HISTORY.relative_to(BASE_DIR) if TRADE_HISTORY.exists() else TRADE_LOG.relative_to(BASE_DIR)}"
    )

    display_history = trade_history.copy()

    st.dataframe(
        display_history,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No trade-history CSV is currently available. "
        "The dashboard will populate this section when the trading "
        "pipeline records completed trades."
    )


# ============================================================
# PERFORMANCE
# ============================================================

st.divider()

st.header("Performance")

perf_col1, perf_col2 = st.columns(2)

with perf_col1:

    st.subheader("P&L Summary")

    performance_df = pd.DataFrame(
        {
            "Metric": [
                "Total P&L",
                "Average P&L",
                "Winning Trades",
                "Losing Trades",
                "Win Rate",
            ],
            "Value": [
                money(total_pnl),
                money(average_pnl),
                winning_trades,
                losing_trades,
                percent(win_rate),
            ],
        }
    )

    st.dataframe(
        performance_df,
        use_container_width=True,
        hide_index=True,
    )


with perf_col2:

    st.subheader("P&L Visualization")

    pnl_column = None

    if not trade_history.empty:

        for column in [
            "pnl",
            "profit_loss",
            "profit",
            "realized_pnl",
            "realized_profit",
            "net_pnl",
        ]:

            if column in trade_history.columns:

                pnl_column = column
                break

    if pnl_column is not None:

        chart_df = trade_history.copy()

        chart_df[pnl_column] = pd.to_numeric(
            chart_df[pnl_column],
            errors="coerce",
        )

        chart_df = chart_df.dropna(
            subset=[pnl_column]
        )

        if not chart_df.empty:

            chart_df["Cumulative P&L"] = (
                chart_df[pnl_column].cumsum()
            )

            chart_df["Trade"] = range(
                1,
                len(chart_df) + 1
            )

            fig = px.line(
                chart_df,
                x="Trade",
                y="Cumulative P&L",
                markers=True,
                title="Cumulative Realized P&L",
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                margin=dict(
                    l=20,
                    r=20,
                    t=50,
                    b=20,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        else:

            st.info(
                "No numeric P&L records are available for plotting."
            )

    else:

        st.info(
            "A P&L column was not found in the trade-history file."
        )


# ============================================================
# AI DECISION / EXPLAINABILITY
# ============================================================

st.divider()

st.header("AI Decision Engine")

decision_col1, decision_col2 = st.columns(2)

with decision_col1:

    st.subheader("Decision Flow")

    st.write(
        """
        1. Collect market data  
        2. Calculate technical indicators  
        3. Evaluate market conditions  
        4. Generate AI/trading signal  
        5. Apply confidence threshold  
        6. Select options contract  
        7. Apply risk controls  
        8. Submit paper order  
        9. Monitor position  
        10. Exit according to defined rules
        """
    )

with decision_col2:

    st.subheader("Explainability")

    st.info(
        "AlphaPilot is designed to make the trading decision process "
        "traceable instead of treating the final BUY/NO TRADE decision "
        "as a black box."
    )


# ============================================================
# DATA SOURCES
# ============================================================

st.divider()

st.header("Data Sources & System Status")

source_col1, source_col2, source_col3 = st.columns(3)

with source_col1:

    st.subheader("Broker")

    if trading_client is not None:

        st.success("Alpaca Paper API")

    else:

        st.error("Alpaca unavailable")


with source_col2:

    st.subheader("Trade History")

    if TRADE_HISTORY.exists():

        st.success(
            "agents/trade_history.csv"
        )

    elif TRADE_LOG.exists():

        st.success(
            "logs/trades.csv"
        )

    else:

        st.info(
            "No trade-history file"
        )


with source_col3:

    st.subheader("Execution Mode")

    st.success(
        "PAPER ONLY"
    )


# ============================================================
# SYSTEM INFORMATION
# ============================================================

st.divider()

with st.expander("System Information"):

    st.write(
        {
            "Application": "AlphaPilot AI",
            "Trading Mode": "Paper Trading",
            "Broker": "Alpaca",
            "Account Connected": trading_client is not None,
            "Account Equity": equity,
            "Cash": cash,
            "Buying Power": buying_power,
            "Open Positions": len(positions),
            "Completed Trades": completed_trades,
            "Total P&L": total_pnl,
            "Win Rate": win_rate,
            "Trade History File": str(TRADE_HISTORY),
            "Trade Log File": str(TRADE_LOG),
        }
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "AlphaPilot AI • Autonomous AI Paper-Trading System • "
    "Built with Python, Streamlit, Alpaca and market-data analytics"
)

st.caption(
    "Paper trading only. Dashboard displays real account/trade data "
    "when available and does not fabricate performance results."
)