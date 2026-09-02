# -*- coding: utf-8 -*-

# ============================================================
# AlphaPilot AI - LIVE Interactive Paper Trading Dashboard
# ============================================================
# REAL DATA ONLY
# REAL ALPACA PAPER ACCOUNT ONLY
# NO FABRICATED SIGNALS
# NO FABRICATED PERFORMANCE
# NO LIVE-MONEY EXECUTION
#
# Pipeline:
# Market -> AI Signal -> Options -> Risk -> Paper Order -> Monitor
# ============================================================

import os
import math
from pathlib import Path
from datetime import datetime, timedelta, date, timezone
from agents.position_monitor import monitor_positions

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


# ============================================================
# OPTIONAL ALPACA IMPORTS
# ============================================================

try:
    from alpaca.trading.client import TradingClient

    from alpaca.trading.enums import (
        QueryOrderStatus,
        OrderSide,
        TimeInForce,
        ContractType,
    )

    from alpaca.trading.requests import (
        GetOptionContractsRequest,
        MarketOrderRequest,
    )

    from alpaca.data.historical import (
        StockHistoricalDataClient,
        OptionHistoricalDataClient,
    )

    from alpaca.data.requests import (
        StockBarsRequest,
        StockLatestTradeRequest,
        OptionLatestQuoteRequest,
    )

    from alpaca.data.timeframe import TimeFrame

    # Basic Alpaca equity data uses IEX.
    from alpaca.data.enums import DataFeed

    ALPACA_AVAILABLE = True
    ALPACA_IMPORT_ERROR = None

except Exception as exc:

    TradingClient = None
    QueryOrderStatus = None
    OrderSide = None
    TimeInForce = None
    ContractType = None

    GetOptionContractsRequest = None
    MarketOrderRequest = None

    StockHistoricalDataClient = None
    OptionHistoricalDataClient = None

    StockBarsRequest = None
    StockLatestTradeRequest = None
    OptionLatestQuoteRequest = None

    TimeFrame = None
    DataFeed = None

    ALPACA_AVAILABLE = False
    ALPACA_IMPORT_ERROR = str(exc)


# ============================================================
# PAGE CONFIG
# ============================================================

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
# ENVIRONMENT
# ============================================================

load_dotenv(BASE_DIR / ".env")


# ============================================================
# STRATEGY SETTINGS
# ============================================================

UNDERLYING = "SPY"

MIN_CONFIDENCE = 70

MIN_DTE = 7
MAX_DTE = 30

MAX_STRIKE_DISTANCE = 15.0
MIN_OPEN_INTEREST = 100

MAX_ACCOUNT_RISK = 0.01

STOP_LOSS_PCT = 0.25
TAKE_PROFIT_PCT = 0.50

DEFAULT_CONTRACT_QTY = 1


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #0b1120;
    }

    .block-container {
        max-width: 1550px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3 {
        color: #f8fafc !important;
    }

    .hero-box {
        background: linear-gradient(
            135deg,
            #111827,
            #172033
        );
        border: 1px solid #29364d;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }

    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 1rem;
    }

    .pipeline-box {
        background: #111827;
        border: 1px solid #243044;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 18px;
        color: #cbd5e1;
        text-align: center;
        font-size: 14px;
    }

    div[data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #243044;
        border-radius: 12px;
        padding: 14px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 9px;
        min-height: 42px;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "market_data": None,
    "ai_decision": None,
    "selected_option": None,
    "option_candidates": [],
    "risk_result": None,
    "last_order": None,
    "analysis_timestamp": None,
    "market_error": None,
    "paper_order_confirmation": False,
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def get_secret(name):

    try:

        value = st.secrets.get(name)

        if value:
            return value

    except Exception:
        pass

    return os.getenv(name)


def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:
        return default


def money(value):

    try:
        return f"${float(value):,.2f}"

    except Exception:
        return "$0.00"


def pct(value):

    try:
        return f"{float(value):.2f}%"

    except Exception:
        return "0.00%"


def enum_text(value):

    if value is None:
        return ""

    return str(value).split(".")[-1].lower()


def normalize_columns(df):

    if df is None or df.empty:
        return df

    df = df.copy()

    df.columns = [
        str(c)
        .strip()
        .lower()
        .replace(" ", "_")
        for c in df.columns
    ]

    return df


def find_pnl_column(df):

    if df is None or df.empty:
        return None

    candidates = [
        "pnl",
        "p&l",
        "profit_loss",
        "profit",
        "realized_pnl",
        "realized_profit",
        "net_pnl",
    ]

    for column in candidates:

        if column in df.columns:
            return column

    return None


def now_local():

    return datetime.now()


# ============================================================
# CREDENTIALS
# ============================================================

API_KEY = get_secret("ALPACA_API_KEY")

SECRET_KEY = get_secret("ALPACA_SECRET_KEY")


# ============================================================
# CLIENTS
# ============================================================

trading_client = None
stock_client = None
option_client = None

alpaca_error = None


if ALPACA_AVAILABLE and API_KEY and SECRET_KEY:

    try:

        # PAPER ONLY
        trading_client = TradingClient(
            API_KEY,
            SECRET_KEY,
            paper=True,
        )

        stock_client = StockHistoricalDataClient(
            API_KEY,
            SECRET_KEY,
        )

        option_client = OptionHistoricalDataClient(
            API_KEY,
            SECRET_KEY,
        )

    except Exception as exc:

        alpaca_error = str(exc)

else:

    if not ALPACA_AVAILABLE:

        alpaca_error = (
            "alpaca-py import failed: "
            + str(ALPACA_IMPORT_ERROR)
        )

    elif not API_KEY or not SECRET_KEY:

        alpaca_error = (
            "ALPACA_API_KEY or ALPACA_SECRET_KEY "
            "is missing."
        )


# ============================================================
# MARKET DATA
# ============================================================

def fetch_market_data():

    if stock_client is None:

        raise RuntimeError(
            "Alpaca market-data client is not connected."
        )

    if DataFeed is None:

        raise RuntimeError(
            "Alpaca DataFeed support is unavailable. "
            "Upgrade alpaca-py."
        )

    # --------------------------------------------------------
    # LATEST SPY TRADE
    # --------------------------------------------------------

    latest_request = StockLatestTradeRequest(
        symbol_or_symbols=UNDERLYING,
        feed=DataFeed.IEX,
    )

    latest = stock_client.get_stock_latest_trade(
        latest_request
    )

    latest_trade = latest.get(
        UNDERLYING
    )

    if latest_trade is None:

        raise RuntimeError(
            "No latest SPY trade was returned."
        )

    current_price = safe_float(
        getattr(
            latest_trade,
            "price",
            0,
        )
    )

    if current_price <= 0:

        raise RuntimeError(
            "Invalid SPY latest trade price."
        )

    # --------------------------------------------------------
    # HISTORICAL DAILY BARS
    # --------------------------------------------------------

    end = datetime.now(timezone.utc)

    start = end - timedelta(days=120)

    bars_request = StockBarsRequest(
        symbol_or_symbols=UNDERLYING,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        limit=100,
        feed=DataFeed.IEX,
    )

    bars_response = stock_client.get_stock_bars(
        bars_request
    )

    try:

        bars = bars_response[UNDERLYING]

    except Exception:

        bars = []

    rows = []

    for bar in bars:

        rows.append(
            {
                "timestamp": getattr(
                    bar,
                    "timestamp",
                    None,
                ),
                "close": safe_float(
                    getattr(
                        bar,
                        "close",
                        0,
                    )
                ),
                "volume": safe_float(
                    getattr(
                        bar,
                        "volume",
                        0,
                    )
                ),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:

        raise RuntimeError(
            "No historical SPY bars were returned."
        )

    if len(df) < 50:

        raise RuntimeError(
            "Not enough SPY historical bars to calculate "
            "SMA20, SMA50, RSI and MACD."
        )

    # --------------------------------------------------------
    # TECHNICAL INDICATORS
    # --------------------------------------------------------

    df["sma20"] = (
        df["close"]
        .rolling(20)
        .mean()
    )

    df["sma50"] = (
        df["close"]
        .rolling(50)
        .mean()
    )

    delta = df["close"].diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = (
        gain
        .rolling(14)
        .mean()
    )

    avg_loss = (
        loss
        .rolling(14)
        .mean()
    )

    rs = (
        avg_gain
        / avg_loss.replace(
            0,
            math.nan,
        )
    )

    df["rsi"] = (
        100
        - (
            100
            / (
                1 + rs
            )
        )
    )

    ema12 = (
        df["close"]
        .ewm(
            span=12,
            adjust=False,
        )
        .mean()
    )

    ema26 = (
        df["close"]
        .ewm(
            span=26,
            adjust=False,
        )
        .mean()
    )

    df["macd"] = ema12 - ema26

    df["macd_signal"] = (
        df["macd"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    df["volume_sma20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    row = df.iloc[-1]

    price = current_price

    sma20 = safe_float(row["sma20"])

    sma50 = safe_float(row["sma50"])

    rsi = safe_float(row["rsi"])

    macd = safe_float(row["macd"])

    macd_signal = safe_float(
        row["macd_signal"]
    )

    volume = safe_float(row["volume"])

    volume_average = safe_float(
        row["volume_sma20"]
    )

    # --------------------------------------------------------
    # CONDITIONS
    # --------------------------------------------------------

    bullish_trend = (
        price > sma20
        and sma20 > sma50
    )

    bullish_macd = (
        macd > macd_signal
    )

    supportive_rsi = (
        50 <= rsi <= 70
    )

    volume_confirmation = (
        volume >= volume_average
        if volume_average > 0
        else False
    )

    return {

        "price": price,
        "sma20": sma20,
        "sma50": sma50,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "volume": volume,
        "volume_average": volume_average,

        "bullish_trend": bullish_trend,
        "bullish_macd": bullish_macd,
        "supportive_rsi": supportive_rsi,
        "volume_confirmation": volume_confirmation,

        "bars": df,

        "timestamp": now_local(),

    }


# ============================================================
# AI DECISION
# ============================================================

def calculate_ai_decision(market):

    checks = {

        "Price > SMA20": (
            market["price"]
            > market["sma20"]
        ),

        "SMA20 > SMA50": (
            market["sma20"]
            > market["sma50"]
        ),

        "RSI supportive": (
            50
            <= market["rsi"]
            <= 70
        ),

        "MACD bullish": (
            market["macd"]
            > market["macd_signal"]
        ),

        "Volume confirmation": (
            market["volume"]
            >= market["volume_average"]
            if market["volume_average"] > 0
            else False
        ),
    }

    passed = sum(
        bool(value)
        for value in checks.values()
    )

    total = len(checks)

    confidence = (
        passed
        / total
        * 100
    )

    signal = (
        "BUY"
        if confidence >= MIN_CONFIDENCE
        else "NO TRADE"
    )

    return {

        "signal": signal,

        "confidence": confidence,

        "checks": checks,

        "passed": passed,

        "total": total,

    }


# ============================================================
# OPTIONS SCANNER
# ============================================================

def scan_options(market):

    if trading_client is None:

        raise RuntimeError(
            "Trading client is not connected."
        )

    today = date.today()

    expiration_min = (
        today
        + timedelta(days=MIN_DTE)
    )

    expiration_max = (
        today
        + timedelta(days=MAX_DTE)
    )

    lower_strike = (
        market["price"]
        - MAX_STRIKE_DISTANCE
    )

    upper_strike = (
        market["price"]
        + MAX_STRIKE_DISTANCE
    )

    request = GetOptionContractsRequest(

        underlying_symbols=[
            UNDERLYING
        ],

        type=ContractType.CALL,

        expiration_date_gte=expiration_min,

        expiration_date_lte=expiration_max,

        strike_price_gte=str(
            round(
                lower_strike,
                2,
            )
        ),

        strike_price_lte=str(
            round(
                upper_strike,
                2,
            )
        ),

        limit=10000,
    )

    response = (
        trading_client.get_option_contracts(
            request
        )
    )

    contracts = getattr(
        response,
        "option_contracts",
        None,
    )

    if contracts is None:
        contracts = []

    candidates = []

    for contract in contracts:

        if not getattr(
            contract,
            "tradable",
            False,
        ):
            continue

        strike = safe_float(
            getattr(
                contract,
                "strike_price",
                0,
            )
        )

        oi = int(
            safe_float(
                getattr(
                    contract,
                    "open_interest",
                    0,
                )
            )
        )

        expiration = getattr(
            contract,
            "expiration_date",
            None,
        )

        symbol = getattr(
            contract,
            "symbol",
            "",
        )

        if not symbol:
            continue

        if strike <= 0:
            continue

        if expiration is None:
            continue

        distance = abs(
            strike
            - market["price"]
        )

        if distance > MAX_STRIKE_DISTANCE:
            continue

        if oi < MIN_OPEN_INTEREST:
            continue

        dte = (
            expiration - today
        ).days

        if dte < MIN_DTE:
            continue

        if dte > MAX_DTE:
            continue

        # ----------------------------------------------------
        # SELECTION SCORE
        # ----------------------------------------------------

        distance_score = max(
            0,
            100
            - (
                distance
                / MAX_STRIKE_DISTANCE
                * 100
            ),
        )

        oi_score = min(
            100,
            (
                oi
                / 1000
                * 100
            ),
        )

        dte_mid = (
            MIN_DTE
            + MAX_DTE
        ) / 2

        dte_score = max(
            0,
            100
            - (
                abs(
                    dte
                    - dte_mid
                )
                / (
                    MAX_DTE
                    - MIN_DTE
                )
                * 100
            ),
        )

        score = (
            distance_score * 0.45
            + oi_score * 0.30
            + dte_score * 0.25
        )

        candidates.append(
            {
                "symbol": symbol,
                "strike": strike,
                "expiration": expiration,
                "dte": dte,
                "open_interest": oi,
                "score": round(
                    score,
                    2,
                ),
            }
        )

    if not candidates:

        raise RuntimeError(
            "No suitable SPY CALL contracts found "
            "under the current selection rules."
        )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return (
        candidates[0],
        candidates,
    )


# ============================================================
# OPTION PRICE
# ============================================================

def get_option_price(symbol):

    if option_client is None:
        return 0.0

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=symbol
        )

        response = (
            option_client.get_option_latest_quote(
                request
            )
        )

        quote = response.get(symbol)

        if quote is None:
            return 0.0

        bid = safe_float(
            getattr(
                quote,
                "bid_price",
                0,
            )
        )

        ask = safe_float(
            getattr(
                quote,
                "ask_price",
                0,
            )
        )

        if bid > 0 and ask > 0:

            return (
                bid + ask
            ) / 2

        if ask > 0:
            return ask

        if bid > 0:
            return bid

    except Exception:
        pass

    return 0.0


# ============================================================
# ACCOUNT
# ============================================================

def get_account():

    if trading_client is None:
        return None

    try:

        return trading_client.get_account()

    except Exception:

        return None


# ============================================================
# RISK ENGINE
# ============================================================

def run_risk_check():

    option = (
        st.session_state.selected_option
    )

    account = get_account()

    if option is None:

        return {
            "approved": False,
            "reason": "No option has been selected.",
        }

    if account is None:

        return {
            "approved": False,
            "reason": "Alpaca account unavailable.",
        }

    account_equity = safe_float(
        getattr(
            account,
            "equity",
            0,
        )
    )

    option_price = safe_float(
        option.get(
            "price",
            0,
        )
    )

    if option_price <= 0:

        return {
            "approved": False,
            "reason": (
                "No usable option quote is currently "
                "available."
            ),
        }

    quantity = DEFAULT_CONTRACT_QTY

    estimated_cost = (
        option_price
        * 100
        * quantity
    )

    max_risk = (
        account_equity
        * MAX_ACCOUNT_RISK
    )

    position_size_ok = (
        estimated_cost
        <= max_risk
    )

    exposure_ok = (
        estimated_cost
        <= account_equity
        * 0.05
    )

    stop_loss = (
        option_price
        * (
            1
            - STOP_LOSS_PCT
        )
    )

    take_profit = (
        option_price
        * (
            1
            + TAKE_PROFIT_PCT
        )
    )

    stop_loss_ok = (
        stop_loss > 0
        and stop_loss < option_price
    )

    take_profit_ok = (
        take_profit > option_price
    )

    duplicate_entry = False

    if trading_client is not None:

        try:

            positions = (
                trading_client.get_all_positions()
            )

            duplicate_entry = any(

                getattr(
                    p,
                    "symbol",
                    "",
                )
                == option["symbol"]

                for p in positions

            )

        except Exception:

            duplicate_entry = False

    duplicate_ok = (
        not duplicate_entry
    )

    approved = all(
        [
            position_size_ok,
            exposure_ok,
            stop_loss_ok,
            take_profit_ok,
            duplicate_ok,
        ]
    )

    return {

        "approved": approved,

        "position_size_ok": position_size_ok,

        "exposure_ok": exposure_ok,

        "stop_loss_ok": stop_loss_ok,

        "take_profit_ok": take_profit_ok,

        "duplicate_ok": duplicate_ok,

        "duplicate_entry": duplicate_entry,

        "quantity": quantity,

        "estimated_cost": estimated_cost,

        "max_risk": max_risk,

        "stop_loss": stop_loss,

        "take_profit": take_profit,

        "reason": (
            "All risk checks passed."
            if approved
            else "One or more risk checks failed."
        ),

    }


# ============================================================
# PAPER ORDER
# ============================================================

def submit_paper_order():

    option = (
        st.session_state.selected_option
    )

    risk = (
        st.session_state.risk_result
    )

    if trading_client is None:

        raise RuntimeError(
            "Alpaca paper client is not connected."
        )

    if option is None:

        raise RuntimeError(
            "No option has been selected."
        )

    if risk is None:

        raise RuntimeError(
            "Risk engine has not been executed."
        )

    if not risk["approved"]:

        raise RuntimeError(
            "Risk engine has not approved this trade."
        )

    # --------------------------------------------------------
    # DUPLICATE PROTECTION
    # --------------------------------------------------------

    positions = (
        trading_client.get_all_positions()
    )

    for position in positions:

        if (
            getattr(
                position,
                "symbol",
                "",
            )
            == option["symbol"]
        ):

            raise RuntimeError(
                "Duplicate-entry protection blocked "
                "this order."
            )

    # --------------------------------------------------------
    # PAPER MARKET ORDER
    # --------------------------------------------------------

    order_request = MarketOrderRequest(

        symbol=option["symbol"],

        qty=risk["quantity"],

        side=OrderSide.BUY,

        time_in_force=TimeInForce.DAY,

    )

    order = trading_client.submit_order(
        order_data=order_request
    )

    return order


# ============================================================
# TRADE HISTORY
# ============================================================

def load_trade_history():

    if TRADE_HISTORY.exists():

        try:

            return normalize_columns(
                pd.read_csv(
                    TRADE_HISTORY
                )
            )

        except Exception:
            pass

    if TRADE_LOG.exists():

        try:

            return normalize_columns(
                pd.read_csv(
                    TRADE_LOG
                )
            )

        except Exception:
            pass

    return pd.DataFrame()


trade_history = load_trade_history()


# ============================================================
# ACCOUNT / POSITIONS / ORDERS
# ============================================================

account = get_account()

positions = []

orders = []


if trading_client is not None:

    try:

        positions = (
            trading_client.get_all_positions()
        )

    except Exception:

        positions = []

    try:

        if QueryOrderStatus:

            orders = (
                trading_client.get_orders(
                    filter=QueryOrderStatus.ALL
                )
            )

        else:

            orders = (
                trading_client.get_orders()
            )

    except Exception:

        orders = []


# ============================================================
# ACCOUNT VALUES
# ============================================================

if account:

    equity = safe_float(
        getattr(
            account,
            "equity",
            0,
        )
    )

    cash = safe_float(
        getattr(
            account,
            "cash",
            0,
        )
    )

    buying_power = safe_float(
        getattr(
            account,
            "buying_power",
            0,
        )
    )

    last_equity = safe_float(
        getattr(
            account,
            "last_equity",
            equity,
        )
    )

    day_change = (
        equity
        - last_equity
    )

else:

    equity = 0
    cash = 0
    buying_power = 0
    day_change = 0


# ============================================================
# TRADE STATS
# ============================================================

def calculate_stats(df):

    if df is None or df.empty:

        return (
            0,
            0,
            0,
            0,
            0,
            0,
        )

    pnl_col = find_pnl_column(df)

    if pnl_col is None:

        return (
            0,
            0,
            0,
            0,
            0,
            0,
        )

    values = pd.to_numeric(
        df[pnl_col],
        errors="coerce",
    ).dropna()

    if values.empty:

        return (
            0,
            0,
            0,
            0,
            0,
            0,
        )

    total = len(values)

    wins = int(
        (values > 0).sum()
    )

    losses = int(
        (values < 0).sum()
    )

    total_pnl = float(
        values.sum()
    )

    average = float(
        values.mean()
    )

    win_rate = (
        wins
        / total
        * 100
        if total
        else 0
    )

    return (
        total,
        wins,
        losses,
        total_pnl,
        average,
        win_rate,
    )


(
    completed_trades,
    winning_trades,
    losing_trades,
    total_pnl,
    average_pnl,
    win_rate,
) = calculate_stats(
    trade_history
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🚀 AlphaPilot AI")

    st.caption(
        "🤖 Autonomous AI Options Paper Trading"
    )

    st.divider()

    st.success(
        "🔒 PAPER TRADING ONLY"
    )

    st.caption(
        "Real Alpaca paper account. "
        "No live-money execution."
    )

    st.divider()

    st.subheader("🔄 Demo Pipeline")

    st.caption(
        "Run each stage sequentially."
    )

    st.write("1. 📊 Market Analysis")

    st.write("2. 🧠 AI Signal")

    st.write("3. ⚙️ Options Selection")

    st.write("4. 🛡️ Risk Check")

    st.write("5. 🚀 Paper Entry")

    st.write("6. 👁️ Monitoring")

    st.write("7. 🎯 Exit")

    st.divider()

    if trading_client:

        st.success("🟢 Alpaca Connected")

    else:

        st.error("🔴 Alpaca Offline")

    st.caption(
        now_local().strftime(
            "Updated %Y-%m-%d %H:%M:%S"
        )
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">
            🚀 AlphaPilot AI
        </div>
        <div class="hero-subtitle">
            🤖 Live AI-powered autonomous options paper-trading system
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.warning(
    "⚠️ PAPER TRADING ONLY — "
    "Execution can only reach the connected "
    "Alpaca PAPER account."
)

st.markdown(
    """
    <div class="pipeline-box">
        📊 Market Analysis
        &nbsp;→&nbsp;
        🧠 AI Signal
        &nbsp;→&nbsp;
        ⚙️ Options
        &nbsp;→&nbsp;
        🛡️ Risk
        &nbsp;→&nbsp;
        🚀 Paper Order
        &nbsp;→&nbsp;
        👁️ Monitor
        &nbsp;→&nbsp;
        🎯 Exit
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TOP CONTROLS
# ============================================================

st.header(
    "🎮 Live Trading Controls",
    anchor=False,
)

control1, control2, control3, control4, control5 = st.columns(5)


with control1:

    refresh_market = st.button(
        "🔄 Refresh Market",
        use_container_width=True,
    )


with control2:

    run_ai = st.button(
        "🧠 Run AI Analysis",
        use_container_width=True,
    )


with control3:

    scan_contracts = st.button(
        "⚙️ Scan Options",
        use_container_width=True,
    )


with control4:

    run_risk = st.button(
        "🛡️ Run Risk Check",
        use_container_width=True,
    )


with control5:

    monitor = st.button(
        "👁️ Monitor Position",
        use_container_width=True,
    )


# ============================================================
# MARKET BUTTON
# ============================================================

if refresh_market:

    try:

        with st.spinner(
            "Fetching fresh SPY market data..."
        ):

            st.session_state.market_data = (
                fetch_market_data()
            )

            st.session_state.analysis_timestamp = (
                now_local()
            )

            st.session_state.market_error = None

            st.session_state.ai_decision = None

            st.session_state.selected_option = None

            st.session_state.option_candidates = []

            st.session_state.risk_result = None

        st.success(
            "🟢 Fresh SPY market data loaded from Alpaca IEX."
        )

    except Exception as exc:

        st.session_state.market_error = str(exc)

        st.error(
            f"❌ Market data error: {exc}"
        )


# ============================================================
# AI BUTTON
# ============================================================

if run_ai:

    try:

        if st.session_state.market_data is None:

            with st.spinner(
                "Fetching fresh market data..."
            ):

                st.session_state.market_data = (
                    fetch_market_data()
                )

        st.session_state.ai_decision = (
            calculate_ai_decision(
                st.session_state.market_data
            )
        )

        st.session_state.selected_option = None

        st.session_state.option_candidates = []

        st.session_state.risk_result = None

        st.success(
            "🧠 AI analysis completed using real market data."
        )

    except Exception as exc:

        st.error(
            f"❌ AI analysis error: {exc}"
        )


# ============================================================
# OPTIONS BUTTON
# ============================================================

if scan_contracts:

    try:

        if st.session_state.market_data is None:

            st.session_state.market_data = (
                fetch_market_data()
            )

        if st.session_state.ai_decision is None:

            st.session_state.ai_decision = (
                calculate_ai_decision(
                    st.session_state.market_data
                )
            )

        if (
            st.session_state.ai_decision["signal"]
            != "BUY"
        ):

            st.session_state.selected_option = None

            st.session_state.risk_result = None

            st.warning(
                "🟡 Options scan blocked because "
                "the current AI signal is NO TRADE."
            )

        else:

            with st.spinner(
                "Scanning live SPY option contracts..."
            ):

                selected, candidates = (
                    scan_options(
                        st.session_state.market_data
                    )
                )

                option_price = get_option_price(
                    selected["symbol"]
                )

            selected["price"] = option_price

            selected["quantity"] = (
                DEFAULT_CONTRACT_QTY
            )

            st.session_state.selected_option = selected

            st.session_state.option_candidates = candidates

            st.session_state.risk_result = None

            st.success(
                "🟢 Live option scan completed."
            )

    except Exception as exc:

        st.error(
            f"❌ Option scan error: {exc}"
        )


# ============================================================
# RISK BUTTON
# ============================================================

if run_risk:

    try:

        if st.session_state.market_data is None:

            st.session_state.market_data = (
                fetch_market_data()
            )

        if st.session_state.ai_decision is None:

            st.session_state.ai_decision = (
                calculate_ai_decision(
                    st.session_state.market_data
                )
            )

        if (
            st.session_state.ai_decision["signal"]
            != "BUY"
        ):

            st.session_state.risk_result = {

                "approved": False,

                "reason": (
                    "AI signal is NO TRADE."
                ),

            }

        elif st.session_state.selected_option is None:

            st.session_state.risk_result = {

                "approved": False,

                "reason": (
                    "No option contract has been selected."
                ),

            }

        else:

            with st.spinner(
                "Running live account risk checks..."
            ):

                st.session_state.risk_result = (
                    run_risk_check()
                )

    except Exception as exc:

        st.error(
            f"❌ Risk engine error: {exc}"
        )


# ============================================================
# LIVE AI DECISION
# ============================================================

st.divider()

st.header(
    "🧠 LIVE AI DECISION",
    anchor=False,
)

market = st.session_state.market_data

decision = st.session_state.ai_decision


if market is None:

    st.info(
        "📌 Click Refresh Market to load fresh SPY data, "
        "then run AI Analysis."
    )

else:

    st.caption(
        "🕒 Fresh market data: "
        + market["timestamp"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:

        st.metric(
            "📍 SPY",
            money(market["price"]),
        )

    with m2:

        st.metric(
            "📊 SMA20",
            money(market["sma20"]),
        )

    with m3:

        st.metric(
            "📈 SMA50",
            money(market["sma50"]),
        )

    with m4:

        st.metric(
            "💪 RSI",
            f"{market['rsi']:.2f}",
        )

    with m5:

        macd_state = (
            "🟢 Bullish"
            if market["bullish_macd"]
            else "🔴 Bearish"
        )

        st.metric(
            "📉 MACD",
            macd_state,
        )

    trend_col, volume_col = st.columns(2)

    with trend_col:

        if market["bullish_trend"]:

            st.success(
                "🟢 Bullish Trend"
            )

        else:

            st.error(
                "🔴 Non-Bullish Trend"
            )

    with volume_col:

        if market["volume_confirmation"]:

            st.success(
                "🔊 Volume Confirmed"
            )

        else:

            st.warning(
                "⚠️ Volume Not Confirmed"
            )


# ============================================================
# AI SIGNAL
# ============================================================

if decision is not None:

    st.divider()

    st.subheader(
        "🤖 AI SIGNAL",
        anchor=False,
    )

    signal_col, confidence_col = st.columns(2)

    with signal_col:

        if decision["signal"] == "BUY":

            st.success(
                "🟢 BUY"
            )

        else:

            st.error(
                "🔴 NO TRADE"
            )

    with confidence_col:

        st.metric(
            "🎯 Confidence",
            f"{decision['confidence']:.0f}%",
        )

    st.subheader(
        "🔍 Why?",
        anchor=False,
    )

    for label, passed in decision["checks"].items():

        if passed:

            st.success(
                f"✅ PASS — {label}"
            )

        else:

            st.error(
                f"❌ FAIL — {label}"
            )

    st.caption(
        f"{decision['passed']} / "
        f"{decision['total']} conditions passed. "
        f"Minimum confidence: {MIN_CONFIDENCE}%."
    )


# ============================================================
# OPTIONS SELECTION
# ============================================================

st.divider()

st.header(
    "⚙️ SELECTED OPTION",
    anchor=False,
)

option = st.session_state.selected_option


if option is None:

    st.info(
        "📌 No contract selected yet. "
        "Run AI Analysis and then Scan Options."
    )

else:

    option_col1, option_col2, option_col3 = st.columns(3)

    with option_col1:

        st.metric(
            "🎫 Contract",
            option["symbol"],
        )

        st.metric(
            "💵 Strike",
            money(option["strike"]),
        )

    with option_col2:

        st.metric(
            "📅 Expiration",
            str(option["expiration"]),
        )

        st.metric(
            "⏳ Days to Expiry",
            option["dte"],
        )

    with option_col3:

        st.metric(
            "📊 Open Interest",
            option["open_interest"],
        )

        st.metric(
            "⭐ Selection Score",
            f"{option['score']:.2f}/100",
        )

    st.metric(
        "💰 Current Option Price",
        money(option["price"]),
    )


# ============================================================
# OPTION CANDIDATES
# ============================================================

if st.session_state.option_candidates:

    with st.expander(
        "📋 View Option Candidates"
    ):

        candidate_df = pd.DataFrame(
            st.session_state.option_candidates
        )

        candidate_df = candidate_df[
            [
                "symbol",
                "strike",
                "expiration",
                "dte",
                "open_interest",
                "score",
            ]
        ]

        # Static table instead of interactive dataframe.
        # This avoids canvas-like rendering artifacts.
        st.table(candidate_df)


# ============================================================
# RISK CHECK
# ============================================================

st.divider()

st.header(
    "🛡️ RISK CHECK",
    anchor=False,
)

risk = st.session_state.risk_result


if risk is None:

    st.info(
        "📌 Run Risk Check after selecting an option."
    )

else:

    if risk["approved"]:

        st.success(
            "✅ FINAL: APPROVED"
        )

    else:

        st.error(
            "❌ FINAL: REJECTED"
        )

    if "position_size_ok" in risk:

        r1, r2, r3, r4, r5 = st.columns(5)

        with r1:

            st.metric(
                "📦 Position Size",
                "PASS"
                if risk["position_size_ok"]
                else "FAIL",
            )

        with r2:

            st.metric(
                "📊 Exposure",
                "PASS"
                if risk["exposure_ok"]
                else "FAIL",
            )

        with r3:

            st.metric(
                "🛑 Stop Loss",
                "PASS"
                if risk["stop_loss_ok"]
                else "FAIL",
            )

        with r4:

            st.metric(
                "🎯 Take Profit",
                "PASS"
                if risk["take_profit_ok"]
                else "FAIL",
            )

        with r5:

            st.metric(
                "🔒 Duplicate Entry",
                "PASS"
                if risk["duplicate_ok"]
                else "BLOCKED",
            )

        st.write(
            f"🔢 Quantity: **{risk['quantity']}**"
        )

        st.write(
            "💵 Estimated cost: "
            f"**{money(risk['estimated_cost'])}**"
        )

        st.write(
            "🛡️ Maximum configured risk: "
            f"**{money(risk['max_risk'])}**"
        )

        st.write(
            "🛑 Stop Loss reference: "
            f"**{money(risk['stop_loss'])}**"
        )

        st.write(
            "🎯 Take Profit reference: "
            f"**{money(risk['take_profit'])}**"
        )

    st.caption(
        risk["reason"]
    )


# ============================================================
# PAPER ORDER
# ============================================================

st.divider()

st.header(
    "🚀 ALPACA PAPER ORDER",
    anchor=False,
)

st.error(
    "⚠️ PAPER TRADING ONLY — "
    "This control can submit an actual order "
    "to the connected Alpaca PAPER account."
)

order_ready = (

    decision is not None

    and decision["signal"] == "BUY"

    and option is not None

    and risk is not None

    and risk.get(
        "approved",
        False,
    )

)


if not order_ready:

    st.info(
        "🔒 Order locked. Required: "
        "BUY signal + selected option + approved risk check."
    )

else:

    confirm = st.checkbox(
        "I confirm this will submit an order "
        "to my Alpaca PAPER account.",
        key="paper_order_confirmation",
    )

    submit_order = st.button(
        "🚀 SUBMIT PAPER ORDER",
        type="primary",
        disabled=not confirm,
        use_container_width=True,
    )

    if submit_order:

        try:

            with st.spinner(
                "Submitting paper order to Alpaca..."
            ):

                order = submit_paper_order()

            st.session_state.last_order = order

            st.success(
                "🟢 Paper order submitted successfully."
            )

        except Exception as exc:

            st.error(
                f"❌ Paper order was not submitted: {exc}"
            )


# ============================================================
# ORDER RESULT
# ============================================================

if st.session_state.last_order is not None:

    order = st.session_state.last_order

    st.subheader(
        "📦 Latest Paper Order",
        anchor=False,
    )

    order_col1, order_col2, order_col3, order_col4 = st.columns(4)

    with order_col1:

        st.metric(
            "📊 Status",
            enum_text(
                getattr(
                    order,
                    "status",
                    "",
                )
            ).upper(),
        )

    with order_col2:

        st.metric(
            "🎫 Symbol",
            getattr(
                order,
                "symbol",
                "",
            ),
        )

    with order_col3:

        st.metric(
            "🔢 Quantity",
            getattr(
                order,
                "qty",
                "",
            ),
        )

    with order_col4:

        st.metric(
            "💵 Filled Price",
            money(
                getattr(
                    order,
                    "filled_avg_price",
                    0,
                )
            ),
        )

    st.caption(
        "🆔 Order ID: "
        + str(
            getattr(
                order,
                "id",
                "",
            )
        )
    )


# ============================================================
# LIVE POSITION MONITOR
# ============================================================

st.divider()

st.header(
    "👁️ LIVE POSITION MONITOR",
    anchor=False,
)

if monitor:

    account = get_account()

    try:

        positions = (
            trading_client.get_all_positions()
            if trading_client
            else []
        )

        st.success(
            "🟢 Monitoring data refreshed from Alpaca."
        )

    except Exception as exc:

        positions = []

        st.error(
            f"❌ Monitoring error: {exc}"
        )


if positions:

    for position in positions:

        symbol = getattr(
            position,
            "symbol",
            "",
        )

        current_price = safe_float(
            getattr(
                position,
                "current_price",
                0,
            )
        )

        entry_price = safe_float(
            getattr(
                position,
                "avg_entry_price",
                0,
            )
        )

        unrealized = safe_float(
            getattr(
                position,
                "unrealized_pl",
                0,
            )
        )

        unrealized_pct = safe_float(
            getattr(
                position,
                "unrealized_plpc",
                0,
            )
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "🎫 Contract",
                symbol,
            )

        with c2:

            st.metric(
                "📥 Entry",
                money(entry_price),
            )

        with c3:

            st.metric(
                "📈 Current",
                money(current_price),
            )

        with c4:

            # IMPORTANT:
            # No delta= here.
            # This removes Streamlit's SVG delta artifact.
            st.metric(
                "💰 Unrealized P&L",
                money(unrealized),
            )

            st.caption(
                "📊 Unrealized return: "
                f"{pct(unrealized_pct * 100)}"
            )

else:

    st.info(
        "📭 No open option positions in the Alpaca paper account."
    )

# ============================================================
# AUTOMATIC EXIT ENGINE
# ============================================================

st.subheader("🛑 Automatic Exit Engine")

st.caption(
    "AlphaPilot continuously checks open paper positions "
    "against Stop Loss and Take Profit rules."
)

if st.button(
    "🛑 RUN EXIT ENGINE",
    use_container_width=True
):

    with st.spinner("Checking positions and exit conditions..."):

        try:

            exit_results = monitor_positions()

            if not exit_results:

                st.info("No monitored open positions found.")

            else:

                for result in exit_results:

                    symbol = result.get("symbol", "Unknown")
                    status = result.get("status", "MONITORING")
                    reason = result.get("exit_reason")

                    entry = result.get("entry_price", 0)
                    current = result.get("current_price", 0)
                    stop = result.get("stop_price", 0)
                    target = result.get("target_price", 0)
                    return_pct = result.get("return_pct", 0)

                    st.markdown(f"### {symbol}")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric(
                            "Entry",
                            f"${entry:.2f}"
                        )

                    with col2:
                        st.metric(
                            "Current",
                            f"${current:.2f}"
                        )

                    with col3:
                        st.metric(
                            "Stop Loss",
                            f"${stop:.2f}"
                        )

                    with col4:
                        st.metric(
                            "Take Profit",
                            f"${target:.2f}"
                        )

                    st.write(
                        f"**Current Return:** {return_pct:.2f}%"
                    )

                    if status == "MARKET_CLOSED":

                        st.warning(
                            f"⏰ Market closed — {reason} detected. "
                            "SELL order was not submitted. "
                            "Exit saved for the next market session."
                        )

                    elif status == "EXIT_SUBMITTED":

                        st.success(
                            f"🚀 {reason} — Paper SELL order submitted."
                        )

                        if result.get("order_id"):

                            st.write(
                                f"**Order ID:** "
                                f"{result['order_id']}"
                            )

                    elif status == "EXIT_ALREADY_SUBMITTED":

                        st.info(
                            "🔒 Exit order already submitted. "
                            "Duplicate SELL prevented."
                        )

                    elif reason is None:

                        st.success(
                            "🟢 Position within risk limits."
                        )

                    else:

                        st.error(
                            f"Exit status: {status}"
                        )

        except Exception as error:

            st.error(
                f"Exit Engine Error: {error}"
            )

# ============================================================
# CURRENT ACCOUNT
# ============================================================

st.divider()

st.header(
    "📊 Trading Overview",
    anchor=False,
)

a1, a2, a3, a4 = st.columns(4)

with a1:

    # IMPORTANT:
    # No delta= here.
    st.metric(
        "💰 Account Equity",
        money(equity),
    )

    st.caption(
        "📅 Day P&L: "
        f"{money(day_change)}"
    )

with a2:

    st.metric(
        "💵 Cash",
        money(cash),
    )

with a3:

    st.metric(
        "⚡ Buying Power",
        money(buying_power),
    )

with a4:

    st.metric(
        "📂 Open Positions",
        len(positions),
    )


# ============================================================
# TRADE HISTORY
# ============================================================

st.divider()

st.header(
    "📜 Trade History",
    anchor=False,
)

if not trade_history.empty:

    source = (
        "agents/trade_history.csv"
        if TRADE_HISTORY.exists()
        else "logs/trades.csv"
    )

    st.caption(
        f"📁 Source: {source}"
    )

    # Static table instead of interactive dataframe.
    st.table(trade_history)

else:

    st.info(
        "📭 No completed trade-history records available."
    )


# ============================================================
# PERFORMANCE
# ============================================================

st.divider()

st.header(
    "📈 Performance",
    anchor=False,
)

p1, p2, p3, p4, p5 = st.columns(5)

with p1:

    st.metric(
        "💰 Total P&L",
        money(total_pnl),
    )

with p2:

    st.metric(
        "📊 Average P&L",
        money(average_pnl),
    )

with p3:

    st.metric(
        "🟢 Winning Trades",
        winning_trades,
    )

with p4:

    st.metric(
        "🔴 Losing Trades",
        losing_trades,
    )

with p5:

    st.metric(
        "🎯 Win Rate",
        pct(win_rate),
    )


# ============================================================
# P&L BREAKDOWN
# ============================================================

pnl_column = find_pnl_column(
    trade_history
)

if pnl_column:

    pnl_df = trade_history.copy()

    pnl_df[pnl_column] = pd.to_numeric(
        pnl_df[pnl_column],
        errors="coerce",
    )

    pnl_df = pnl_df.dropna(
        subset=[
            pnl_column
        ]
    )

    if not pnl_df.empty:

        pnl_df["Trade"] = range(
            1,
            len(pnl_df) + 1,
        )

        pnl_df["Cumulative P&L"] = (
            pnl_df[pnl_column]
            .cumsum()
        )

        display_pnl = pnl_df[
            [
                "Trade",
                pnl_column,
                "Cumulative P&L",
            ]
        ].copy()

        display_pnl.columns = [
            "Trade",
            "Trade P&L",
            "Cumulative P&L",
        ]

        display_pnl["Trade P&L"] = (
            display_pnl["Trade P&L"]
            .map(money)
        )

        display_pnl["Cumulative P&L"] = (
            display_pnl["Cumulative P&L"]
            .map(money)
        )

        st.subheader(
            "📊 P&L Breakdown",
            anchor=False,
        )

        # Static table instead of interactive dataframe.
        st.table(display_pnl)

        st.caption(
            "🔒 Performance shown above is derived only "
            "from recorded trade-history data. "
            "No simulated or fabricated results are displayed."
        )


# ============================================================
# AI EXPLAINABILITY
# ============================================================

st.divider()

st.header(
    "🧠 Why AlphaPilot Made This Decision",
    anchor=False,
)

if decision:

    st.write(
        f"""
AlphaPilot evaluated **{decision['total']}**
independent market conditions.

**{decision['passed']}**
conditions currently support the setup.

Calculated confidence:
**{decision['confidence']:.0f}%**

Required confidence:
**{MIN_CONFIDENCE}%**

Final signal:
**{decision['signal']}**
"""
    )

    if market:

        st.subheader(
            "🔎 Decision Inputs",
            anchor=False,
        )

        explain_col1, explain_col2 = st.columns(2)

        with explain_col1:

            st.write(
                f"📍 SPY Price: **{money(market['price'])}**"
            )

            st.write(
                f"📊 SMA20: **{money(market['sma20'])}**"
            )

            st.write(
                f"📈 SMA50: **{money(market['sma50'])}**"
            )

            st.write(
                f"💪 RSI: **{market['rsi']:.2f}**"
            )

        with explain_col2:

            macd_text = (
                "🟢 Bullish"
                if market["bullish_macd"]
                else "🔴 Bearish"
            )

            trend_text = (
                "🟢 Bullish"
                if market["bullish_trend"]
                else "🔴 Non-Bullish"
            )

            volume_text = (
                "🟢 Confirmed"
                if market["volume_confirmation"]
                else "🔴 Not Confirmed"
            )

            st.write(
                f"📉 MACD: **{macd_text}**"
            )

            st.write(
                f"📈 Trend: **{trend_text}**"
            )

            st.write(
                f"🔊 Volume: **{volume_text}**"
            )

else:

    st.info(
        "📌 Run AI Analysis to generate explainable decision data."
    )


# ============================================================
# SYSTEM STATUS
# ============================================================

st.divider()

st.header(
    "⚡ System Status",
    anchor=False,
)

s1, s2, s3 = st.columns(3)

with s1:

    if trading_client:

        st.success(
            "🟢 Alpaca Paper API"
        )

    else:

        st.error(
            "🔴 Alpaca unavailable"
        )

with s2:

    if stock_client:

        st.success(
            "🟢 SPY Market Data — IEX"
        )

    else:

        st.error(
            "🔴 Market data unavailable"
        )

with s3:

    st.success(
        "🔒 PAPER ONLY"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🚀 AlphaPilot AI • "
    "📊 Live market analysis • "
    "🧠 Explainable AI • "
    "⚙️ Options selection • "
    "🛡️ Risk controls • "
    "🏦 Alpaca paper execution • "
    "🔒 No fabricated performance"
)