# -*- coding: utf-8 -*-

# ============================================================
# AlphaPilot AI
# Institutional-Style Interactive Options Paper Dashboard
# ============================================================
# REAL ALPACA PAPER ACCOUNT
# REAL IEX MARKET DATA
# REAL OPTIONS DATA
# REAL TRADE HISTORY
# NO FABRICATED PERFORMANCE
# NO LIVE-MONEY EXECUTION
#
# Pipeline:
# Market -> AI Signal -> Option Selection -> Risk
# -> Paper Order -> Monitor -> Exit -> Performance
# ============================================================

import os
import math
from pathlib import Path
from datetime import datetime, timedelta, date, timezone
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


# ============================================================
# OPTIONAL AUTO REFRESH
# ============================================================

try:
    from streamlit_autorefresh import st_autorefresh

    AUTO_REFRESH_AVAILABLE = True
except Exception:
    st_autorefresh = None
    AUTO_REFRESH_AVAILABLE = False


# ============================================================
# ALPACA IMPORTS
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

    from alpaca.data.enums import DataFeed

    ALPACA_AVAILABLE = True
    ALPACA_IMPORT_ERROR = None

except Exception as exc:

    TradingClient = None
    StockHistoricalDataClient = None
    OptionHistoricalDataClient = None

    QueryOrderStatus = None
    OrderSide = None
    TimeInForce = None
    ContractType = None

    GetOptionContractsRequest = None
    MarketOrderRequest = None

    StockBarsRequest = None
    StockLatestTradeRequest = None
    OptionLatestQuoteRequest = None

    TimeFrame = None
    DataFeed = None

    ALPACA_AVAILABLE = False
    ALPACA_IMPORT_ERROR = str(exc)


# ============================================================
# PAGE
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

TRADE_HISTORY = (
    BASE_DIR
    / "agents"
    / "trade_history.csv"
)

TRADE_LOG = (
    BASE_DIR
    / "logs"
    / "trades.csv"
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(BASE_DIR / ".env")


# ============================================================
# CORE STRATEGY SETTINGS
# ============================================================

UNDERLYING = "SPY"

MIN_CONFIDENCE = 70

MIN_DTE = 7
MAX_DTE = 30

MAX_STRIKE_DISTANCE = 15.0

MIN_OPEN_INTEREST = 100

MAX_ACCOUNT_RISK = 0.01

DEFAULT_STOP_LOSS_PCT = 25.0
DEFAULT_TAKE_PROFIT_PCT = 50.0

DEFAULT_SCAN_INTERVAL = 30

DEFAULT_MAX_POSITION_SIZE_PCT = 5.0

DEFAULT_MAX_DAILY_DRAWDOWN_PCT = 2.0

DEFAULT_TRAILING_STOP_PCT = 0.0

DEFAULT_CONTRACT_QTY = 1


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_SETTINGS = {

    "role": "Options Officer",

    "scan_interval": DEFAULT_SCAN_INTERVAL,

    "tickers": "SPY",

    "max_position_size_pct":
        DEFAULT_MAX_POSITION_SIZE_PCT,

    "max_daily_drawdown_pct":
        DEFAULT_MAX_DAILY_DRAWDOWN_PCT,

    "stop_loss_pct":
        DEFAULT_STOP_LOSS_PCT,

    "take_profit_pct":
        DEFAULT_TAKE_PROFIT_PCT,

    "trailing_stop_pct":
        DEFAULT_TRAILING_STOP_PCT,

    "strategy": "Long Call",

}


SESSION_DEFAULTS = {

    "market_data": None,

    "ai_decision": None,

    "selected_option": None,

    "option_candidates": [],

    "risk_result": None,

    "last_order": None,

    "analysis_timestamp": None,

    "market_error": None,

    "paper_order_confirmation": False,

    "copilot_mode": True,

    "autopilot_mode": False,

    "terminal_cleared": False,

    "settings": DEFAULT_SETTINGS.copy(),

}


for key, value in SESSION_DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

html, body, [data-testid="stAppViewContainer"] {
    background: #07111f;
}

[data-testid="stHeader"] {
    background: rgba(7,17,31,0.92);
}

.block-container {
    max-width: 1580px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}

h1, h2, h3, h4 {
    color: #f8fafc !important;
    letter-spacing: -0.02em;
}

p, span, label {
    color: #cbd5e1;
}

.hero {
    background:
        radial-gradient(
            circle at 90% 10%,
            rgba(37,99,235,.18),
            transparent 30%
        ),
        linear-gradient(
            135deg,
            #0c1728,
            #101c30
        );

    border: 1px solid #22324b;
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 16px;
    box-shadow: 0 18px 45px rgba(0,0,0,.20);
}

.hero-title {
    font-size: 2.5rem;
    font-weight: 850;
    color: #ffffff;
}

.hero-subtitle {
    margin-top: 5px;
    font-size: 1rem;
    color: #8fa4bd;
}

.badges {
    margin-top: 18px;
}

.badge {
    display: inline-block;
    padding: 6px 11px;
    margin-right: 7px;
    border-radius: 999px;
    border: 1px solid #30435f;
    background: #101d30;
    color: #b8c8db;
    font-size: 12px;
    font-weight: 700;
}

.badge-live {
    border-color: #166534;
    color: #86efac;
}

.badge-paper {
    border-color: #854d0e;
    color: #fde68a;
}

.navbar {
    background: #0b1728;
    border: 1px solid #22324b;
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 18px;
}

.navbar a {
    color: #9fb0c5 !important;
    text-decoration: none;
    font-size: 13px;
    font-weight: 700;
    margin-right: 22px;
}

.navbar a:hover {
    color: #ffffff !important;
}

.pipeline {
    background: #0b1728;
    border: 1px solid #22324b;
    border-radius: 14px;
    padding: 14px;
    text-align: center;
    color: #aebed0;
    font-size: 13px;
    margin-bottom: 20px;
}

.section-card {
    background: #0b1728;
    border: 1px solid #22324b;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 16px;
}

.metric-card {
    background: linear-gradient(
        145deg,
        #0d192b,
        #0a1524
    );
    border: 1px solid #22324b;
    border-radius: 15px;
    padding: 18px;
    min-height: 118px;
}

.metric-label {
    color: #7f93ab;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
}

.metric-value {
    color: #f8fafc;
    font-size: 1.55rem;
    font-weight: 800;
    margin-top: 8px;
}

.metric-sub {
    color: #7f93ab;
    font-size: 11px;
    margin-top: 5px;
}

.status-online {
    color: #86efac;
    font-weight: 800;
}

.status-warning {
    color: #fde68a;
    font-weight: 800;
}

.status-danger {
    color: #fca5a5;
    font-weight: 800;
}

.signal-buy {
    background: rgba(22,101,52,.18);
    border: 1px solid #166534;
    border-radius: 14px;
    padding: 20px;
}

.signal-no-trade {
    background: rgba(127,29,29,.18);
    border: 1px solid #7f1d1d;
    border-radius: 14px;
    padding: 20px;
}

.signal-title {
    font-size: 1.55rem;
    font-weight: 850;
}

.recommendation {
    background:
        linear-gradient(
            145deg,
            #111d31,
            #0b1728
        );
    border: 1px solid #31435e;
    border-radius: 16px;
    padding: 20px;
}

.recommendation-title {
    color: #f8fafc;
    font-size: 1.2rem;
    font-weight: 800;
}

.small-muted {
    color: #71859d;
    font-size: 12px;
}

.warning-box {
    background: rgba(146,64,14,.12);
    border: 1px solid #854d0e;
    border-radius: 12px;
    padding: 14px;
}

.lock-box {
    background: rgba(127,29,29,.10);
    border: 1px solid #7f1d1d;
    border-radius: 12px;
    padding: 14px;
}

.success-box {
    background: rgba(22,101,52,.10);
    border: 1px solid #166534;
    border-radius: 12px;
    padding: 14px;
}

.terminal {
    background: #050b14;
    border: 1px solid #1e293b;
    border-radius: 13px;
    padding: 15px;
    font-family: Consolas, monospace;
    font-size: 12px;
    color: #9fb3c8;
}

.terminal-line {
    padding: 5px 0;
    border-bottom: 1px solid #111827;
}

.footer {
    text-align: center;
    color: #64748b;
    font-size: 12px;
    padding: 25px 0 10px;
}

div[data-testid="stMetric"] {
    background: #0b1728;
    border: 1px solid #22324b;
    border-radius: 14px;
    padding: 12px;
}

.stButton > button {
    border-radius: 9px;
    min-height: 42px;
    font-weight: 700;
}

[data-testid="stSidebar"] {
    background: #081321;
    border-right: 1px solid #1d2b40;
}

</style>
""",
    unsafe_allow_html=True,
)


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

@st.cache_data(ttl=300)
def get_option_expiration(symbol):

    if trading_client is None:
        return "—"

    try:
        contract = trading_client.get_option_contract(symbol)

        expiration = getattr(
            contract,
            "expiration_date",
            None,
        )

        if expiration is None:
            return "—"

        if isinstance(expiration, datetime):
            return expiration.strftime("%Y-%m-%d")

        if isinstance(expiration, date):
            return expiration.strftime("%Y-%m-%d")

        return str(expiration)

    except Exception:
        return "—"

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


def fmt_timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# CREDENTIALS
# ============================================================

API_KEY = get_secret(
    "ALPACA_API_KEY"
)

SECRET_KEY = get_secret(
    "ALPACA_SECRET_KEY"
)


# ============================================================
# CLIENTS
# ============================================================

trading_client = None
stock_client = None
option_client = None

alpaca_error = None


if (
    ALPACA_AVAILABLE
    and API_KEY
    and SECRET_KEY
):

    try:

        trading_client = TradingClient(
            API_KEY,
            SECRET_KEY,
            paper=True,
        )

        stock_client = (
            StockHistoricalDataClient(
                API_KEY,
                SECRET_KEY,
            )
        )

        option_client = (
            OptionHistoricalDataClient(
                API_KEY,
                SECRET_KEY,
            )
        )

    except Exception as exc:

        alpaca_error = str(exc)

else:

    if not ALPACA_AVAILABLE:

        alpaca_error = (
            "alpaca-py unavailable: "
            + str(ALPACA_IMPORT_ERROR)
        )

    elif not API_KEY:

        alpaca_error = (
            "ALPACA_API_KEY is missing."
        )

    elif not SECRET_KEY:

        alpaca_error = (
            "ALPACA_SECRET_KEY is missing."
        )


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
# POSITIONS
# ============================================================

def get_positions():

    if trading_client is None:
        return []

    try:

        return trading_client.get_all_positions()

    except Exception:

        return []


# ============================================================
# ORDERS
# ============================================================

def get_orders():
    if trading_client is None:
        return []

    try:
        request = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=100,
            nested=True,
        )

        return trading_client.get_orders(filter=request)

    except Exception as exc:
        st.error(f"❌ Alpaca orders API error: {exc}")
        return []


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
            "Alpaca IEX data-feed support unavailable."
        )

    # --------------------------------------------------------
    # LATEST TRADE
    # --------------------------------------------------------

    latest_request = (
        StockLatestTradeRequest(
            symbol_or_symbols=UNDERLYING,
            feed=DataFeed.IEX,
        )
    )

    latest_response = (
        stock_client.get_stock_latest_trade(
            latest_request
        )
    )

    latest_trade = (
        latest_response.get(
            UNDERLYING
        )
    )

    if latest_trade is None:

        raise RuntimeError(
            "No latest SPY trade returned."
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
    # DAILY BARS
    # --------------------------------------------------------

    end = datetime.now(timezone.utc)

    start = (
        end
        - timedelta(days=180)
    )

    bars_request = StockBarsRequest(
        symbol_or_symbols=UNDERLYING,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        limit=150,
        feed=DataFeed.IEX,
    )

    bars_response = (
        stock_client.get_stock_bars(
            bars_request
        )
    )

    try:

        bars = bars_response[UNDERLYING]

    except Exception:

        bars = []

    rows = []

    for bar in bars:

        rows.append(
            {
                "timestamp":
                    getattr(
                        bar,
                        "timestamp",
                        None,
                    ),

                "close":
                    safe_float(
                        getattr(
                            bar,
                            "close",
                            0,
                        )
                    ),

                "volume":
                    safe_float(
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
            "No historical SPY bars returned."
        )

    if len(df) < 50:

        raise RuntimeError(
            "At least 50 SPY daily bars are required."
        )

    # --------------------------------------------------------
    # SMA
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

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = df["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

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
        /
        avg_loss.replace(
            0,
            math.nan,
        )
    )

    df["rsi"] = (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

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

    df["macd"] = (
        ema12 - ema26
    )

    df["macd_signal"] = (
        df["macd"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    df["volume_sma20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    row = df.iloc[-1]

    sma20 = safe_float(
        row["sma20"]
    )

    sma50 = safe_float(
        row["sma50"]
    )

    rsi = safe_float(
        row["rsi"]
    )

    macd = safe_float(
        row["macd"]
    )

    macd_signal = safe_float(
        row["macd_signal"]
    )

    volume = safe_float(
        row["volume"]
    )

    volume_average = safe_float(
        row["volume_sma20"]
    )

    return {

        "price": current_price,

        "sma20": sma20,

        "sma50": sma50,

        "rsi": rsi,

        "macd": macd,

        "macd_signal": macd_signal,

        "volume": volume,

        "volume_average":
            volume_average,

        "bullish_trend": (
            current_price > sma20
            and sma20 > sma50
        ),

        "bullish_macd": (
            macd > macd_signal
        ),

        "supportive_rsi": (
            50 <= rsi <= 70
        ),

        "volume_confirmation": (
            volume >= volume_average
            if volume_average > 0
            else False
        ),

        "bars": df,

        "timestamp":
            datetime.now(),

    }


# ============================================================
# AI DECISION
# ============================================================

def calculate_ai_decision(
    market
):

    checks = {

        "Price > SMA20":
            market["price"]
            > market["sma20"],

        "SMA20 > SMA50":
            market["sma20"]
            > market["sma50"],

        "RSI supportive":
            50
            <= market["rsi"]
            <= 70,

        "MACD bullish":
            market["macd"]
            > market["macd_signal"],

        "Volume confirmation":
            (
                market["volume"]
                >= market["volume_average"]
            )
            if market["volume_average"] > 0
            else False,
    }

    passed = sum(
        bool(v)
        for v in checks.values()
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

        "confidence":
            confidence,

        "checks": checks,

        "passed":
            passed,

        "total":
            total,

    }


# ============================================================
# OPTION QUOTE
# ============================================================

def get_option_price(
    symbol
):

    if option_client is None:
        return 0.0

    try:

        request = (
            OptionLatestQuoteRequest(
                symbol_or_symbols=symbol
            )
        )

        response = (
            option_client
            .get_option_latest_quote(
                request
            )
        )

        try:

            quote = response[symbol]

        except Exception:

            quote = response.get(
                symbol
            )

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
# OPTION SCANNER
# ============================================================

def scan_options(
    market
):

    if trading_client is None:

        raise RuntimeError(
            "Trading client is not connected."
        )

    today = date.today()

    expiration_min = (
        today
        + timedelta(
            days=MIN_DTE
        )
    )

    expiration_max = (
        today
        + timedelta(
            days=MAX_DTE
        )
    )

    lower_strike = max(
        1,
        market["price"]
        - MAX_STRIKE_DISTANCE
    )

    upper_strike = (
        market["price"]
        + MAX_STRIKE_DISTANCE
    )

    request = (
        GetOptionContractsRequest(

            underlying_symbols=[
                UNDERLYING
            ],

            type=ContractType.CALL,

            expiration_date_gte=
                expiration_min,

            expiration_date_lte=
                expiration_max,

            # Alpaca request fields are strings.
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
    )

    response = (
        trading_client
        .get_option_contracts(
            request
        )
    )

    contracts = getattr(
        response,
        "option_contracts",
        []
    )

    candidates = []

    for contract in contracts:

        if not getattr(
            contract,
            "tradable",
            False,
        ):
            continue

        symbol = getattr(
            contract,
            "symbol",
            "",
        )

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

        dte = (
            expiration
            - today
        ).days

        if (
            distance
            > MAX_STRIKE_DISTANCE
        ):
            continue

        if oi < MIN_OPEN_INTEREST:
            continue

        if (
            dte < MIN_DTE
            or dte > MAX_DTE
        ):
            continue

        distance_score = max(
            0,
            100
            -
            (
                distance
                /
                MAX_STRIKE_DISTANCE
                * 100
            )
        )

        oi_score = min(
            100,
            (
                oi
                / 1000
                * 100
            )
        )

        dte_mid = (
            MIN_DTE
            + MAX_DTE
        ) / 2

        dte_score = max(
            0,
            100
            -
            (
                abs(
                    dte
                    - dte_mid
                )
                /
                (
                    MAX_DTE
                    - MIN_DTE
                )
                * 100
            )
        )

        score = (
            distance_score * 0.45
            +
            oi_score * 0.30
            +
            dte_score * 0.25
        )

        candidates.append(
            {

                "symbol":
                    symbol,

                "strike":
                    strike,

                "expiration":
                    expiration,

                "dte":
                    dte,

                "open_interest":
                    oi,

                "score":
                    round(
                        score,
                        2,
                    ),

            }
        )

    if not candidates:

        raise RuntimeError(
            "No suitable SPY CALL contracts found."
        )

    candidates.sort(
        key=lambda x:
            x["score"],
        reverse=True,
    )

    # Quote only the strongest candidates.
    quote_candidates = (
        candidates[:100]
    )

    best = None

    for candidate in quote_candidates:

        price = get_option_price(
            candidate["symbol"]
        )

        candidate["price"] = price

        if price > 0:

            if best is None:

                best = candidate

    if best is None:

        # We still return the highest-ranked
        # contract, but price remains unavailable.
        best = candidates[0]

        best["price"] = (
            get_option_price(
                best["symbol"]
            )
        )

    return (
        best,
        candidates,
    )


# ============================================================
# DAILY P&L
# ============================================================

def get_day_pnl(
    account
):

    if account is None:
        return None

    current = safe_float(
        getattr(
            account,
            "equity",
            0,
        )
    )

    raw_last = getattr(
        account,
        "last_equity",
        None,
    )

    if raw_last is None:
        return None

    try:

        last = float(
            raw_last
        )

    except Exception:

        return None

    return current - last


# ============================================================
# RISK ENGINE
# ============================================================

def run_risk_check():

    option = (
        st.session_state.selected_option
    )

    account = get_account()

    settings = (
        st.session_state.settings
    )

    decision = (
        st.session_state.ai_decision
    )

    if option is None:

        return {
            "approved": False,
            "reason":
                "No option selected.",
        }

    if account is None:

        return {
            "approved": False,
            "reason":
                "Alpaca account unavailable.",
        }

    if decision is None:

        return {
            "approved": False,
            "reason":
                "AI decision unavailable.",
        }

    if decision["signal"] != "BUY":

        return {
            "approved": False,
            "reason":
                "AI signal is NO TRADE.",
        }

    if settings["strategy"] != "Long Call":

        return {
            "approved": False,
            "reason":
                "Selected strategy is not implemented "
                "for single-leg execution.",
        }

    equity = safe_float(
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

    if equity <= 0:

        return {
            "approved": False,
            "reason":
                "Account equity unavailable.",
        }

    if option_price <= 0:

        return {
            "approved": False,
            "reason":
                "No usable option quote available.",
        }

    day_pnl = get_day_pnl(
        account
    )

    if (
        day_pnl is not None
        and day_pnl < 0
    ):

        daily_drawdown = (
            abs(day_pnl)
            / equity
            * 100
        )

    else:

        daily_drawdown = 0.0

    daily_drawdown_ok = (
        daily_drawdown
        <
        settings[
            "max_daily_drawdown_pct"
        ]
    )

    max_risk = (
        equity
        * MAX_ACCOUNT_RISK
    )

    max_exposure = (
        equity
        *
        settings[
            "max_position_size_pct"
        ]
        / 100
    )

    risk_per_contract = (
        option_price
        * 100
    )

    max_qty_risk = (
        math.floor(
            max_risk
            /
            risk_per_contract
        )
        if risk_per_contract > 0
        else 0
    )

    max_qty_exposure = (
        math.floor(
            max_exposure
            /
            risk_per_contract
        )
        if risk_per_contract > 0
        else 0
    )

    max_quantity = max(
        0,
        min(
            max_qty_risk,
            max_qty_exposure,
        )
    )

    quantity = DEFAULT_CONTRACT_QTY

    estimated_cost = (
        option_price
        * 100
        * quantity
    )

    position_size_ok = (
        estimated_cost
        <= max_exposure
    )

    account_risk_ok = (
        estimated_cost
        <= max_risk
    )

    stop_loss_pct = (
        settings[
            "stop_loss_pct"
        ]
        / 100
    )

    take_profit_pct = (
        settings[
            "take_profit_pct"
        ]
        / 100
    )

    stop_loss = (
        option_price
        *
        (
            1
            - stop_loss_pct
        )
    )

    take_profit = (
        option_price
        *
        (
            1
            + take_profit_pct
        )
    )

    stop_loss_ok = (
        0
        < stop_loss
        < option_price
    )

    take_profit_ok = (
        take_profit
        > option_price
    )

    duplicate_entry = False

    existing_positions = (
        get_positions()
    )

    for position in existing_positions:

        symbol = getattr(
            position,
            "symbol",
            "",
        )

        if symbol == option["symbol"]:

            duplicate_entry = True

    duplicate_ok = (
        not duplicate_entry
    )

    no_existing_option = True

    for position in existing_positions:

        symbol = getattr(
            position,
            "symbol",
            "",
        )

        asset_class = enum_text(
            getattr(
                position,
                "asset_class",
                "",
            )
        )

        if (
            asset_class == "us_option"
            or symbol.startswith("SPY")
        ):

            no_existing_option = False

    approved = all(
        [
            daily_drawdown_ok,
            position_size_ok,
            account_risk_ok,
            stop_loss_ok,
            take_profit_ok,
            duplicate_ok,
            no_existing_option,
            max_quantity >= quantity,
        ]
    )

    return {

        "approved":
            approved,

        "position_size_ok":
            position_size_ok,

        "account_risk_ok":
            account_risk_ok,

        "daily_drawdown_ok":
            daily_drawdown_ok,

        "stop_loss_ok":
            stop_loss_ok,

        "take_profit_ok":
            take_profit_ok,

        "duplicate_ok":
            duplicate_ok,

        "no_existing_option":
            no_existing_option,

        "duplicate_entry":
            duplicate_entry,

        "daily_drawdown":
            daily_drawdown,

        "quantity":
            quantity,

        "max_quantity":
            max_quantity,

        "estimated_cost":
            estimated_cost,

        "max_risk":
            max_risk,

        "max_exposure":
            max_exposure,

        "stop_loss":
            stop_loss,

        "take_profit":
            take_profit,

        "reason":
            (
                "All configured risk guards passed."
                if approved
                else
                "One or more risk guards failed."
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
            "Alpaca paper client unavailable."
        )

    if option is None:

        raise RuntimeError(
            "No option selected."
        )

    if risk is None:

        raise RuntimeError(
            "Risk check has not been run."
        )

    if not risk.get(
        "approved",
        False,
    ):

        raise RuntimeError(
            "Risk engine has not approved this trade."
        )

    existing_positions = (
        get_positions()
    )

    for position in existing_positions:

        symbol = getattr(
            position,
            "symbol",
            "",
        )

        if symbol == option["symbol"]:

            raise RuntimeError(
                "Duplicate-entry protection blocked order."
            )

    request = MarketOrderRequest(

        symbol=option["symbol"],

        qty=risk["quantity"],

        side=OrderSide.BUY,

        time_in_force=TimeInForce.DAY,

    )

    return trading_client.submit_order(
        order_data=request
    )


# ============================================================
# CLOSE POSITION
# ============================================================

def close_single_position(
    symbol
):

    if trading_client is None:

        raise RuntimeError(
            "Alpaca paper client unavailable."
        )

    return trading_client.close_position(
        symbol
    )


# ============================================================
# EMERGENCY EXIT
# ============================================================

def emergency_exit_all():

    if trading_client is None:

        raise RuntimeError(
            "Alpaca paper client unavailable."
        )

    return trading_client.close_all_positions(
        cancel_orders=True
    )


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


trade_history = (
    load_trade_history()
)


# ============================================================
# STATS
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

    pnl_column = (
        find_pnl_column(df)
    )

    if pnl_column is None:

        return (
            0,
            0,
            0,
            0,
            0,
            0,
        )

    values = pd.to_numeric(
        df[pnl_column],
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
# LIVE ACCOUNT SNAPSHOT
# ============================================================

account = get_account()

positions = get_positions()

orders = get_orders()

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

else:

    equity = 0.0
    cash = 0.0
    buying_power = 0.0


day_pnl = get_day_pnl(
    account
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🚀 AlphaPilot AI"
    )

    st.caption(
        "Institutional Options Officer"
    )

    st.divider()

    if trading_client:

        st.success(
            "🟢 Alpaca PAPER connected"
        )

    else:

        st.error(
            "🔴 Alpaca unavailable"
        )

    st.divider()

    st.markdown(
        "### 🎛️ Operating Mode"
    )

    st.session_state.copilot_mode = (
        st.toggle(
            "🧠 Copilot Mode",
            value=st.session_state.copilot_mode,
        )
    )

    st.session_state.autopilot_mode = (
        st.toggle(
            "🤖 Autopilot",
            value=st.session_state.autopilot_mode,
        )
    )

    if st.session_state.autopilot_mode:

        st.warning(
            "Autopilot UI enabled. "
            "Dashboard does not independently start "
            "new entry workers."
        )

    st.divider()

    st.markdown(
        "### 📌 Quick Navigation"
    )

    st.markdown(
        """
        <a href="#decision">Decision Center</a><br>
        <a href="#options">Options</a><br>
        <a href="#risk">Risk</a><br>
        <a href="#positions">Positions</a><br>
        <a href="#performance">Performance</a><br>
        <a href="#status">System Status</a>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        "### 🔒 Execution Policy"
    )

    st.caption(
        "Paper account only."
    )

    st.caption(
        "No live-money routing."
    )

    st.caption(
        "Real data only."
    )

    st.caption(
        "No fabricated performance."
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
""",
    unsafe_allow_html=True,
)


# ============================================================
# NAV
# ============================================================

st.markdown(
    """
""",
    unsafe_allow_html=True,
)


# ============================================================
# PAPER WARNING
# ============================================================

st.warning(
    "⚠️ PAPER TRADING ONLY — "
    "Any order submitted from this dashboard "
    "can reach the connected Alpaca PAPER account."
)


# ============================================================
# PIPELINE
# ============================================================

st.markdown(
    """
    <div class="pipeline">
        <span>📊 Market</span>
        <span class="arrow">→</span>
        <span>🧠 AI Signal</span>
        <span class="arrow">→</span>
        <span>⚙️ Options</span>
        <span class="arrow">→</span>
        <span>🛡️ Risk</span>
        <span class="arrow">→</span>
        <span>🚀 Paper Order</span>
        <span class="arrow">→</span>
        <span>👁️ Monitor</span>
        <span class="arrow">→</span>
        <span>🎯 Exit</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SETUP & PARAMETERS
# ============================================================

with st.expander(
    "⚙️ Setup & Trading Workflow",
    expanded=False,
):

    settings = (
        st.session_state.settings
    )

    with st.form(
        "settings_form"
    ):

        c1, c2, c3 = st.columns(3)

        with c1:

            role = st.selectbox(
                "Agent Role Mode",
                [
                    "Options Officer",
                    "Risk Officer",
                    "Market Analyst",
                ],
                index=[
                    "Options Officer",
                    "Risk Officer",
                    "Market Analyst",
                ].index(
                    settings["role"]
                ),
            )

            scan_interval = st.number_input(
                "Scan Interval (sec)",
                min_value=10,
                max_value=3600,
                value=int(
                    settings[
                        "scan_interval"
                    ]
                ),
            )

            tickers = st.text_input(
                "Target Tickers",
                value=settings[
                    "tickers"
                ],
            )

        with c2:

            max_position = st.number_input(
                "Max Position Size %",
                min_value=0.5,
                max_value=50.0,
                value=float(
                    settings[
                        "max_position_size_pct"
                    ]
                ),
                step=0.5,
            )

            max_drawdown = st.number_input(
                "Max Daily Drawdown %",
                min_value=0.5,
                max_value=25.0,
                value=float(
                    settings[
                        "max_daily_drawdown_pct"
                    ]
                ),
                step=0.5,
            )

            stop_loss = st.number_input(
                "Stop Loss %",
                min_value=1.0,
                max_value=90.0,
                value=float(
                    settings[
                        "stop_loss_pct"
                    ]
                ),
                step=1.0,
            )

        with c3:

            take_profit = st.number_input(
                "Take Profit %",
                min_value=1.0,
                max_value=200.0,
                value=float(
                    settings[
                        "take_profit_pct"
                    ]
                ),
                step=1.0,
            )

            trailing_stop = st.number_input(
                "Trailing Stop %",
                min_value=0.0,
                max_value=90.0,
                value=float(
                    settings[
                        "trailing_stop_pct"
                    ]
                ),
                step=1.0,
            )

            strategy = st.selectbox(
                "Strategy Selector",
                [
                    "Long Call",
                    "Bull Put Spread",
                    "Iron Condor",
                    "Long Put",
                ],
                index=[
                    "Long Call",
                    "Bull Put Spread",
                    "Iron Condor",
                    "Long Put",
                ].index(
                    settings["strategy"]
                ),
            )

        apply_settings = st.form_submit_button(
            "✓ APPLY PARAMETERS",
            use_container_width=True,
        )

    if apply_settings:

        st.session_state.settings = {

            "role":
                role,

            "scan_interval":
                scan_interval,

            "tickers":
                tickers,

            "max_position_size_pct":
                max_position,

            "max_daily_drawdown_pct":
                max_drawdown,

            "stop_loss_pct":
                stop_loss,

            "take_profit_pct":
                take_profit,

            "trailing_stop_pct":
                trailing_stop,

            "strategy":
                strategy,

        }

        st.success(
            "Parameters applied to this dashboard session."
        )

        st.rerun()

    if settings["strategy"] != "Long Call":

        st.warning(
            "⚠️ Multi-leg strategies are configuration-only "
            "in this dashboard. Paper execution currently "
            "supports the implemented Long Call workflow."
        )


# ============================================================
# LIVE CONTROL CENTER
# ============================================================

st.header(
    "🎮 Live Trading Controls",
    anchor=False,
)

b1, b2, b3, b4, b5 = st.columns(5)

with b1:

    refresh_market = st.button(
        "🔄 Refresh Market",
        use_container_width=True,
    )

with b2:

    run_ai = st.button(
        "🧠 Run AI Analysis",
        use_container_width=True,
    )

with b3:

    scan_contracts = st.button(
        "⚙️ Scan Options",
        use_container_width=True,
    )

with b4:

    run_risk = st.button(
        "🛡️ Run Risk Check",
        use_container_width=True,
    )

with b5:

    monitor_button = st.button(
        "👁️ Refresh Positions",
        use_container_width=True,
    )


# ============================================================
# REFRESH MARKET
# ============================================================

if refresh_market:

    try:

        with st.spinner(
            "Fetching fresh SPY data from Alpaca IEX..."
        ):

            st.session_state.market_data = (
                fetch_market_data()
            )

        st.session_state.analysis_timestamp = (
            datetime.now()
        )

        st.session_state.market_error = None

        st.session_state.ai_decision = None

        st.session_state.selected_option = None

        st.session_state.option_candidates = []

        st.session_state.risk_result = None

        st.success(
            "🟢 Fresh SPY market data loaded."
        )

    except Exception as exc:

        st.session_state.market_error = str(
            exc
        )

        st.error(
            f"❌ Market data error: {exc}"
        )


# ============================================================
# AI
# ============================================================

if run_ai:

    try:

        if (
            st.session_state.market_data
            is None
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
            "🧠 AI decision generated from fresh market data."
        )

    except Exception as exc:

        st.error(
            f"❌ AI analysis failed: {exc}"
        )


# ============================================================
# OPTION SCAN
# ============================================================

if scan_contracts:

    try:

        if (
            st.session_state.market_data
            is None
        ):

            st.session_state.market_data = (
                fetch_market_data()
            )

        if (
            st.session_state.ai_decision
            is None
        ):

            st.session_state.ai_decision = (
                calculate_ai_decision(
                    st.session_state.market_data
                )
            )

        decision_now = (
            st.session_state.ai_decision
        )

        if decision_now["signal"] != "BUY":

            st.session_state.selected_option = None

            st.session_state.option_candidates = []

            st.session_state.risk_result = None

            st.warning(
                "🟡 Options scan blocked — "
                "current AI signal is NO TRADE."
            )

        else:

            with st.spinner(
                "Scanning live SPY CALL contracts..."
            ):

                selected, candidates = (
                    scan_options(
                        st.session_state.market_data
                    )
                )

            st.session_state.selected_option = selected

            st.session_state.option_candidates = candidates

            st.session_state.risk_result = None

            st.success(
                "🟢 Live option selection completed."
            )

    except Exception as exc:

        st.error(
            f"❌ Option scanner error: {exc}"
        )


# ============================================================
# RISK ENGINE TRIGGER & IMPLEMENTATION
# ============================================================

if run_risk:
    try:
        # Step 1: Ensure Market Data is available
        if st.session_state.get("market_data") is None:
            st.session_state.market_data = fetch_market_data()

        # Step 2: Ensure AI Decision is calculated
        if st.session_state.get("ai_decision") is None:
            if st.session_state.market_data is not None:
                st.session_state.ai_decision = calculate_ai_decision(
                    st.session_state.market_data
                )
            else:
                st.warning("⚠️ Market data unavailable to calculate AI decision.")

        # Step 3: Ensure an Option is selected for Risk Calculation
        if st.session_state.get("selected_option") is None:
            best_opt, candidates = scan_options(st.session_state.market_data)
            st.session_state.selected_option = best_opt
            st.session_state.option_candidates = candidates

        # Step 4: Run Risk Engine Check
        st.session_state.risk_result = run_risk_check()
        
        if st.session_state.risk_result and st.session_state.risk_result.get("approved"):
            st.success("✅ Risk Check Passed: Order parameters within risk thresholds.")
        else:
            reason = st.session_state.risk_result.get("reason", "Unknown") if st.session_state.risk_result else "No result"
            st.error(f"❌ Risk Check Failed: {reason}")

    except Exception as exc:
        st.error(f"❌ Risk engine error: {exc}")
# ============================================================
# DECISION CENTER
# ============================================================

st.markdown(
    '<div id="decision"></div>',
    unsafe_allow_html=True,
)

st.divider()

st.header(
    "🧠 Decision Center",
    anchor=False,
)

market = (
    st.session_state.market_data
)

decision = (
    st.session_state.ai_decision
)


if market is None:

    st.info(
        "Run Market Refresh or AI Analysis "
        "to load live SPY decision data."
    )

else:

    st.caption(
        "Fresh market timestamp: "
        +
        market["timestamp"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:

        st.metric(
            "SPY",
            money(
                market["price"]
            ),
        )

    with m2:

        st.metric(
            "SMA20",
            money(
                market["sma20"]
            ),
        )

    with m3:

        st.metric(
            "SMA50",
            money(
                market["sma50"]
            ),
        )

    with m4:

        st.metric(
            "RSI",
            f"{market['rsi']:.2f}",
        )

    with m5:

        st.metric(
            "MACD",
            (
                "🟢 Bullish"
                if market["bullish_macd"]
                else
                "🔴 Bearish"
            ),
        )


if decision is not None:

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )
   
    d1, d2 = st.columns(
        [1.4, 1]
    )

    with d1:

        if (
            decision["signal"]
            == "BUY"
        ):

            st.success(
                "🟢 BUY SIGNAL\n\n"
                "Technical conditions meet the configured confidence threshold."
            )

        else:

            st.error(
                "🔴 NO TRADE\n\n"
                "Current conditions do not meet the minimum confidence requirement."
            )
    with d2:

        st.metric(
            "Signal Confidence",
            f"{decision['confidence']:.0f}%",
            help=(
                "This is technical-rule confidence, "
                "not a calibrated probability of profit."
            ),
        )

    st.subheader("🔍 Signal Evidence")

    e1, e2 = st.columns(2)

    check_items = list(
        decision["checks"].items()
    )

    with e1:

        for label, passed in check_items[:3]:

            if passed:

                st.success(
                    f"PASS — {label}"
                )

            else:

                st.error(
                    f"FAIL — {label}"
                )

    with e2:

        for label, passed in check_items[3:]:

            if passed:

                st.success(
                    f"PASS — {label}"
                )

            else:

                st.error(
                    f"FAIL — {label}"
                )

    st.caption(
        f"{decision['passed']} / "
        f"{decision['total']} conditions passed. "
        f"Required confidence: {MIN_CONFIDENCE}%."
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
# COPILOT RECOMMENDATION
# ============================================================

st.subheader(
    "🤖 Copilot Trade Recommendation"
)

option = (
    st.session_state.selected_option
)


if (
    st.session_state.copilot_mode
    and decision is not None
    and decision["signal"] == "BUY"
    and option is not None
):

    policy_rr = (
        st.session_state.settings[
            "take_profit_pct"
        ]
        /
        st.session_state.settings[
            "stop_loss_pct"
        ]
    )

    st.markdown(
        f"""
<div class="recommendation">

    <div class="recommendation-title">
        🎯 Proposed Paper Trade
    </div>

    <br>

    <b>Ticker:</b> SPY<br>
    <b>Contract:</b> {option['symbol']}<br>
    <b>Strike:</b> {money(option['strike'])}<br>
    <b>Option Expiration:</b> {option.get('expiration', '—')}<br>
    <b>Option Type:</b> CALL<br>
    <b>Signal Confidence:</b>
        {decision['confidence']:.0f}%<br>
    <b>Policy Risk/Reward:</b>
        {policy_rr:.2f}:1<br>
    <b>Estimated Win Probability:</b>
        Not calibrated

    <br><br>

    <span class="small-muted">
        Win probability is intentionally not fabricated.
        The current system produces technical confidence,
        not a statistically calibrated probability of profit.
    </span>

</div>
""",
        unsafe_allow_html=True,
    )

else:

    st.info(
        "Copilot recommendation will appear only "
        "after a BUY signal and valid option selection."
    )


# ============================================================
# OPTIONS
# ============================================================

st.markdown(
    '<div id="options"></div>',
    unsafe_allow_html=True,
)

st.divider()

st.header(
    "⚙️ Option Selection",
    anchor=False,
)

if option is None:

    st.info(
        "No contract selected. "
        "A valid BUY signal is required before "
        "the live SPY option scanner can select a contract."
    )

else:

    o1, o2, o3, o4 = st.columns(4)

    with o1:

        st.metric(
            "Contract",
            option["symbol"],
        )

    with o2:

        st.metric(
            "Strike",
            money(
                option["strike"]
            ),
        )

    with o3:

        st.metric(
            "Option Expiration",
            str(
              option.get("expiration", "—")
            ),
        )

    with o4:

        st.metric(
            "DTE",
            option["dte"],
        )

    o5, o6, o7, o8 = st.columns(4)

    with o5:

        st.metric(
            "CALL",
            "Long",
        )

    with o6:

        st.metric(
            "Open Interest",
            option[
                "open_interest"
            ],
        )

    with o7:

        st.metric(
            "Selection Score",
            f"{option['score']:.2f}",
        )

    with o8:

        st.metric(
            "Option Price",
            money(
                option.get(
                    "price",
                    0,
                )
            ),
        )


# ============================================================
# CANDIDATES
# ============================================================

if (
    st.session_state.option_candidates
):

    with st.expander(
        "📋 Active Option Candidates"
    ):

        candidate_df = pd.DataFrame(
            st.session_state.option_candidates
        )

        columns = [
            "symbol",
            "strike",
            "expiration",
            "dte",
            "open_interest",
            "score",
        ]

        candidate_df = candidate_df[
            [
                c
                for c in columns
                if c in candidate_df.columns
            ]
        ]

        st.dataframe(
            candidate_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# RISK
# ============================================================

st.markdown(
    '<div id="risk"></div>',
    unsafe_allow_html=True,
)

st.divider()

st.header(
    "🛡️ Risk Guards",
    anchor=False,
)

risk = (
    st.session_state.risk_result
)


if risk is None:

    st.info(
        "Run Risk Check after a contract has been selected."
    )

else:

    if risk.get("approved", False):
        st.success(
            "🟢 FINAL RISK DECISION: APPROVED\n\n"
            "All configured risk guards passed."
        )
    else:
        st.error(
            "🔴 FINAL RISK DECISION: REJECTED\n\n"
            "One or more guards failed."
        )

    r1, r2, r3, r4 = st.columns(4)

    with r1:

        st.metric(
            "Position Size",
            (
                "PASS"
                if risk.get(
                    "position_size_ok",
                    False,
                )
                else
                "FAIL"
            ),
        )

    with r2:

        st.metric(
            "Account Risk",
            (
                "PASS"
                if risk.get(
                    "account_risk_ok",
                    False,
                )
                else
                "FAIL"
            ),
        )

    with r3:

        st.metric(
            "Daily Drawdown",
            (
                "PASS"
                if risk.get(
                    "daily_drawdown_ok",
                    False,
                )
                else
                "BLOCKED"
            ),
        )

    with r4:

        st.metric(
            "Duplicate Guard",
            (
                "PASS"
                if risk.get(
                    "duplicate_ok",
                    False,
                )
                else
                "BLOCKED"
            ),
        )

    r5, r6, r7, r8 = st.columns(4)

    with r5:

        st.metric(
            "Quantity",
            risk.get(
                "quantity",
                0,
            ),
        )

    with r6:

        st.metric(
            "Estimated Cost",
            money(
                risk.get(
                    "estimated_cost",
                    0,
                )
            ),
        )

    with r7:

        st.metric(
            "Stop Loss",
            money(
                risk.get(
                    "stop_loss",
                    0,
                )
            ),
        )

    with r8:

        st.metric(
            "Take Profit",
            money(
                risk.get(
                    "take_profit",
                    0,
                )
            ),
        )

    st.caption(
        risk.get(
            "reason",
            "",
        )
    )


# ============================================================
# PAPER EXECUTION
# ============================================================

st.divider()

st.header(
    "🚀 Alpaca Paper Execution",
    anchor=False,
)

st.error(
    "⚠️ REAL PAPER ORDER CONTROL — "
    "Submitting this order sends an actual order "
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

    st.warning(
        "🔒 ORDER LOCKED\n\n"
        "Required:\n"
        "BUY signal → selected option → approved risk check"
    )

else:

    confirmation = st.checkbox(
        "I understand this submits an order to my Alpaca PAPER account.",
        key="paper_order_confirmation",
    )

    submit = st.button(
        "🚀 SUBMIT PAPER ORDER",
        type="primary",
        disabled=not confirmation,
        use_container_width=True,
    )

    if submit:

        try:

            with st.spinner(
                "Submitting paper order..."
            ):

                order = (
                    submit_paper_order()
                )

            st.session_state.last_order = (
                order
            )

            st.success(
                "🟢 Paper order submitted to Alpaca."
            )

        except Exception as exc:

            st.error(
                f"❌ Order rejected: {exc}"
            )


# ============================================================
# LATEST ORDER
# ============================================================

if (
    st.session_state.last_order
    is not None
):

    st.subheader(
        "📦 Latest Paper Order"
    )

    latest_order = (
        st.session_state.last_order
    )

    q1, q2, q3, q4 = st.columns(4)

    with q1:

        st.metric(
            "Status",
            enum_text(
                getattr(
                    latest_order,
                    "status",
                    "",
                )
            ).upper(),
        )

    with q2:

        st.metric(
            "Symbol",
            getattr(
                latest_order,
                "symbol",
                "",
            ),
        )

    with q3:

        st.metric(
            "Quantity",
            getattr(
                latest_order,
                "qty",
                "",
            ),
        )

    with q4:

        st.metric(
            "Filled Price",
            money(
                getattr(
                    latest_order,
                    "filled_avg_price",
                    0,
                )
            ),
        )

    st.caption(
        "Order ID: "
        +
        str(
            getattr(
                latest_order,
                "id",
                "",
            )
        )
    )


# ============================================================
# RECENT ALPACA PAPER ORDERS
# ============================================================

st.markdown(
    '<div id="orders"></div>',
    unsafe_allow_html=True,
)

st.divider()
st.header(
    "📋 Recent Alpaca Paper Orders",
    anchor=False,
)

if not orders:
    st.info(
        "No Alpaca PAPER orders found."
    )
else:
    recent_order_rows = []

    def order_timestamp(order, field):
        value = getattr(order, field, None)
        if value is None:
            return "—"
        try:
            return value.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            return str(value)

    def order_number(value, decimals=2):
        try:
            return f"{float(value):.{decimals}f}"
        except Exception:
            return "—"

    sorted_orders = sorted(
        orders,
        key=lambda order: getattr(order, "submitted_at", None) or datetime.min,
        reverse=True,
    )

    for order in sorted_orders[:10]:
        symbol = getattr(order, "symbol", "")

        option_expiration = get_option_expiration(symbol)

        order_expires_at = getattr(
            order,
            "expires_at",
            None,
        )

        recent_order_rows.append(
            {
                "Asset": symbol or "—",

                "Order Type": enum_text(
                    getattr(order, "order_type", "")
                ),

                "Side": enum_text(
                    getattr(order, "side", "")
                ),

                "Qty": order_number(
                    getattr(order, "qty", 0)
                ),

                "Filled Qty": order_number(
                    getattr(order, "filled_qty", 0)
                ),

                "Avg. Fill Price": (
                    money(
                        getattr(
                            order,
                            "filled_avg_price",
                            0,
                        )
                    )
                    if getattr(
                        order,
                        "filled_avg_price",
                        None,
                    ) is not None
                    else "—"
                ),

                "Status": enum_text(
                    getattr(order, "status", "")
                ),

                "Option Expiration": option_expiration,

                "Submitted At": order_timestamp(
                    order,
                    "submitted_at",
                ),

                "Filled At": order_timestamp(
                    order,
                    "filled_at",
                ),

                "Order Expires At": order_timestamp(
                    order,
                    "expires_at",
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(recent_order_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Source: Alpaca PAPER account API. Showing the 10 most recent orders; no static or fabricated order data is used."
    )


# ============================================================
# POSITION MANAGER
# ============================================================

st.markdown(
    '<div id="positions"></div>',
    unsafe_allow_html=True,
)

st.divider()

st.header(
    "👁️ Position Manager",
    anchor=False,
)

active_option_positions = []

for position in positions:

    symbol = getattr(
        position,
        "symbol",
        "",
    )

    asset_class = enum_text(
        getattr(
            position,
            "asset_class",
            "",
        )
    )

    if (
        asset_class == "us_option"
        or symbol.startswith("SPY")
    ):

        active_option_positions.append(
            position
        )


tab_active, tab_closed = st.tabs(
    [
        f"Active Contracts ({len(active_option_positions)})",
        "Closed Trades / Realized P&L",
    ]
)


# ============================================================
# ACTIVE CONTRACTS
# ============================================================

with tab_active:

    if not active_option_positions:

        st.info(
            "No active SPY option contracts."
        )

    else:

        rows = []

        for position in active_option_positions:

            symbol = getattr(
                position,
                "symbol",
                "",
            )

            qty = getattr(
                position,
                "qty",
                "",
            )

            entry = safe_float(
                getattr(
                    position,
                    "avg_entry_price",
                    0,
                )
            )

            current = safe_float(
                getattr(
                    position,
                    "current_price",
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

            return_pct = (
                safe_float(
                    getattr(
                        position,
                        "unrealized_plpc",
                        0,
                    )
                )
                * 100
            )

            rows.append(
                {
                    "Contract":
                        symbol,

                    "Quantity":
                        qty,

                    "Entry":
                        money(entry),

                    "Current":
                        money(current),

                    "Unrealized P&L":
                        money(unrealized),

                    "Return":
                        pct(return_pct),

                    "Action":
                        "Managed",
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Positions are sourced directly from the Alpaca PAPER account."
        )

        st.warning(
            "Manual position closing is available below. "
            "Use carefully if the automatic exit worker is also running."
        )

        for position in active_option_positions:

            symbol = getattr(
                position,
                "symbol",
                "",
            )

            with st.expander(
                f"Manage {symbol}"
            ):

                confirm_close = st.checkbox(
                    "Confirm I want to close this paper position.",
                    key=f"confirm_close_{symbol}",
                )

                if st.button(
                    f"Close {symbol}",
                    key=f"close_{symbol}",
                    disabled=not confirm_close,
                    use_container_width=True,
                ):

                    try:

                        close_single_position(
                            symbol
                        )

                        st.success(
                            f"Close request submitted for {symbol}."
                        )

                    except Exception as exc:

                        st.error(
                            f"Close request failed: {exc}"
                        )


# ============================================================
# CLOSED TRADES
# ============================================================

with tab_closed:

    if trade_history.empty:

        st.info(
            "No completed trade-history records."
        )

    else:

        st.caption(
            "Source: agents/trade_history.csv"
        )

        st.dataframe(
            trade_history,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# EMERGENCY EXIT
# ============================================================

st.subheader(
    "🚨 Emergency Exit All Positions"
)

st.markdown(
    """
<div class="warning-box">

<b>HIGH-IMPACT PAPER ACTION</b>

<br>

This action closes all positions in the connected
Alpaca PAPER account and cancels open orders.

</div>
""",
    unsafe_allow_html=True,
)

emergency_confirm = st.checkbox(
    "I understand this will close ALL paper positions and cancel open orders.",
    key="emergency_confirmation",
)

if st.button(
    "🚨 CLOSE ALL PAPER POSITIONS",
    disabled=not emergency_confirm,
    use_container_width=True,
):

    try:

        with st.spinner(
            "Closing all paper positions..."
        ):

            result = emergency_exit_all()

        st.success(
            "Emergency close request submitted."
        )

        st.write(
            result
        )

    except Exception as exc:

        st.error(
            f"Emergency exit failed: {exc}"
        )


# ============================================================
# PERFORMANCE
# ============================================================

st.markdown(
    '<div id="performance"></div>',
    unsafe_allow_html=True,
)

st.divider()

st.header(
    "📈 Performance Intelligence",
    anchor=False,
)

p1, p2, p3, p4, p5 = st.columns(5)

with p1:

    st.metric(
        "Total P&L",
        money(
            total_pnl
        ),
    )

with p2:

    st.metric(
        "Average P&L",
        money(
            average_pnl
        ),
    )

with p3:

    st.metric(
        "Winning Trades",
        winning_trades,
    )

with p4:

    st.metric(
        "Losing Trades",
        losing_trades,
    )

with p5:

    st.metric(
        "Win Rate",
        pct(
            win_rate
        ),
    )


pnl_column = (
    find_pnl_column(
        trade_history
    )
)


if pnl_column:

    pnl_df = (
        trade_history.copy()
    )

    pnl_df[pnl_column] = (
        pd.to_numeric(
            pnl_df[pnl_column],
            errors="coerce",
        )
    )

    pnl_df = (
        pnl_df
        .dropna(
            subset=[
                pnl_column
            ]
        )
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
            display_pnl[
                "Trade P&L"
            ].map(money)
        )

        display_pnl["Cumulative P&L"] = (
            display_pnl[
                "Cumulative P&L"
            ].map(money)
        )

        st.subheader(
            "📊 Realized P&L Breakdown"
        )

        st.dataframe(
            display_pnl,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "🔒 Performance is calculated only from recorded trade-history data. "
            "No simulated or fabricated results are included."
        )


# ============================================================
# AI EXPLAINABILITY
# ============================================================

st.divider()

st.header(
    "🧠 Explainable AI",
    anchor=False,
)

if (
    decision is None
    or market is None
):

    st.info(
        "Run AI Analysis to generate explainable decision data."
    )

else:

    x1, x2 = st.columns(2)

    with x1:

        st.markdown(
            f"""
            **Conditions evaluated:** {decision['total']}

            **Conditions passed:** {decision['passed']}

            **Technical confidence:** {decision['confidence']:.0f}%

            **Required threshold:** {MIN_CONFIDENCE}%

            **Final signal:** {decision['signal']}
            """
        )

    with x2:

        st.markdown(
            f"""
            **SPY:** {money(market['price'])}

            **SMA20:** {money(market['sma20'])}

            **SMA50:** {money(market['sma50'])}

            **RSI:** {market['rsi']:.2f}

            **MACD:** {
                'Bullish'
                if market['bullish_macd']
                else
                'Bearish'
            }

            **Volume:** {
                'Confirmed'
                if market['volume_confirmation']
                else
                'Not Confirmed'
            }
            """
        )


# ============================================================
# SYSTEM STATUS
# ============================================================

st.markdown(
    '<div id="status"></div>',
    unsafe_allow_html=True,
)

st.divider()

st.header(
    "⚡ System Status",
    anchor=False,
)

s1, s2, s3, s4 = st.columns(4)

with s1:

    if trading_client:

        st.success(
            "🟢 Alpaca Paper API"
        )

    else:

        st.error(
            "🔴 Alpaca API unavailable"
        )

with s2:

    if stock_client:

        st.success(
            "🟢 SPY IEX Market Data"
        )

    else:

        st.error(
            "🔴 IEX unavailable"
        )

with s3:

    st.success(
        "🔒 PAPER ONLY"
    )

with s4:

    st.success(
        "🔄 Auto Refresh Ready"
    )

    if st.button(
        "↻ Manual Refresh",
        use_container_width=True,
        key="system_manual_refresh",
    ):

        try:

            st.session_state.market_data = (
                fetch_market_data()
            )

            st.session_state.analysis_timestamp = (
                datetime.now()
            )

            st.session_state.market_error = None

            st.session_state.ai_decision = None
            st.session_state.selected_option = None
            st.session_state.option_candidates = []
            st.session_state.risk_result = None

            st.rerun()

        except Exception as exc:

            st.error(
                f"❌ Refresh failed: {exc}"
            )


# ============================================================
# ACCOUNT OVERVIEW
# ============================================================

st.divider()

st.header(
    "📊 Trading Overview",
    anchor=False,
)

a1, a2, a3, a4, a5 = st.columns(5)

with a1:

    st.metric(
        "💰 Equity",
        money(
            equity
        ),
    )

with a2:

    if day_pnl is None:

        st.metric(
            "📅 Day P&L",
            "N/A",
        )

    else:

        st.metric(
            "📅 Day P&L",
            money(
                day_pnl
            ),
        )

with a3:

    st.metric(
        "💵 Cash",
        money(
            cash
        ),
    )

with a4:

    st.metric(
        "⚡ Buying Power",
        money(
            buying_power
        ),
    )

with a5:

    st.metric(
        "📂 Open Positions",
        len(
            positions
        ),
    )


# ============================================================
# TRADE TERMINAL
# ============================================================

st.divider()

st.header(
    "🧠 AI Thought Terminal",
    anchor=False,
)

terminal_col1, terminal_col2, terminal_col3 = st.columns(
    [1, 1, 1],
    vertical_alignment="bottom",
)

with terminal_col1:

    terminal_filter = st.selectbox(
        "Filter",
        [
            "All",
            "Market",
            "AI",
            "Options",
            "Risk",
            "Execution",
            "System",
        ],
        label_visibility="visible",
    )

with terminal_col2:

    clear_terminal = st.button(
        "🧹 Clear Terminal",
        use_container_width=True,
    )

with terminal_col3:

    st.markdown(
        """
        <div style="
            height: 42px;
            display: flex;
            align-items: center;
            padding-left: 8px;
            color: #71859d;
            font-size: 12px;
        ">
            Terminal reflects current dashboard events.
        </div>
        """,
        unsafe_allow_html=True,
    )

if clear_terminal:

    st.session_state.terminal_cleared = True


terminal_events = []


if market:

    terminal_events.append(
        (
            "Market",
            "LIVE",
            f"SPY market snapshot loaded at "
            f"{market['timestamp'].strftime('%H:%M:%S')}",
        )
    )


if decision:

    terminal_events.append(
        (
            "AI",
            decision["signal"],
            f"Technical confidence "
            f"{decision['confidence']:.0f}% "
            f"from {decision['passed']}/"
            f"{decision['total']} conditions",
        )
    )


if option:

    terminal_events.append(
        (
            "Options",
            "SELECTED",
            f"{option['symbol']} | "
            f"score {option['score']:.2f}",
        )
    )


if risk:

    terminal_events.append(
        (
            "Risk",
            (
                "APPROVED"
                if risk.get(
                    "approved",
                    False,
                )
                else
                "REJECTED"
            ),
            risk.get(
                "reason",
                "",
            ),
        )
    )


if st.session_state.last_order:

    terminal_events.append(
        (
            "Execution",
            "ORDER",
            str(
                getattr(
                    st.session_state.last_order,
                    "id",
                    "",
                )
            ),
        )
    )


terminal_events.append(
    (
        "System",
        "PAPER",
        "Connected execution environment is Alpaca PAPER.",
    )
)


if (
    not st.session_state.terminal_cleared
):

    if terminal_filter != "All":

        terminal_events = [
            event
            for event in terminal_events
            if event[0]
            == terminal_filter
        ]

    terminal_html = ""

    for tag, level, message in terminal_events:

        terminal_html += (
            '<div class="terminal-line">'
            f'[{fmt_timestamp()}] '
            f'[{tag}] '
            f'[{level}] '
            f'{message}'
            '</div>'
        )

    st.markdown(
        f"""
        <div class="terminal">
            {terminal_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.info(
        "Terminal cleared for this view."
    )

    if st.button(
        "↩ Restore Live Terminal"
    ):

        st.session_state.terminal_cleared = False

        st.rerun()


# ============================================================
# AUTO REFRESH
# ============================================================

if AUTO_REFRESH_AVAILABLE:

    st_autorefresh(
        interval=(
            st.session_state.settings[
                "scan_interval"
            ]
            * 1000
        ),
        key="alphapilot_live_refresh",
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer">

    🚀 AlphaPilot AI
    • Live Alpaca market data
    • Explainable technical AI
    • Options intelligence
    • Risk governance
    • Paper execution
    • Position monitoring
    • Realized performance tracking
    • No fabricated results

</div>
""",
    unsafe_allow_html=True,
)