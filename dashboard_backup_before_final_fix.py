# dashboard.py

import os
import json
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOptionContractsRequest,
    GetOrdersRequest,
    MarketOrderRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    ContractType,
    QueryOrderStatus,
)

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import (
    StockLatestTradeRequest,
    StockBarsRequest,
    OptionLatestQuoteRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

SYMBOL = "SPY"

MIN_CONFIDENCE = 70.0

MAX_ACCOUNT_RISK = 0.01
MAX_EXPOSURE = 0.05

STOP_LOSS_PCT = 0.25
TAKE_PROFIT_PCT = 0.50

MIN_DTE = 7
MAX_DTE = 30

MAX_STRIKE_DISTANCE = 15.0
MIN_OPEN_INTEREST = 100

LOG_FILE = Path("agents") / "trade_history.csv"
STATE_FILE = Path("agents") / "trade_state.json"


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
# CSS
# ============================================================

st.markdown(
    """
<style>

html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont,
                 "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 20% 0%,
            rgba(59,130,246,0.08),
            transparent 28%
        ),
        radial-gradient(
            circle at 90% 10%,
            rgba(16,185,129,0.06),
            transparent 25%
        ),
        #070b12;
    color: #e5e7eb;
}

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}


/* =========================================================
   HERO
   ========================================================= */

.hero {
    padding: 28px 32px;
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 22px;
    background:
        linear-gradient(
            135deg,
            rgba(15,23,42,0.96),
            rgba(10,15,25,0.96)
        );
    box-shadow:
        0 20px 60px rgba(0,0,0,0.35),
        inset 0 1px 0 rgba(255,255,255,0.03);
    margin-bottom: 22px;
}

.hero-title {
    font-size: 38px;
    font-weight: 800;
    letter-spacing: -1.4px;
    color: #f8fafc;
}

.hero-subtitle {
    margin-top: 5px;
    font-size: 15px;
    color: #94a3b8;
}

.status-row {
    display: flex;
    gap: 9px;
    margin-top: 17px;
    flex-wrap: wrap;
}

.badge {
    display: inline-flex;
    align-items: center;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .5px;
    border: 1px solid;
}

.badge-green {
    color: #34d399;
    background: rgba(16,185,129,.09);
    border-color: rgba(52,211,153,.25);
}

.badge-blue {
    color: #60a5fa;
    background: rgba(59,130,246,.09);
    border-color: rgba(96,165,250,.25);
}

.badge-orange {
    color: #fbbf24;
    background: rgba(245,158,11,.09);
    border-color: rgba(251,191,36,.25);
}

.badge-red {
    color: #f87171;
    background: rgba(239,68,68,.09);
    border-color: rgba(248,113,113,.25);
}


/* =========================================================
   SECTION HEADERS
   ========================================================= */

.section-title {
    font-size: 18px;
    font-weight: 750;
    color: #f8fafc;
    margin: 18px 0 12px;
}

.section-subtitle {
    font-size: 12px;
    color: #64748b;
    margin-top: -7px;
    margin-bottom: 13px;
}


/* =========================================================
   METRIC CARDS
   ========================================================= */

.metric-card {
    background:
        linear-gradient(
            145deg,
            rgba(15,23,42,.92),
            rgba(9,14,23,.92)
        );
    border: 1px solid rgba(148,163,184,.13);
    border-radius: 17px;
    padding: 18px 19px;
    min-height: 104px;
    box-shadow: 0 12px 30px rgba(0,0,0,.18);
}

.metric-label {
    color: #64748b;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .8px;
    font-weight: 700;
}

.metric-value {
    color: #f8fafc;
    font-size: 25px;
    font-weight: 800;
    margin-top: 7px;
    letter-spacing: -.5px;
}

.metric-value.negative {
    color: #f87171;
}

.metric-value.positive {
    color: #34d399;
}


/* =========================================================
   PANELS
   ========================================================= */

.panel {
    background: rgba(10,15,24,.90);
    border: 1px solid rgba(148,163,184,.12);
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 14px 38px rgba(0,0,0,.20);
}

.panel-title {
    font-size: 14px;
    font-weight: 750;
    color: #f1f5f9;
    margin-bottom: 4px;
}

.small-muted {
    color: #64748b;
    font-size: 11px;
    line-height: 1.55;
}


/* =========================================================
   MARKET
   ========================================================= */

.market-open {
    color: #34d399;
    font-weight: 800;
}

.market-closed {
    color: #fbbf24;
    font-weight: 800;
}

.market-price {
    font-size: 30px;
    font-weight: 800;
    color: #f8fafc;
}


/* =========================================================
   WORKFLOW
   ========================================================= */

.workflow {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.workflow-card {
    background: rgba(15,23,42,.62);
    border: 1px solid rgba(148,163,184,.12);
    border-radius: 15px;
    padding: 16px;
    min-height: 125px;
}

.workflow-number {
    font-size: 10px;
    color: #64748b;
    font-weight: 800;
    letter-spacing: 1px;
}

.workflow-name {
    font-size: 13px;
    color: #e2e8f0;
    font-weight: 700;
    margin-top: 9px;
    line-height: 1.4;
}

.workflow-status {
    margin-top: 13px;
    font-size: 11px;
}

.status-good {
    color: #34d399;
}

.status-info {
    color: #60a5fa;
}

.status-warn {
    color: #fbbf24;
}

.status-bad {
    color: #f87171;
}


/* =========================================================
   TERMINAL
   ========================================================= */

.terminal {
    background: #03060a;
    border: 1px solid rgba(71,85,105,.25);
    border-radius: 13px;
    padding: 15px;
    font-family: "JetBrains Mono", Consolas, monospace;
    font-size: 11px;
    color: #94a3b8;
    min-height: 210px;
    max-height: 340px;
    overflow-y: auto;
}

.terminal-line {
    margin: 4px 0;
}

.terminal-ok {
    color: #34d399;
}

.terminal-info {
    color: #60a5fa;
}

.terminal-warn {
    color: #fbbf24;
}

.terminal-bad {
    color: #f87171;
}


/* =========================================================
   POSITION
   ========================================================= */

.position-highlight {
    border: 1px solid rgba(59,130,246,.25);
    background:
        linear-gradient(
            135deg,
            rgba(30,64,175,.12),
            rgba(15,23,42,.72)
        );
    border-radius: 18px;
    padding: 20px;
}

.contract-name {
    font-size: 21px;
    font-weight: 800;
    color: #f8fafc;
}

.contract-subtitle {
    color: #64748b;
    font-size: 11px;
    margin-top: 3px;
}

.position-stat {
    margin-top: 14px;
}

.position-stat-label {
    color: #64748b;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .6px;
}

.position-stat-value {
    color: #e2e8f0;
    font-size: 17px;
    font-weight: 750;
    margin-top: 3px;
}


/* =========================================================
   DECISION
   ========================================================= */

.decision-buy {
    border: 1px solid rgba(52,211,153,.25);
    background: rgba(16,185,129,.06);
    border-radius: 14px;
    padding: 16px;
}

.decision-no-trade {
    border: 1px solid rgba(251,191,36,.20);
    background: rgba(245,158,11,.05);
    border-radius: 14px;
    padding: 16px;
}

.decision-title {
    font-size: 22px;
    font-weight: 850;
}

.decision-buy .decision-title {
    color: #34d399;
}

.decision-no-trade .decision-title {
    color: #fbbf24;
}


/* =========================================================
   TABLE
   ========================================================= */

[data-testid="stTable"] {
    border-radius: 13px;
    overflow: hidden;
}

thead tr th {
    background: #0f172a !important;
    color: #94a3b8 !important;
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: .5px;
}

tbody tr td {
    background: #0a0f18 !important;
    color: #cbd5e1 !important;
    border-color: rgba(148,163,184,.08) !important;
}


/* =========================================================
   BUTTONS
   ========================================================= */

.stButton > button {
    border-radius: 10px;
    font-weight: 700;
    border: 1px solid rgba(148,163,184,.16);
    min-height: 42px;
}

.stButton > button:hover {
    border-color: rgba(96,165,250,.55);
}


/* =========================================================
   SIDEBAR
   ========================================================= */

section[data-testid="stSidebar"] {
    background: #080d15;
    border-right: 1px solid rgba(148,163,184,.09);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}


/* =========================================================
   FOOTER
   ========================================================= */

.footer {
    margin-top: 35px;
    padding-top: 18px;
    border-top: 1px solid rgba(148,163,184,.10);
    color: #475569;
    text-align: center;
    font-size: 10px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "activity_log" not in st.session_state:
    st.session_state.activity_log = []

if "market_data" not in st.session_state:
    st.session_state.market_data = None

if "decision" not in st.session_state:
    st.session_state.decision = None

if "selected_option" not in st.session_state:
    st.session_state.selected_option = None

if "risk_result" not in st.session_state:
    st.session_state.risk_result = None

if "mode" not in st.session_state:
    st.session_state.mode = "Copilot"

if "refresh_seconds" not in st.session_state:
    st.session_state.refresh_seconds = 30

if "connection_logged" not in st.session_state:
    st.session_state.connection_logged = False

if "account_logged" not in st.session_state:
    st.session_state.account_logged = False

if "position_logged" not in st.session_state:
    st.session_state.position_logged = False


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return int(value)

    except Exception:
        return default


def enum_text(value):
    if value is None:
        return ""

    return getattr(
        value,
        "value",
        str(value),
    )


def money(value):
    return f"${safe_float(value):,.2f}"


def pct(value):
    return f"{safe_float(value):,.2f}%"


def format_timestamp(value):
    if not value:
        return "-"

    try:
        ts = pd.to_datetime(
            value,
            utc=True,
        )

        return ts.strftime(
            "%b %d • %H:%M UTC"
        )

    except Exception:
        return str(value)


def log_activity(message, level="info"):

    now = datetime.now().strftime(
        "%H:%M:%S"
    )

    entry = {
        "time": now,
        "message": message,
        "level": level,
    }

    st.session_state.activity_log.append(
        entry
    )

    st.session_state.activity_log = (
        st.session_state.activity_log[-18:]
    )


def get_credentials():

    api_key = os.getenv(
        "ALPACA_API_KEY"
    )

    secret_key = os.getenv(
        "ALPACA_SECRET_KEY"
    )

    if not api_key or not secret_key:

        st.error(
            "ALPACA_API_KEY / ALPACA_SECRET_KEY "
            "not found in .env"
        )

        st.stop()

    return (
        api_key,
        secret_key,
    )


# ============================================================
# ALPACA CLIENTS
# ============================================================

API_KEY, SECRET_KEY = get_credentials()

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


# ============================================================
# ACCOUNT
# ============================================================

try:

    account = trading_client.get_account()

except Exception as e:

    st.error(
        f"Unable to connect to Alpaca PAPER account: {e}"
    )

    st.stop()


if not st.session_state.connection_logged:

    log_activity(
        "Connected to Alpaca PAPER trading environment",
        "ok",
    )

    st.session_state.connection_logged = True


if not st.session_state.account_logged:

    log_activity(
        f"Account synchronized • Equity {money(account.equity)}",
        "ok",
    )

    st.session_state.account_logged = True


# ============================================================
# POSITIONS
# ============================================================

try:

    positions = trading_client.get_all_positions()

except Exception as e:

    positions = []

    log_activity(
        f"Position retrieval failed • {e}",
        "warn",
    )


# ============================================================
# ORDERS
# ============================================================

try:

    order_request = GetOrdersRequest(
        status=QueryOrderStatus.ALL,
    )

    orders = trading_client.get_orders(
        filter=order_request
    )

except Exception as e:

    orders = []

    log_activity(
        f"Order retrieval failed • {e}",
        "warn",
    )


# ============================================================
# CLOCK
# ============================================================

try:

    clock = trading_client.get_clock()

    market_open = bool(
        clock.is_open
    )

    next_open = getattr(
        clock,
        "next_open",
        None,
    )

    next_close = getattr(
        clock,
        "next_close",
        None,
    )

except Exception as e:

    market_open = False
    next_open = None
    next_close = None

    log_activity(
        f"Market clock unavailable • {e}",
        "warn",
    )


# ============================================================
# SPY LATEST IEX TRADE
# ============================================================

spy_price = 0.0
spy_trade_timestamp = None
spy_trade_source = "Alpaca IEX"

try:

    latest_trade_request = StockLatestTradeRequest(
        symbol_or_symbols=SYMBOL,
        feed=DataFeed.IEX,
    )

    latest_trade = (
        stock_client.get_stock_latest_trade(
            latest_trade_request
        )
    )

    if latest_trade and SYMBOL in latest_trade:

        trade = latest_trade[SYMBOL]

        spy_price = safe_float(
            getattr(
                trade,
                "price",
                0,
            )
        )

        spy_trade_timestamp = getattr(
            trade,
            "timestamp",
            None,
        )

except Exception as e:

    log_activity(
        f"SPY latest IEX trade unavailable • {e}",
        "warn",
    )

    spy_price = 0.0


# ============================================================
# TRADE STATE
# ============================================================

def load_trade_state():

    if not STATE_FILE.exists():
        return None

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    except Exception as e:

        log_activity(
            f"Trade state unavailable • {e}",
            "warn",
        )

        return None


trade_state = load_trade_state()


# ============================================================
# LOG POSITION EVENT ONCE
# ============================================================

if positions and not st.session_state.position_logged:

    for position in positions:

        symbol = str(
            position.symbol
        )

        qty = safe_float(
            position.qty
        )

        avg_entry = safe_float(
            position.avg_entry_price
        )

        log_activity(
            f"Open position detected • {symbol} • Qty {qty:g}",
            "info",
        )

        log_activity(
            f"Position entry synchronized • {money(avg_entry)}",
            "info",
        )

    st.session_state.position_logged = True


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    series,
    period=14,
):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        period,
        min_periods=period,
    ).mean()

    avg_loss = loss.rolling(
        period,
        min_periods=period,
    ).mean()

    avg_loss = avg_loss.replace(
        0,
        pd.NA,
    )

    rs = (
        avg_gain / avg_loss
    )

    rsi = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    return rsi


# ============================================================
# NORMALIZE SPY BARS
# ============================================================

def normalize_stock_bars(raw_bars):

    if raw_bars is None:

        raise ValueError(
            "Alpaca returned no SPY bar response."
        )

    bars = raw_bars.copy()

    if bars.empty:

        raise ValueError(
            "Alpaca returned an empty SPY bar dataset."
        )

    # --------------------------------------------------------
    # MultiIndex handling.
    # --------------------------------------------------------

    if isinstance(
        bars.index,
        pd.MultiIndex,
    ):

        index_names = list(
            bars.index.names
        )

        symbol_level = None

        for idx, name in enumerate(
            index_names
        ):

            if str(name).lower() in {
                "symbol",
                "symbols",
            }:

                symbol_level = idx
                break

        if symbol_level is not None:

            try:

                bars = bars.xs(
                    SYMBOL,
                    level=symbol_level,
                )

            except Exception:

                level_values = (
                    bars.index
                    .get_level_values(
                        symbol_level
                    )
                )

                mask = (
                    level_values
                    == SYMBOL
                )

                bars = bars[
                    mask
                ]

                bars.index = (
                    bars.index
                    .droplevel(
                        symbol_level
                    )
                )

        else:

            found = False

            for level_number in range(
                bars.index.nlevels
            ):

                values = (
                    bars.index
                    .get_level_values(
                        level_number
                    )
                )

                if SYMBOL in values:

                    bars = bars.xs(
                        SYMBOL,
                        level=level_number,
                    )

                    found = True
                    break

            if not found:

                raise ValueError(
                    "SPY symbol was not found in the "
                    "historical bar response."
                )

    # --------------------------------------------------------
    # Required OHLCV.
    # --------------------------------------------------------

    required_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing = [
        column
        for column in required_columns
        if column not in bars.columns
    ]

    if missing:

        raise ValueError(
            "SPY market data is missing required "
            f"columns: {', '.join(missing)}"
        )

    # --------------------------------------------------------
    # Numeric conversion.
    # --------------------------------------------------------

    for column in required_columns:

        bars[column] = pd.to_numeric(
            bars[column],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Remove invalid rows.
    # --------------------------------------------------------

    bars = bars.dropna(
        subset=required_columns
    )

    # --------------------------------------------------------
    # Ensure datetime index where possible.
    # --------------------------------------------------------

    try:

        if not isinstance(
            bars.index,
            pd.DatetimeIndex,
        ):

            bars.index = pd.to_datetime(
                bars.index,
                utc=True,
                errors="coerce",
            )

            bars = bars[
                ~bars.index.isna()
            ]

        elif bars.index.tz is None:

            bars.index = bars.index.tz_localize(
                "UTC"
            )

        else:

            bars.index = bars.index.tz_convert(
                "UTC"
            )

    except Exception:

        pass

    # --------------------------------------------------------
    # Sort chronologically.
    # --------------------------------------------------------

    try:

        bars = bars.sort_index()

    except Exception:

        pass

    if bars.empty:

        raise ValueError(
            "SPY historical data contained no valid "
            "OHLCV rows after cleaning."
        )

    return bars


# ============================================================
# FETCH SPY HISTORICAL BARS
# ============================================================

def fetch_spy_daily_bars():

    """
    Fetch real SPY daily bars from Alpaca IEX.

    The function intentionally does not manufacture,
    interpolate, or substitute missing market data.

    Several explicit windows are attempted because the
    available historical range can depend on the data
    subscription and Alpaca response.
    """

    now_utc = datetime.now(
        timezone.utc
    )

    windows = [
        (
            now_utc - timedelta(days=365),
            now_utc,
        ),
        (
            now_utc - timedelta(days=180),
            now_utc,
        ),
        (
            now_utc - timedelta(days=120),
            now_utc,
        ),
        (
            now_utc - timedelta(days=90),
            now_utc,
        ),
    ]

    errors = []

    for start_utc, end_utc in windows:

        try:

            request = StockBarsRequest(
                symbol_or_symbols=[
                    SYMBOL
                ],
                timeframe=TimeFrame.Day,
                start=start_utc,
                end=end_utc,
                limit=1000,
                feed=DataFeed.IEX,
            )

            response = (
                stock_client.get_stock_bars(
                    request
                )
            )

            if response is None:

                errors.append(
                    f"{start_utc.date()} → "
                    f"{end_utc.date()}: "
                    "empty response"
                )

                continue

            raw_df = getattr(
                response,
                "df",
                None,
            )

            if raw_df is None:

                errors.append(
                    f"{start_utc.date()} → "
                    f"{end_utc.date()}: "
                    "no dataframe"
                )

                continue

            if raw_df.empty:

                errors.append(
                    f"{start_utc.date()} → "
                    f"{end_utc.date()}: "
                    "empty dataframe"
                )

                continue

            bars = normalize_stock_bars(
                raw_df
            )

            if bars.empty:

                errors.append(
                    f"{start_utc.date()} → "
                    f"{end_utc.date()}: "
                    "no valid rows"
                )

                continue

            return bars

        except Exception as e:

            errors.append(
                f"{start_utc.date()} → "
                f"{end_utc.date()}: {e}"
            )

    diagnostic = " | ".join(
        errors[-4:]
    )

    raise ValueError(
        "No usable SPY historical data was returned "
        "by Alpaca IEX. "
        f"Diagnostics: {diagnostic}"
    )


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def analyze_market():

    bars = fetch_spy_daily_bars()

    # --------------------------------------------------------
    # Minimum data requirement.
    # --------------------------------------------------------

    if len(bars) < 60:

        raise ValueError(
            f"Only {len(bars)} valid SPY daily bars "
            "were returned by Alpaca IEX. "
            "At least 60 bars are required for the "
            "configured technical analysis."
        )

    close = bars["close"]

    volume = bars["volume"]

    # --------------------------------------------------------
    # SMA20
    # --------------------------------------------------------

    sma20 = close.rolling(
        20,
        min_periods=20,
    ).mean()

    # --------------------------------------------------------
    # SMA50
    # --------------------------------------------------------

    sma50 = close.rolling(
        50,
        min_periods=50,
    ).mean()

    # --------------------------------------------------------
    # RSI14
    # --------------------------------------------------------

    rsi = calculate_rsi(
        close,
        period=14,
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema12 = close.ewm(
        span=12,
        adjust=False,
        min_periods=12,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
        min_periods=26,
    ).mean()

    macd = (
        ema12
        - ema26
    )

    signal = macd.ewm(
        span=9,
        adjust=False,
        min_periods=9,
    ).mean()

    # --------------------------------------------------------
    # Volume confirmation.
    # --------------------------------------------------------

    average_volume = (
        volume
        .rolling(
            20,
            min_periods=20,
        )
        .mean()
    )

    # --------------------------------------------------------
    # Latest values from same dataset.
    # --------------------------------------------------------

    latest_close = safe_float(
        close.iloc[-1]
    )

    latest_sma20 = safe_float(
        sma20.iloc[-1],
        default=float("nan"),
    )

    latest_sma50 = safe_float(
        sma50.iloc[-1],
        default=float("nan"),
    )

    latest_rsi = safe_float(
        rsi.iloc[-1],
        default=float("nan"),
    )

    latest_macd = safe_float(
        macd.iloc[-1],
        default=float("nan"),
    )

    latest_signal = safe_float(
        signal.iloc[-1],
        default=float("nan"),
    )

    latest_volume = safe_float(
        volume.iloc[-1]
    )

    latest_average_volume = safe_float(
        average_volume.iloc[-1],
        default=float("nan"),
    )

    # --------------------------------------------------------
    # Validate indicators.
    # --------------------------------------------------------

    indicator_values = {
        "SMA20": latest_sma20,
        "SMA50": latest_sma50,
        "RSI": latest_rsi,
        "MACD": latest_macd,
        "MACD Signal": latest_signal,
        "Average Volume": latest_average_volume,
    }

    invalid = [
        name
        for name, value in indicator_values.items()
        if pd.isna(value)
    ]

    if invalid:

        raise ValueError(
            "Technical indicators could not be calculated "
            "from the returned SPY data: "
            + ", ".join(invalid)
        )

    # --------------------------------------------------------
    # Conditions.
    # --------------------------------------------------------

    conditions = {

        "Price > SMA20":
            latest_close > latest_sma20,

        "SMA20 > SMA50":
            latest_sma20 > latest_sma50,

        "RSI > 50":
            latest_rsi > 50,

        "MACD > Signal":
            latest_macd > latest_signal,

        "Volume Confirmation":
            latest_volume >= latest_average_volume,
    }

    # --------------------------------------------------------
    # Confidence.
    # --------------------------------------------------------

    passed = sum(
        1
        for value in conditions.values()
        if value
    )

    total_conditions = len(
        conditions
    )

    confidence = (
        passed
        / total_conditions
    ) * 100

    decision = (
        "BUY"
        if confidence >= MIN_CONFIDENCE
        else
        "NO TRADE"
    )

    # --------------------------------------------------------
    # Data timestamps.
    # --------------------------------------------------------

    try:

        first_bar = pd.Timestamp(
            bars.index[0]
        ).isoformat()

        last_bar = pd.Timestamp(
            bars.index[-1]
        ).isoformat()

    except Exception:

        first_bar = "-"
        last_bar = "-"

    return {

        "price":
            latest_close,

        "sma20":
            latest_sma20,

        "sma50":
            latest_sma50,

        "rsi":
            latest_rsi,

        "macd":
            latest_macd,

        "signal":
            latest_signal,

        "volume":
            latest_volume,

        "avg_volume":
            latest_average_volume,

        "conditions":
            conditions,

        "passed":
            passed,

        "total_conditions":
            total_conditions,

        "confidence":
            confidence,

        "decision":
            decision,

        "bars_used":
            len(bars),

        "data_start":
            first_bar,

        "data_end":
            last_bar,

        "scan_time":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# ============================================================
# OPTION SCANNER
# ============================================================

def scan_options():

    # --------------------------------------------------------
    # Prefer latest IEX trade for option selection.
    # Historical price is only a fallback if latest trade
    # is unavailable.
    # --------------------------------------------------------

    underlying_price = spy_price

    if underlying_price <= 0:

        if st.session_state.market_data:

            underlying_price = safe_float(
                st.session_state.market_data.get(
                    "price",
                    0,
                )
            )

    if underlying_price <= 0:

        raise ValueError(
            "SPY price unavailable for option scanning."
        )

    today = date.today()

    start_date = (
        today
        + timedelta(
            days=MIN_DTE
        )
    )

    end_date = (
        today
        + timedelta(
            days=MAX_DTE
        )
    )

    request = GetOptionContractsRequest(
        underlying_symbols=[
            SYMBOL
        ],
        status="active",
        expiration_date_gte=start_date,
        expiration_date_lte=end_date,
        type=ContractType.CALL,
        limit=1000,
    )

    try:

        result = (
            trading_client.get_option_contracts(
                request
            )
        )

    except Exception as e:

        raise ValueError(
            f"Alpaca option contract scan failed: {e}"
        )

    contracts = (
        getattr(
            result,
            "option_contracts",
            None,
        )
        or []
    )

    candidates = []

    for contract in contracts:

        strike = safe_float(
            getattr(
                contract,
                "strike_price",
                0,
            )
        )

        if strike <= 0:
            continue

        distance = abs(
            strike
            - underlying_price
        )

        if distance > MAX_STRIKE_DISTANCE:
            continue

        oi = safe_int(
            getattr(
                contract,
                "open_interest",
                0,
            )
        )

        if oi < MIN_OPEN_INTEREST:
            continue

        expiration = getattr(
            contract,
            "expiration_date",
            None,
        )

        if expiration is None:
            continue

        try:

            exp_date = (
                pd.to_datetime(
                    expiration
                ).date()
            )

        except Exception:

            continue

        dte = (
            exp_date
            - today
        ).days

        if (
            dte < MIN_DTE
            or dte > MAX_DTE
        ):
            continue

        # ----------------------------------------------------
        # Selection score.
        # ----------------------------------------------------

        distance_score = max(
            0,
            40
            - (
                distance
                / MAX_STRIKE_DISTANCE
            ) * 40,
        )

        oi_score = min(
            30,
            oi
            / 1000
            * 30,
        )

        dte_score = max(
            0,
            30
            - abs(
                dte
                - 14
            ),
        )

        score = (
            distance_score
            + oi_score
            + dte_score
        )

        candidates.append(
            {
                "symbol":
                    str(
                        contract.symbol
                    ),

                "strike":
                    strike,

                "expiration":
                    str(
                        expiration
                    ),

                "dte":
                    dte,

                "open_interest":
                    oi,

                "distance":
                    distance,

                "score":
                    score,
            }
        )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates


# ============================================================
# OPTION QUOTE
# ============================================================

def get_option_quote(symbol):

    request = OptionLatestQuoteRequest(
        symbol_or_symbols=symbol,
    )

    try:

        quotes = (
            option_client.get_option_latest_quote(
                request
            )
        )

    except Exception as e:

        raise ValueError(
            f"Unable to retrieve option quote for "
            f"{symbol}: {e}"
        )

    if not quotes or symbol not in quotes:

        raise ValueError(
            f"No option quote returned for {symbol}."
        )

    quote = quotes[symbol]

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

    if (
        bid > 0
        and ask > 0
    ):

        midpoint = (
            bid
            + ask
        ) / 2

    elif ask > 0:

        midpoint = ask

    else:

        midpoint = bid

    if midpoint <= 0:

        raise ValueError(
            f"Option {symbol} has no usable bid/ask quote."
        )

    return {
        "bid": bid,
        "ask": ask,
        "mid": midpoint,
    }


# ============================================================
# RISK CHECK
# ============================================================

def risk_check(option_price):

    account_equity = safe_float(
        account.equity
    )

    contract_cost = (
        option_price
        * 100
    )

    max_risk = (
        account_equity
        * MAX_ACCOUNT_RISK
    )

    max_exposure = (
        account_equity
        * MAX_EXPOSURE
    )

    passed = (
        contract_cost <= max_risk
        and
        contract_cost <= max_exposure
    )

    return {

        "passed":
            passed,

        "contract_cost":
            contract_cost,

        "max_risk":
            max_risk,

        "max_exposure":
            max_exposure,
    }


# ============================================================
# DUPLICATE POSITION CHECK
# ============================================================

def has_open_position(symbol):

    target = str(
        symbol
    ).upper()

    for position in positions:

        existing_symbol = str(
            getattr(
                position,
                "symbol",
                "",
            )
        ).upper()

        qty = safe_float(
            getattr(
                position,
                "qty",
                0,
            )
        )

        if (
            existing_symbol == target
            and qty != 0
        ):

            return True

    return False


# ============================================================
# SUBMIT PAPER ORDER
# ============================================================

def submit_paper_order(symbol):

    if has_open_position(symbol):

        raise ValueError(
            f"Duplicate position blocked: "
            f"{symbol} is already open."
        )

    request = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )

    try:

        order = (
            trading_client.submit_order(
                order_data=request
            )
        )

    except Exception as e:

        raise ValueError(
            f"Alpaca paper BUY submission failed: {e}"
        )

    return order


# ============================================================
# TRADE HISTORY
# ============================================================

def load_trade_history():

    if not LOG_FILE.exists():

        return pd.DataFrame()

    try:

        return pd.read_csv(
            LOG_FILE
        )

    except Exception as e:

        log_activity(
            f"Trade history unavailable • {e}",
            "warn",
        )

        return pd.DataFrame()


history_df = load_trade_history()


# ============================================================
# PERFORMANCE
# ============================================================

def performance_stats(df):

    if df.empty:

        return {

            "trades":
                0,

            "pnl":
                0.0,

            "wins":
                0,

            "win_rate":
                0.0,

            "profit_factor":
                0.0,
        }

    if "P&L" not in df.columns:

        return {

            "trades":
                len(df),

            "pnl":
                0.0,

            "wins":
                0,

            "win_rate":
                0.0,

            "profit_factor":
                0.0,
        }

    pnl = pd.to_numeric(
        df["P&L"],
        errors="coerce",
    ).fillna(0)

    wins = int(
        (
            pnl > 0
        ).sum()
    )

    losses = pnl[
        pnl < 0
    ]

    gross_profit = pnl[
        pnl > 0
    ].sum()

    gross_loss = abs(
        losses.sum()
    )

    if gross_loss > 0:

        profit_factor = (
            gross_profit
            / gross_loss
        )

    else:

        profit_factor = 0.0

    return {

        "trades":
            len(df),

        "pnl":
            pnl.sum(),

        "wins":
            wins,

        "win_rate":
            (
                wins
                / len(df)
            ) * 100,

        "profit_factor":
            profit_factor,
    }


stats = performance_stats(
    history_df
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
<div class="hero">

    <div class="hero-title">
        🚀 AlphaPilot AI
    </div>

    <div class="hero-subtitle">
        AI Options Officer • Autonomous Paper Trading System
    </div>

    <div class="status-row">

        <span class="badge badge-green">
            ● CONNECTED
        </span>

        <span class="badge badge-blue">
            ALPACA PAPER
        </span>

        <span class="badge badge-orange">
            OPTIONS
        </span>

    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## ⚙️ AlphaPilot Controls"
    )

    st.caption(
        "Real Alpaca paper-trading environment"
    )

    st.session_state.mode = st.selectbox(
        "Agent Mode",
        [
            "Copilot",
            "Autopilot",
        ],
        index=(
            0
            if st.session_state.mode
            == "Copilot"
            else 1
        ),
    )

    st.session_state.refresh_seconds = (
        st.slider(
            "Refresh Interval",
            min_value=10,
            max_value=120,
            value=st.session_state.refresh_seconds,
            step=10,
        )
    )

    st.divider()

    st.markdown(
        "### 🛡️ Risk Guards"
    )

    st.metric(
        "Max Account Risk",
        "1.00%",
    )

    st.metric(
        "Max Exposure",
        "5.00%",
    )

    st.metric(
        "Stop Loss",
        "25%",
    )

    st.metric(
        "Take Profit",
        "50%",
    )

    st.divider()

    st.markdown(
        "### 📡 Strategy"
    )

    st.caption(
        "Underlying: SPY"
    )

    st.caption(
        "CALL options only"
    )

    st.caption(
        f"Confidence threshold: {MIN_CONFIDENCE:.0f}%"
    )

    st.caption(
        f"DTE: {MIN_DTE}–{MAX_DTE} days"
    )

    st.caption(
        "Data feed: IEX"
    )


# ============================================================
# ACCOUNT OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-title">💰 Account Overview</div>',
    unsafe_allow_html=True,
)

account_cols = st.columns(5)

day_pnl = (
    safe_float(
        getattr(
            account,
            "equity",
            0,
        )
    )
    - safe_float(
        getattr(
            account,
            "last_equity",
            getattr(
                account,
                "equity",
                0,
            ),
        )
    )
)

account_metrics = [

    (
        "Equity",
        money(
            account.equity
        ),
        "",
    ),

    (
        "Buying Power",
        money(
            account.buying_power
        ),
        "",
    ),

    (
        "Cash",
        money(
            account.cash
        ),
        "",
    ),

    (
        "Day P&L",
        money(
            day_pnl
        ),
        (
            "negative"
            if day_pnl < 0
            else
            "positive"
            if day_pnl > 0
            else ""
        ),
    ),

    (
        "Open Positions",
        str(
            len(positions)
        ),
        "",
    ),
]

for col, item in zip(
    account_cols,
    account_metrics,
):

    label, value, css_class = item

    col.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-label">
                {label}
            </div>

            <div class="metric-value {css_class}">
                {value}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MARKET STATUS
# ============================================================

st.markdown(
    '<div class="section-title">🌐 Market Status</div>',
    unsafe_allow_html=True,
)

market_cols = st.columns(3)

market_cols[0].markdown(
    f"""
    <div class="panel">

        <div class="panel-title">
            {
                "🟢 US MARKET OPEN"
                if market_open
                else
                "🟡 US MARKET CLOSED"
            }
        </div>

        <div class="small-muted">
            Alpaca market clock
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)

market_price_text = (
    money(spy_price)
    if spy_price > 0
    else
    "UNAVAILABLE"
)

market_cols[1].markdown(
    f"""
    <div class="panel">

        <div class="panel-title">
            SPY Last IEX Trade
        </div>

        <div class="market-price">
            {market_price_text}
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)

market_cols[2].markdown(
    f"""
    <div class="panel">

        <div class="panel-title">
            Agent Mode
        </div>

        <div class="market-price"
             style="font-size:22px;">
            {st.session_state.mode}
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# WORKFLOW STATE
# ============================================================

market_state = (
    "✓ SCAN COMPLETE"
    if st.session_state.market_data
    else
    "Waiting for scan"
)

decision_state = (
    "Awaiting decision"
)

if st.session_state.decision:

    decision_state = (
        f"✓ "
        f"{st.session_state.decision['decision']} "
        f"• "
        f"{st.session_state.decision['confidence']:.0f}%"
    )


if trade_state:

    state_status = trade_state.get(
        "status",
        "UNKNOWN",
    )

    if state_status == "EXIT_PENDING":

        monitor_state = (
            "⚠ EXIT PENDING"
        )

    elif state_status == "OPEN":

        monitor_state = (
            "✓ MONITORING"
        )

    else:

        monitor_state = state_status

else:

    monitor_state = (
        "✓ POSITION ACTIVE"
        if positions
        else
        "No active position"
    )


st.markdown(
    '<div class="section-title">🧭 AlphaPilot Workflow</div>',
    unsafe_allow_html=True,
)

workflow_html = f"""
<div class="workflow">

<div class="workflow-card">

    <div class="workflow-number">
        STEP 01
    </div>

    <div class="workflow-name">
        🛡️ Configure Risk Guards
    </div>

    <div class="workflow-status">
        <span class="status-good">
            ✓ ACTIVE
        </span>
    </div>

</div>


<div class="workflow-card">

    <div class="workflow-number">
        STEP 02
    </div>

    <div class="workflow-name">
        🧠 AI Market Scan
    </div>

    <div class="workflow-status">
        <span class="status-info">
            {market_state}
        </span>
    </div>

</div>


<div class="workflow-card">

    <div class="workflow-number">
        STEP 03
    </div>

    <div class="workflow-name">
        🎯 Decision & Entry
    </div>

    <div class="workflow-status">
        <span class="status-info">
            {decision_state}
        </span>
    </div>

</div>


<div class="workflow-card">

    <div class="workflow-number">
        STEP 04
    </div>

    <div class="workflow-name">
        📈 Monitor Performance
    </div>

    <div class="workflow-status">
        <span class="status-good">
            {monitor_state}
        </span>
    </div>

</div>

</div>
"""

st.markdown(
    workflow_html,
    unsafe_allow_html=True,
)


# ============================================================
# AGENT CONTROLS
# ============================================================

st.markdown(
    '<div class="section-title">⚡ Agent Controls</div>',
    unsafe_allow_html=True,
)

control_cols = st.columns(4)


# ============================================================
# SCAN MARKET
# ============================================================

with control_cols[0]:

    if st.button(
        "🧠 Scan Market",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Fetching real SPY historical data from Alpaca IEX..."
            ):

                data = analyze_market()

            st.session_state.market_data = (
                data
            )

            st.session_state.decision = (
                data
            )

            log_activity(
                f"Market scan complete • "
                f"{data['bars_used']} daily bars • "
                f"Confidence {data['confidence']:.0f}%",
                "ok",
            )

            log_activity(
                f"SPY {money(data['price'])} • "
                f"SMA20 {money(data['sma20'])} • "
                f"SMA50 {money(data['sma50'])}",
                "info",
            )

            log_activity(
                f"Decision engine returned "
                f"{data['decision']}",
                "info",
            )

            st.rerun()

        except Exception as e:

            log_activity(
                f"Market scan failed • {e}",
                "bad",
            )

            st.error(
                f"Market scan failed: {e}"
            )


# ============================================================
# SCAN OPTIONS
# ============================================================

with control_cols[1]:

    if st.button(
        "🔎 Scan Options",
        use_container_width=True,
    ):

        try:

            if not st.session_state.market_data:

                st.warning(
                    "Run Scan Market first."
                )

            else:

                candidates = (
                    scan_options()
                )

                if candidates:

                    st.session_state.selected_option = (
                        candidates[0]
                    )

                    log_activity(
                        f"Option scan complete • "
                        f"{len(candidates)} candidates",
                        "ok",
                    )

                    log_activity(
                        f"Top contract "
                        f"{candidates[0]['symbol']} • "
                        f"Score "
                        f"{candidates[0]['score']:.2f}",
                        "info",
                    )

                    st.rerun()

                else:

                    st.warning(
                        "No qualifying option contracts found."
                    )

        except Exception as e:

            log_activity(
                f"Option scan failed • {e}",
                "bad",
            )

            st.error(
                f"Option scan failed: {e}"
            )


# ============================================================
# RISK CHECK
# ============================================================

with control_cols[2]:

    if st.button(
        "🛡️ Risk Check",
        use_container_width=True,
    ):

        option = (
            st.session_state.selected_option
        )

        if not option:

            st.warning(
                "Scan options first."
            )

        else:

            try:

                quote = get_option_quote(
                    option["symbol"]
                )

                result = risk_check(
                    quote["mid"]
                )

                result["quote"] = quote

                st.session_state.risk_result = (
                    result
                )

                if result["passed"]:

                    log_activity(
                        f"Risk check PASSED • "
                        f"Cost "
                        f"{money(result['contract_cost'])}",
                        "ok",
                    )

                else:

                    log_activity(
                        "Risk check BLOCKED order",
                        "warn",
                    )

                st.rerun()

            except Exception as e:

                log_activity(
                    f"Risk check failed • {e}",
                    "bad",
                )

                st.error(
                    f"Risk check failed: {e}"
                )


# ============================================================
# REFRESH
# ============================================================

with control_cols[3]:

    if st.button(
        "🔄 Refresh Positions",
        use_container_width=True,
    ):

        st.rerun()


# ============================================================
# TERMINAL + DECISION
# ============================================================

st.markdown(
    '<div class="section-title">🤖 Copilot Decision Center</div>',
    unsafe_allow_html=True,
)

left, right = st.columns(
    [1.05, 1],
    gap="large",
)


# ============================================================
# TERMINAL
# ============================================================

with left:

    st.markdown(
        """
        <div class="panel-title">
            🖥️ Agent Activity Terminal
        </div>

        <div class="small-muted">
            Real AlphaPilot execution and decision events.
            No fabricated AI thoughts or performance data.
        </div>
        """,
        unsafe_allow_html=True,
    )

    terminal_lines = []

    for entry in (
        st.session_state.activity_log
    ):

        level = entry["level"]

        if level == "ok":

            cls = "terminal-ok"
            icon = "✓"

        elif level == "warn":

            cls = "terminal-warn"
            icon = "!"

        elif level == "bad":

            cls = "terminal-bad"
            icon = "✕"

        else:

            cls = "terminal-info"
            icon = "→"

        terminal_lines.append(
            f"""
            <div class="terminal-line">

                <span style="color:#475569;">
                    [{entry['time']}]
                </span>

                <span class="{cls}">
                    {icon} {entry['message']}
                </span>

            </div>
            """
        )

    if not terminal_lines:

        terminal_lines.append(
            """
            <div class="terminal-line">

                <span class="terminal-info">
                    → No AI decision available.
                    Click Scan Market to begin.
                </span>

            </div>
            """
        )

    st.markdown(
        f"""
        <div class="terminal">
            {''.join(terminal_lines)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🧹 Clear Session Log",
        use_container_width=True,
    ):

        st.session_state.activity_log = []

        st.rerun()


# ============================================================
# DECISION PANEL
# ============================================================

with right:

    data = (
        st.session_state.market_data
    )

    if not data:

        st.markdown(
            """
            <div class="panel">

                <div class="panel-title">
                    🎯 Decision Engine
                </div>

                <div class="small-muted"
                     style="margin-top:12px;">

                    Run a market scan to generate a
                    real technical-analysis decision.

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        decision = data[
            "decision"
        ]

        if decision == "BUY":

            st.markdown(
                f"""
                <div class="decision-buy">

                    <div class="decision-title">
                        🟢 BUY SIGNAL
                    </div>

                    <div class="small-muted">
                        Technical conditions passed the
                        configured confidence threshold.
                    </div>

                    <div style="
                        margin-top:14px;
                        font-size:25px;
                        font-weight:800;
                        color:#f8fafc;
                    ">
                        {data['confidence']:.1f}%
                    </div>

                    <div class="small-muted">
                        Confidence • Required
                        {MIN_CONFIDENCE:.0f}%
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"""
                <div class="decision-no-trade">

                    <div class="decision-title">
                        🟡 NO TRADE
                    </div>

                    <div class="small-muted">
                        Current technical conditions did not
                        meet the configured confidence threshold.
                    </div>

                    <div style="
                        margin-top:14px;
                        font-size:25px;
                        font-weight:800;
                        color:#f8fafc;
                    ">
                        {data['confidence']:.1f}%
                    </div>

                    <div class="small-muted">
                        Confidence • Required
                        {MIN_CONFIDENCE:.0f}%
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "#### Technical Conditions"
        )

        condition_df = pd.DataFrame(
            [
                {
                    "Condition":
                        key,

                    "Status":
                        (
                            "PASS"
                            if value
                            else
                            "FAIL"
                        ),
                }
                for key, value
                in data[
                    "conditions"
                ].items()
            ]
        )

        st.table(
            condition_df
        )

        # ----------------------------------------------------
        # Actual data freshness.
        # ----------------------------------------------------

        try:

            data_end_display = (
                pd.to_datetime(
                    data["data_end"],
                    utc=True,
                ).strftime(
                    "%Y-%m-%d %H:%M UTC"
                )
            )

        except Exception:

            data_end_display = str(
                data["data_end"]
            )

        st.markdown(
            f"""
            <div class="small-muted"
                 style="margin-top:10px;">

                Data source: Alpaca IEX •
                {data['bars_used']} daily bars

                <br>

                Historical range:
                {data['data_start']}
                →
                {data['data_end']}

                <br>

                Technical data as-of:
                {data_end_display}

                <br>

                Scan time:
                {data['scan_time']}

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# OPTION SELECTION
# ============================================================

option = (
    st.session_state.selected_option
)

if option:

    st.markdown(
        '<div class="section-title">🎯 Selected Option</div>',
        unsafe_allow_html=True,
    )

    option_cols = st.columns(5)

    option_values = [

        (
            "Contract",
            option["symbol"],
        ),

        (
            "Strike",
            money(
                option["strike"]
            ),
        ),

        (
            "DTE",
            str(
                option["dte"]
            ),
        ),

        (
            "Open Interest",
            f"{option['open_interest']:,}",
        ),

        (
            "Selection Score",
            f"{option['score']:.2f}",
        ),
    ]

    for col, item in zip(
        option_cols,
        option_values,
    ):

        col.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-label">
                    {item[0]}
                </div>

                <div class="metric-value"
                     style="font-size:18px;">
                    {item[1]}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# RISK RESULT
# ============================================================

if st.session_state.risk_result:

    result = (
        st.session_state.risk_result
    )

    st.markdown(
        '<div class="section-title">🛡️ Risk Assessment</div>',
        unsafe_allow_html=True,
    )

    risk_cols = st.columns(4)

    risk_values = [

        (
            "Risk Status",
            (
                "PASS"
                if result["passed"]
                else
                "BLOCKED"
            ),
        ),

        (
            "Option Cost",
            money(
                result[
                    "contract_cost"
                ]
            ),
        ),

        (
            "Max Account Risk",
            money(
                result[
                    "max_risk"
                ]
            ),
        ),

        (
            "Max Exposure",
            money(
                result[
                    "max_exposure"
                ]
            ),
        ),
    ]

    for col, item in zip(
        risk_cols,
        risk_values,
    ):

        col.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-label">
                    {item[0]}
                </div>

                <div class="metric-value"
                     style="font-size:18px;">
                    {item[1]}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# PAPER BUY CONFIRMATION
# ============================================================

if (
    st.session_state.decision
    and
    st.session_state.decision[
        "decision"
    ] == "BUY"
    and
    option
    and
    st.session_state.risk_result
    and
    st.session_state.risk_result[
        "passed"
    ]
):

    st.markdown(
        '<div class="section-title">🧾 Paper Entry</div>',
        unsafe_allow_html=True,
    )

    st.warning(
        "A paper BUY order will be submitted to Alpaca. "
        "This dashboard does not submit live-money orders."
    )

    confirm = st.checkbox(
        "I confirm this paper-trading order.",
        key="confirm_paper_order",
    )

    if confirm:

        if has_open_position(
            option["symbol"]
        ):

            st.warning(
                f"Paper BUY blocked: "
                f"{option['symbol']} is already an open position."
            )

        elif st.button(
            f"🚀 Submit PAPER BUY • {option['symbol']}",
            use_container_width=True,
        ):

            try:

                order = submit_paper_order(
                    option["symbol"]
                )

                order_id = getattr(
                    order,
                    "id",
                    None,
                )

                log_activity(
                    f"PAPER BUY submitted • "
                    f"{option['symbol']}",
                    "ok",
                )

                if order_id:

                    log_activity(
                        f"Order ID {order_id}",
                        "info",
                    )

                st.success(
                    "Paper order submitted successfully."
                )

                st.rerun()

            except Exception as e:

                log_activity(
                    f"Paper BUY failed • {e}",
                    "bad",
                )

                st.error(
                    f"Paper order failed: {e}"
                )


# ============================================================
# ACTIVE POSITIONS
# ============================================================

st.markdown(
    '<div class="section-title">📌 Active Option Contracts</div>',
    unsafe_allow_html=True,
)

if positions:

    for position in positions:

        symbol = str(
            position.symbol
        )

        qty = safe_float(
            position.qty
        )

        avg_entry = safe_float(
            position.avg_entry_price
        )

        market_value = safe_float(
            position.market_value
        )

        unrealized = safe_float(
            position.unrealized_pl
        )

        unrealized_pct = (
            safe_float(
                position.unrealized_plpc
            )
            * 100
        )

        current_price = 0.0

        try:

            quote = get_option_quote(
                symbol
            )

            current_price = quote[
                "mid"
            ]

        except Exception as e:

            log_activity(
                f"Option quote unavailable • "
                f"{symbol} • {e}",
                "warn",
            )

            current_price = 0.0

        if current_price > 0:

            calculated_market_value = (
                current_price
                * qty
                * 100
            )

            calculated_pnl = (
                current_price
                - avg_entry
            ) * qty * 100

            if avg_entry > 0:

                calculated_return = (
                    (
                        current_price
                        / avg_entry
                    )
                    - 1
                ) * 100

            else:

                calculated_return = 0.0

            market_value = (
                calculated_market_value
            )

            unrealized = (
                calculated_pnl
            )

            unrealized_pct = (
                calculated_return
            )

        stop_price = (
            avg_entry
            * (
                1
                - STOP_LOSS_PCT
            )
        )

        target_price = (
            avg_entry
            * (
                1
                + TAKE_PROFIT_PCT
            )
        )

        exit_state = "OPEN"

        if trade_state:

            exit_state = (
                trade_state.get(
                    "status",
                    "OPEN",
                )
            )

        st.markdown(
            f"""
            <div class="position-highlight">

                <div class="contract-name">
                    {symbol}
                </div>

                <div class="contract-subtitle">
                    Active paper position • Alpaca
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        pos_cols = st.columns(8)

        position_values = [

            (
                "Qty",
                f"{qty:g}",
            ),

            (
                "Entry",
                money(avg_entry),
            ),

            (
                "Current",
                money(current_price),
            ),

            (
                "Market Value",
                money(market_value),
            ),

            (
                "Unrealized P&L",
                money(unrealized),
            ),

            (
                "Return",
                pct(unrealized_pct),
            ),

            (
                "Stop",
                money(stop_price),
            ),

            (
                "Target",
                money(target_price),
            ),
        ]

        for col, item in zip(
            pos_cols,
            position_values,
        ):

            col.markdown(
                f"""
                <div class="position-stat">

                    <div class="position-stat-label">
                        {item[0]}
                    </div>

                    <div class="position-stat-value">
                        {item[1]}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        exit_color = (
            "#fbbf24"
            if exit_state == "EXIT_PENDING"
            else
            "#60a5fa"
        )

        st.markdown(
            f"""
            <div style="
                margin-top:15px;
                color:#94a3b8;
                font-size:11px;
            ">

                Exit State:

                <strong style="color:{exit_color};">
                    {exit_state}
                </strong>

            </div>
            """,
            unsafe_allow_html=True,
        )

else:

    st.info(
        "No active option positions detected."
    )


# ============================================================
# PERFORMANCE
# ============================================================

st.markdown(
    '<div class="section-title">📈 Performance & Risk</div>',
    unsafe_allow_html=True,
)

perf_cols = st.columns(5)

pnl_css = (
    "negative"
    if stats["pnl"] < 0
    else
    "positive"
    if stats["pnl"] > 0
    else ""
)

performance_values = [

    (
        "Completed Trades",
        str(
            stats["trades"]
        ),
        "",
    ),

    (
        "Total Realized P&L",
        money(
            stats["pnl"]
        ),
        pnl_css,
    ),

    (
        "Win Rate",
        pct(
            stats["win_rate"]
        ),
        "",
    ),

    (
        "Winning Trades",
        str(
            stats["wins"]
        ),
        "",
    ),

    (
        "Profit Factor",
        f"{stats['profit_factor']:.2f}",
        "",
    ),
]

for col, item in zip(
    perf_cols,
    performance_values,
):

    label, value, css_class = item

    col.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-label">
                {label}
            </div>

            <div class="metric-value {css_class}">
                {value}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# REALIZED P&L CURVE
# ============================================================

if not history_df.empty:

    if "P&L" in history_df.columns:

        pnl_series = pd.to_numeric(
            history_df["P&L"],
            errors="coerce",
        ).fillna(0)

        cumulative_pnl = (
            pnl_series.cumsum()
        )

        chart_df = pd.DataFrame(
            {
                "Trade":
                    range(
                        1,
                        len(
                            cumulative_pnl
                        ) + 1,
                    ),

                "Cumulative P&L":
                    cumulative_pnl,
            }
        )

        st.markdown(
            "#### Realized P&L Curve"
        )

        st.line_chart(
            chart_df.set_index(
                "Trade"
            ),
            height=250,
        )

    else:

        st.info(
            "Trade history does not contain a P&L column."
        )

else:

    st.info(
        "No completed trades yet."
    )


# ============================================================
# RECENT COMPLETED TRADES
# ============================================================

st.markdown(
    "#### Recent Completed Trades"
)

if not history_df.empty:

    recent = (
        history_df
        .tail(10)
        .copy()
    )

    numeric_columns = [
        "Quantity",
        "Entry Price",
        "Exit Price",
        "Entry Value",
        "Exit Value",
        "P&L",
        "P&L %",
    ]

    for column in numeric_columns:

        if column in recent.columns:

            recent[column] = pd.to_numeric(
                recent[column],
                errors="coerce",
            )

    if "Quantity" in recent.columns:

        recent["Quantity"] = (
            recent["Quantity"]
            .map(
                lambda x:
                    f"{x:g}"
                    if pd.notna(x)
                    else "-"
            )
        )

    for column in [
        "Entry Price",
        "Exit Price",
        "Entry Value",
        "Exit Value",
    ]:

        if column in recent.columns:

            recent[column] = (
                recent[column]
                .map(
                    lambda x:
                        f"${x:,.2f}"
                        if pd.notna(x)
                        else "-"
                )
            )

    if "P&L" in recent.columns:

        recent["P&L"] = (
            recent["P&L"]
            .map(
                lambda x:
                    f"${x:,.2f}"
                    if pd.notna(x)
                    else "-"
            )
        )

    if "P&L %" in recent.columns:

        recent["P&L %"] = (
            recent["P&L %"]
            .map(
                lambda x:
                    f"{x:,.2f}%"
                    if pd.notna(x)
                    else "-"
            )
        )

    st.table(
        recent
    )

else:

    st.info(
        "No completed trades recorded."
    )


# ============================================================
# RECENT ALPACA ORDERS
# ============================================================

st.markdown(
    '<div class="section-title">🧾 Recent Alpaca Orders</div>',
    unsafe_allow_html=True,
)

if orders:

    order_rows = []

    for order in orders[:10]:

        order_rows.append(
            {
                "Created":
                    format_timestamp(
                        getattr(
                            order,
                            "created_at",
                            None,
                        )
                    ),

                "Symbol":
                    str(
                        getattr(
                            order,
                            "symbol",
                            "",
                        )
                    ),

                "Side":
                    enum_text(
                        getattr(
                            order,
                            "side",
                            "",
                        )
                    ).upper(),

                "Qty":
                    safe_float(
                        getattr(
                            order,
                            "qty",
                            0,
                        )
                    ),

                "Filled":
                    safe_float(
                        getattr(
                            order,
                            "filled_qty",
                            0,
                        )
                    ),

                "Avg Fill":
                    safe_float(
                        getattr(
                            order,
                            "filled_avg_price",
                            0,
                        )
                    ),

                "Status":
                    enum_text(
                        getattr(
                            order,
                            "status",
                            "",
                        )
                    ).upper(),
            }
        )

    orders_df = pd.DataFrame(
        order_rows
    )

    if not orders_df.empty:

        orders_df["Qty"] = (
            orders_df["Qty"]
            .map(
                lambda x:
                    f"{x:g}"
            )
        )

        orders_df["Filled"] = (
            orders_df["Filled"]
            .map(
                lambda x:
                    f"{x:g}"
            )
        )

        orders_df["Avg Fill"] = (
            orders_df["Avg Fill"]
            .map(
                lambda x:
                    (
                        f"${x:,.2f}"
                        if x > 0
                        else "-"
                    )
            )
        )

        st.table(
            orders_df
        )

else:

    st.info(
        "No Alpaca orders available."
    )


# ============================================================
# AUTOPILOT STATUS
# ============================================================

st.markdown(
    '<div class="section-title">🤖 Autopilot Status</div>',
    unsafe_allow_html=True,
)

if (
    st.session_state.mode
    == "Autopilot"
):

    st.markdown(
        """
        <div class="panel">

            <div class="panel-title">
                🟢 AUTOPILOT MODE
            </div>

            <div class="small-muted"
                 style="margin-top:9px;">

                AlphaPilot is configured for autonomous
                paper-trading workflow.

                Entry and exit lifecycle workers operate
                separately from this dashboard.

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
        <div class="panel">

            <div class="panel-title">
                🔵 COPILOT MODE
            </div>

            <div class="small-muted"
                 style="margin-top:9px;">

                AlphaPilot analyzes market conditions and
                prepares trading decisions.

                Paper order submission requires explicit
                confirmation.

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CURRENT TRADE STATE
# ============================================================

st.markdown(
    "#### Current Trade State"
)

if trade_state:

    state_cols = st.columns(4)

    state_cols[0].metric(
        "Status",
        trade_state.get(
            "status",
            "UNKNOWN",
        ),
    )

    state_cols[1].metric(
        "Symbol",
        trade_state.get(
            "symbol",
            "-",
        ),
    )

    state_cols[2].metric(
        "Quantity",
        str(
            trade_state.get(
                "quantity",
                "-",
            )
        ),
    )

    state_cols[3].metric(
        "Entry",
        money(
            trade_state.get(
                "entry_price",
                0,
            )
        ),
    )

else:

    st.info(
        "No active AlphaPilot trade state."
    )


# ============================================================
# WORKER COMMANDS
# ============================================================

with st.expander(
    "⚙️ Autonomous Worker Commands"
):

    st.code(
        """
# Entry Engine
python -m agents.entry_engine

# Exit Engine
python -m agents.exit_engine

# Dashboard
python -m streamlit run dashboard.py
""",
        language="powershell",
    )

    st.caption(
        "Run autonomous workers separately. "
        "Do not start duplicate workers."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer">

AlphaPilot AI • Alpaca Paper Trading •
Real Market Data • Real Orders •
Real Trade History • No Fake Performance

</div>
""",
    unsafe_allow_html=True,
)