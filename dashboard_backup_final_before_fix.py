
import os
import math
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

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
    StockBarsRequest,
    StockLatestTradeRequest,
    OptionLatestQuoteRequest,
)
from alpaca.data.enums import DataFeed
from alpaca.data.timeframe import TimeFrame


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

PAPER = True

SYMBOL = "SPY"

TRADE_HISTORY_FILE = (
    BASE_DIR / "agents" / "trade_history.csv"
)

TRADE_STATE_FILE = (
    BASE_DIR / "agents" / "trade_state.json"
)

MIN_CONFIDENCE = 70.0

STOP_LOSS_PCT = 25.0
TAKE_PROFIT_PCT = 50.0

MAX_ACCOUNT_RISK_PCT = 1.0
MAX_EXPOSURE_PCT = 5.0

MIN_OI = 100
MAX_STRIKE_DISTANCE = 15.0

MIN_DTE = 7
MAX_DTE = 30

CONTRACT_MULTIPLIER = 100


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AlphaPilot AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PROFESSIONAL UI
# ============================================================

st.markdown(
    """
<style>

html, body, [class*="css"] {
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 20% 0%,
            rgba(37,99,235,.10),
            transparent 28%
        ),
        radial-gradient(
            circle at 80% 0%,
            rgba(14,165,233,.07),
            transparent 25%
        ),
        #070b12;

    color: #e5e7eb;
}

.block-container {
    max-width: 1500px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.hero {
    padding: 28px 30px;
    border: 1px solid #1e293b;
    border-radius: 18px;

    background:
        linear-gradient(
            135deg,
            rgba(15,23,42,.97),
            rgba(8,15,27,.97)
        );

    box-shadow:
        0 20px 60px rgba(0,0,0,.30);

    margin-bottom: 20px;
}

.hero-title {
    font-size: 38px;
    line-height: 1.1;
    font-weight: 850;
    letter-spacing: -1px;
    color: #f8fafc;
}

.hero-subtitle {
    margin-top: 8px;
    color: #94a3b8;
    font-size: 15px;
}

.status-row {
    display: flex;
    gap: 9px;
    margin-top: 18px;
    flex-wrap: wrap;
}

.badge {
    display: inline-flex;
    align-items: center;

    padding: 6px 11px;

    border-radius: 999px;

    font-size: 11px;
    font-weight: 800;
    letter-spacing: .5px;

    border: 1px solid;
}

.badge-green {
    color: #4ade80;
    background: rgba(34,197,94,.08);
    border-color: rgba(34,197,94,.25);
}

.badge-blue {
    color: #60a5fa;
    background: rgba(59,130,246,.08);
    border-color: rgba(59,130,246,.25);
}

.badge-orange {
    color: #fb923c;
    background: rgba(249,115,22,.08);
    border-color: rgba(249,115,22,.25);
}

.section-title {
    color: #f8fafc;
    font-size: 21px;
    font-weight: 800;

    margin-top: 28px;
    margin-bottom: 13px;
}

.panel {
    background:
        linear-gradient(
            145deg,
            #0c121d,
            #0a1019
        );

    border: 1px solid #1e293b;

    border-radius: 15px;

    padding: 18px;

    min-height: 100%;

    box-shadow:
        0 10px 35px rgba(0,0,0,.18);
}

.panel-title {
    font-size: 14px;
    font-weight: 800;
    color: #e2e8f0;
}

.small-muted {
    color: #64748b;
    font-size: 12px;
    line-height: 1.55;
}

.metric-label {
    color: #64748b;
    font-size: 11px;

    text-transform: uppercase;

    letter-spacing: .7px;

    font-weight: 800;
}

.metric-value {
    color: #f8fafc;

    font-size: 24px;

    font-weight: 850;

    margin-top: 4px;
}

.metric-value.negative {
    color: #f87171;
}

.metric-value.positive {
    color: #4ade80;
}

.metric-value.warning {
    color: #fbbf24;
}

.market-price {
    color: #f8fafc;

    font-size: 27px;

    font-weight: 850;

    margin-top: 7px;
}

.workflow-card {
    background: #0b111b;

    border: 1px solid #1e293b;

    border-radius: 13px;

    padding: 16px;

    min-height: 120px;
}

.workflow-number {
    color: #475569;

    font-size: 10px;

    font-weight: 900;

    letter-spacing: 1px;
}

.workflow-name {
    color: #f8fafc;

    font-weight: 750;

    font-size: 14px;

    margin-top: 10px;
}

.workflow-status {
    margin-top: 12px;

    font-size: 11px;

    font-weight: 800;
}

.status-good {
    color: #4ade80;
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

.decision-panel {
    border: 1px solid #1e293b;

    border-radius: 15px;

    padding: 22px;

    background:
        linear-gradient(
            145deg,
            #0d1420,
            #090f18
        );
}

.decision-title {
    color: #fbbf24;

    font-size: 27px;

    font-weight: 900;
}

.terminal {
    background: #030712;

    border: 1px solid #172033;

    border-radius: 14px;

    padding: 17px;

    font-family:
        "Cascadia Code",
        "Consolas",
        monospace;

    min-height: 270px;

    max-height: 430px;

    overflow-y: auto;
}

.terminal-line {
    margin: 5px 0;

    font-size: 12px;

    line-height: 1.5;
}

.terminal-ok {
    color: #4ade80;
}

.terminal-info {
    color: #60a5fa;
}

.terminal-warn {
    color: #fbbf24;
}

.terminal-error {
    color: #f87171;
}

.contract-name {
    color: #f8fafc;

    font-size: 17px;

    font-weight: 850;
}

.contract-subtitle {
    color: #64748b;

    font-size: 11px;

    margin-top: 3px;
}

.risk-pass {
    color: #4ade80 !important;
}

.risk-fail {
    color: #f87171 !important;
}

.footer-note {
    text-align: center;

    color: #475569;

    font-size: 11px;

    margin-top: 35px;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #1e293b;

    border-radius: 12px;

    overflow: hidden;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# ALPACA CLIENTS
# ============================================================

if not API_KEY or not SECRET_KEY:

    st.error(
        "ALPACA_API_KEY / ALPACA_SECRET_KEY missing. "
        "Check your .env file."
    )

    st.stop()


try:

    trading_client = TradingClient(
        API_KEY,
        SECRET_KEY,
        paper=PAPER,
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

    st.error(
        f"Alpaca connection failed: {exc}"
    )

    st.stop()


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_float(
    value,
    default=0.0,
):

    try:

        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except Exception:

        return default


def safe_int(
    value,
    default=0,
):

    try:

        if value is None:
            return default

        if pd.isna(value):
            return default

        return int(
            float(value)
        )

    except Exception:

        return default


def money(value):

    return (
        f"${safe_float(value):,.2f}"
    )


def signed_money(value):

    value = safe_float(value)

    if value < 0:

        return (
            f"-${abs(value):,.2f}"
        )

    return (
        f"${value:,.2f}"
    )


def signed_pct(value):

    value = safe_float(value)

    if value < 0:

        return (
            f"{value:.2f}%"
        )

    return (
        f"+{value:.2f}%"
    )


def get_attr(
    obj,
    name,
    default=None,
):

    try:

        return getattr(
            obj,
            name,
            default,
        )

    except Exception:

        return default


def fmt_datetime(value):

    try:

        if value is None:
            return "-"

        dt = pd.to_datetime(
            value,
            utc=True,
        )

        return dt.strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    except Exception:

        return str(value)


# ============================================================
# ACCOUNT / MARKET
# ============================================================

def get_account():

    return (
        trading_client
        .get_account()
    )


def get_market_clock():

    return (
        trading_client
        .get_clock()
    )


def get_positions():

    try:

        return (
            trading_client
            .get_all_positions()
        )

    except Exception:

        return []


def get_orders(
    limit=25,
):

    try:

        request = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit,
        )

        orders = (
            trading_client
            .get_orders(
                filter=request
            )
        )

        return list(
            orders or []
        )

    except Exception as exc:

        st.warning(
            f"Unable to retrieve orders: {exc}"
        )

        return []


# ============================================================
# STOCK DATA NORMALIZATION
# ============================================================

def normalize_stock_bars(
    raw_df,
):

    if raw_df is None:
        return pd.DataFrame()

    df = raw_df.copy()

    if df.empty:
        return pd.DataFrame()

    # --------------------------------------------
    # MultiIndex handling
    # --------------------------------------------

    if isinstance(
        df.index,
        pd.MultiIndex,
    ):

        names = list(
            df.index.names
        )

        symbol_level = None

        for i, name in enumerate(
            names
        ):

            if str(name).lower() in {
                "symbol",
                "symbols",
            }:

                symbol_level = i

                break

        if symbol_level is not None:

            try:

                df = df.xs(
                    SYMBOL,
                    level=symbol_level,
                )

            except Exception:

                try:

                    df = df.xs(
                        SYMBOL,
                        level=names[
                            symbol_level
                        ],
                    )

                except Exception:
                    pass

        if isinstance(
            df.index,
            pd.MultiIndex,
        ):

            df = df.reset_index()

    # --------------------------------------------
    # Timestamp handling
    # --------------------------------------------

    timestamp_column = None

    for col in [
        "timestamp",
        "datetime",
        "date",
        "time",
    ]:

        if col in df.columns:

            timestamp_column = col

            break

    if timestamp_column:

        df[
            timestamp_column
        ] = pd.to_datetime(
            df[
                timestamp_column
            ],
            utc=True,
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                timestamp_column
            ]
        )

        df = df.set_index(
            timestamp_column
        )

    else:

        try:

            df.index = pd.to_datetime(
                df.index,
                utc=True,
                errors="coerce",
            )

            df = df[
                ~pd.isna(df.index)
            ]

        except Exception:

            return pd.DataFrame()

    # --------------------------------------------
    # Standardize columns
    # --------------------------------------------

    rename_map = {}

    for col in df.columns:

        lower = str(
            col
        ).lower()

        if lower == "open":
            rename_map[col] = "open"

        elif lower == "high":
            rename_map[col] = "high"

        elif lower == "low":
            rename_map[col] = "low"

        elif lower == "close":
            rename_map[col] = "close"

        elif lower == "volume":
            rename_map[col] = "volume"

    df = df.rename(
        columns=rename_map
    )

    required = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for col in required:

        if col not in df.columns:

            return pd.DataFrame()

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.dropna(
        subset=required
    )

    df = df.sort_index()

    return df


# ============================================================
# ROBUST SPY HISTORICAL DATA
# ============================================================

def fetch_spy_daily_bars():

    now_utc = datetime.now(
        timezone.utc
    )

    # Try several real Alpaca windows.
    windows = [
        365,
        270,
        180,
        120,
        90,
    ]

    errors = []

    for days in windows:

        start_utc = (
            now_utc
            - timedelta(
                days=days
            )
        )

        try:

            request = StockBarsRequest(
                symbol_or_symbols=[SYMBOL],
                timeframe=TimeFrame.Day,
                start=start_utc,
                end=now_utc,
                limit=1000,
                feed=DataFeed.IEX,
            )

            response = (
                stock_client
                .get_stock_bars(
                    request
                )
            )

            raw_df = getattr(
                response,
                "df",
                None,
            )

            df = normalize_stock_bars(
                raw_df
            )

            if not df.empty:

                if len(df) >= 60:

                    return df

                errors.append(
                    f"{days}d window returned "
                    f"only {len(df)} bars"
                )

            else:

                errors.append(
                    f"{days}d window returned no bars"
                )

        except Exception as exc:

            errors.append(
                f"{days}d request failed: {exc}"
            )

    raise ValueError(
        "No usable SPY historical market data "
        "returned by Alpaca IEX. "
        + " | ".join(errors)
    )


# ============================================================
# LATEST REAL SPY TRADE
# ============================================================

def get_latest_spy_trade():

    try:

        request = StockLatestTradeRequest(
            symbol_or_symbols=[SYMBOL],
            feed=DataFeed.IEX,
        )

        response = (
            stock_client
            .get_stock_latest_trade(
                request
            )
        )

        trade = response[
            SYMBOL
        ]

        price = safe_float(
            get_attr(
                trade,
                "price",
                0,
            )
        )

        timestamp = get_attr(
            trade,
            "timestamp",
            None,
        )

        return price, timestamp

    except Exception:

        return 0.0, None


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

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    rs = (
        avg_gain
        /
        avg_loss.replace(
            0,
            pd.NA,
        )
    )

    rsi = (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )

    return rsi.fillna(50)


# ============================================================
# MARKET ANALYSIS
# ============================================================

def analyze_market():

    df = fetch_spy_daily_bars()

    if df.empty:

        raise ValueError(
            "SPY market data dataframe is empty."
        )

    df = df.copy()

    # --------------------------------------------
    # SMA
    # --------------------------------------------

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

    # --------------------------------------------
    # RSI
    # --------------------------------------------

    df["rsi"] = calculate_rsi(
        df["close"],
        14,
    )

    # --------------------------------------------
    # MACD
    # --------------------------------------------

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

    # --------------------------------------------
    # Volume
    # --------------------------------------------

    df["volume_ma20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    latest = df.iloc[-1]

    price = safe_float(
        latest["close"]
    )

    sma20 = safe_float(
        latest["sma20"]
    )

    sma50 = safe_float(
        latest["sma50"]
    )

    rsi = safe_float(
        latest["rsi"]
    )

    macd = safe_float(
        latest["macd"]
    )

    macd_signal = safe_float(
        latest["macd_signal"]
    )

    volume = safe_float(
        latest["volume"]
    )

    volume_ma20 = safe_float(
        latest["volume_ma20"]
    )

    # --------------------------------------------
    # Conditions
    # --------------------------------------------

    conditions = {

        "Price > SMA20":
            price > sma20,

        "SMA20 > SMA50":
            sma20 > sma50,

        "RSI > 50":
            rsi > 50,

        "MACD > Signal":
            macd > macd_signal,

        "Volume Confirmation":
            volume > volume_ma20,
    }

    passed = sum(
        1
        for value in conditions.values()
        if value
    )

    confidence = (
        passed
        /
        len(conditions)
        *
        100
    )

    decision = (
        "BUY"
        if confidence >= MIN_CONFIDENCE
        else "NO TRADE"
    )

    return {

        "df": df,

        "price": price,

        "sma20": sma20,

        "sma50": sma50,

        "rsi": rsi,

        "macd": macd,

        "macd_signal": macd_signal,

        "volume": volume,

        "volume_ma20": volume_ma20,

        "conditions": conditions,

        "passed": passed,

        "total_conditions":
            len(conditions),

        "confidence": confidence,

        "decision": decision,

        "bars": len(df),

        "start": df.index[0],

        "end": df.index[-1],

        "as_of": df.index[-1],
    }


# ============================================================
# OPTION CONTRACT PARSER
# ============================================================

def parse_option_contract(
    contract,
):

    symbol = str(
        get_attr(
            contract,
            "symbol",
            "",
        )
    )

    strike = safe_float(
        get_attr(
            contract,
            "strike_price",
            0,
        )
    )

    expiration = get_attr(
        contract,
        "expiration_date",
        None,
    )

    if expiration is None:

        expiration_date = None

    else:

        try:

            expiration_date = (
                pd.to_datetime(
                    expiration
                ).date()
            )

        except Exception:

            expiration_date = None

    open_interest = safe_int(
        get_attr(
            contract,
            "open_interest",
            0,
        )
    )

    return {

        "symbol": symbol,

        "strike": strike,

        "expiration":
            expiration_date,

        "open_interest":
            open_interest,
    }


# ============================================================
# OPTION QUOTE
# ============================================================

def get_option_quote(
    symbol,
):

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=[
                symbol
            ],
        )

        response = (
            option_client
            .get_option_latest_quote(
                request
            )
        )

        quote = response[
            symbol
        ]

        bid = safe_float(
            get_attr(
                quote,
                "bid_price",
                0,
            )
        )

        ask = safe_float(
            get_attr(
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
                bid + ask
            ) / 2

        elif ask > 0:

            midpoint = ask

        elif bid > 0:

            midpoint = bid

        else:

            midpoint = 0.0

        return {

            "bid": bid,

            "ask": ask,

            "mid": midpoint,
        }

    except Exception:

        return {

            "bid": 0.0,

            "ask": 0.0,

            "mid": 0.0,
        }


# ============================================================
# OPTION SCANNER
# ============================================================

def scan_options(
    spy_price,
):

    if spy_price <= 0:

        raise ValueError(
            "Real SPY price unavailable; "
            "option scan blocked."
        )

    today = datetime.now(
        timezone.utc
    ).date()

    min_expiration = (
        today
        +
        timedelta(
            days=MIN_DTE
        )
    )

    max_expiration = (
        today
        +
        timedelta(
            days=MAX_DTE
        )
    )

    # IMPORTANT:
    # Alpaca's GetOptionContractsRequest
    # expects strike bounds as STRINGS.
    strike_low = round(
        spy_price
        -
        MAX_STRIKE_DISTANCE,
        2,
    )

    strike_high = round(
        spy_price
        +
        MAX_STRIKE_DISTANCE,
        2,
    )

    request = GetOptionContractsRequest(

        underlying_symbols=[
            SYMBOL
        ],

        type=ContractType.CALL,

        status="active",

        expiration_date_gte=
            min_expiration,

        expiration_date_lte=
            max_expiration,

        strike_price_gte=
            f"{strike_low:.2f}",

        strike_price_lte=
            f"{strike_high:.2f}",
    )

    try:

        response = (
            trading_client
            .get_option_contracts(
                request
            )
        )

        contracts = getattr(
            response,
            "option_contracts",
            response,
        )

        contracts = list(
            contracts or []
        )

    except Exception as exc:

        raise ValueError(
            f"Option contract scan failed: {exc}"
        )

    candidates = []

    for raw_contract in contracts:

        contract = (
            parse_option_contract(
                raw_contract
            )
        )

        if not contract[
            "symbol"
        ]:

            continue

        expiration = contract[
            "expiration"
        ]

        if expiration is None:
            continue

        dte = (
            expiration
            -
            today
        ).days

        if (
            dte < MIN_DTE
            or dte > MAX_DTE
        ):

            continue

        strike = contract[
            "strike"
        ]

        if strike <= 0:
            continue

        distance = abs(
            strike
            -
            spy_price
        )

        if (
            distance
            >
            MAX_STRIKE_DISTANCE
        ):

            continue

        oi = contract[
            "open_interest"
        ]

        if oi < MIN_OI:
            continue

        quote = get_option_quote(
            contract["symbol"]
        )

        mid = quote[
            "mid"
        ]

        # Don't select a contract
        # without a real market quote.
        if mid <= 0:
            continue

        # ----------------------------------------
        # Selection Score
        # ----------------------------------------

        distance_score = max(
            0,
            40
            *
            (
                1
                -
                distance
                /
                MAX_STRIKE_DISTANCE
            ),
        )

        dte_score = max(
            0,
            25
            *
            (
                1
                -
                abs(dte - 14)
                /
                21
            ),
        )

        oi_score = min(
            20,
            math.log10(
                max(
                    oi,
                    1,
                )
            )
            *
            5,
        )

        liquidity_score = 15

        score = (
            distance_score
            +
            dte_score
            +
            oi_score
            +
            liquidity_score
        )

        candidates.append(
            {

                "symbol":
                    contract["symbol"],

                "strike":
                    strike,

                "expiration":
                    expiration,

                "dte":
                    dte,

                "open_interest":
                    oi,

                "bid":
                    quote["bid"],

                "ask":
                    quote["ask"],

                "mid":
                    mid,

                "distance":
                    distance,

                "score":
                    score,
            }
        )

    if not candidates:

        raise ValueError(
            "No suitable real SPY option "
            "contracts were returned."
        )

    candidates.sort(
        key=lambda x:
            x["score"],
        reverse=True,
    )

    return candidates


# ============================================================
# RISK
# ============================================================

def calculate_risk(
    option,
    account,
):

    equity = safe_float(
        get_attr(
            account,
            "equity",
            0,
        )
    )

    if equity <= 0:

        return {

            "passed": False,

            "cost": 0.0,

            "max_account_risk": 0.0,

            "max_exposure": 0.0,

            "reason":
                "Invalid account equity",
        }

    premium = safe_float(
        option.get(
            "mid",
            0,
        )
    )

    cost = (
        premium
        *
        CONTRACT_MULTIPLIER
    )

    max_account_risk = (
        equity
        *
        MAX_ACCOUNT_RISK_PCT
        /
        100
    )

    max_exposure = (
        equity
        *
        MAX_EXPOSURE_PCT
        /
        100
    )

    passed = (
        cost <= max_account_risk
        and
        cost <= max_exposure
        and
        cost > 0
    )

    if cost <= 0:

        reason = (
            "Invalid option premium"
        )

    elif cost > max_account_risk:

        reason = (
            "Exceeds maximum account risk"
        )

    elif cost > max_exposure:

        reason = (
            "Exceeds maximum exposure"
        )

    else:

        reason = (
            "Risk checks passed"
        )

    return {

        "passed":
            passed,

        "cost":
            cost,

        "max_account_risk":
            max_account_risk,

        "max_exposure":
            max_exposure,

        "reason":
            reason,
    }


# ============================================================
# POSITIONS
# ============================================================

def find_option_positions():

    positions = get_positions()

    results = []

    for position in positions:

        symbol = str(
            get_attr(
                position,
                "symbol",
                "",
            )
        )

        asset_class = str(
            get_attr(
                position,
                "asset_class",
                "",
            )
        ).lower()

        if (
            asset_class == "us_option"
            or
            symbol.startswith("SPY")
        ):

            results.append(
                position
            )

    return results


def find_position(
    symbol,
):

    for position in get_positions():

        current_symbol = str(
            get_attr(
                position,
                "symbol",
                "",
            )
        )

        if current_symbol == symbol:

            return position

    return None


def position_qty(
    position,
):

    return abs(
        safe_float(
            get_attr(
                position,
                "qty",
                0,
            )
        )
    )


def position_avg_entry(
    position,
):

    return safe_float(
        get_attr(
            position,
            "avg_entry_price",
            0,
        )
    )


def position_market_price(
    position,
):

    return safe_float(
        get_attr(
            position,
            "current_price",
            0,
        )
    )


def position_market_value(
    position,
):

    return safe_float(
        get_attr(
            position,
            "market_value",
            0,
        )
    )


def position_unrealized_pl(
    position,
):

    return safe_float(
        get_attr(
            position,
            "unrealized_pl",
            0,
        )
    )


def position_unrealized_plpc(
    position,
):

    value = safe_float(
        get_attr(
            position,
            "unrealized_plpc",
            0,
        )
    )

    if abs(value) <= 2:

        return value * 100

    return value


# ============================================================
# TRADE STATE
# ============================================================

def load_trade_state():

    if not TRADE_STATE_FILE.exists():

        return {}

    try:

        with open(
            TRADE_STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return (
                json.load(file)
                or {}
            )

    except Exception:

        return {}


# ============================================================
# TRADE HISTORY
# ============================================================

def load_trade_history():

    columns = [

        "Symbol",

        "Quantity",

        "Entry Price",

        "Exit Price",

        "Entry Value",

        "Exit Value",

        "P&L",

        "P&L %",

        "Entry Time",

        "Exit Time",

        "Reason",
    ]

    if not TRADE_HISTORY_FILE.exists():

        return pd.DataFrame(
            columns=columns
        )

    try:

        df = pd.read_csv(
            TRADE_HISTORY_FILE
        )

    except Exception:

        return pd.DataFrame(
            columns=columns
        )

    if df.empty:

        return df

    numeric_columns = [

        "Quantity",

        "Entry Price",

        "Exit Price",

        "Entry Value",

        "Exit Value",

        "P&L",

        "P&L %",
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    return df


def calculate_performance(
    df,
):

    if (
        df is None
        or
        df.empty
    ):

        return {

            "completed": 0,

            "total_pnl": 0.0,

            "wins": 0,

            "losses": 0,

            "win_rate": 0.0,

            "profit_factor": 0.0,
        }

    pnl = pd.to_numeric(
        df["P&L"],
        errors="coerce",
    ).fillna(0.0)

    wins = pnl[
        pnl > 0
    ]

    losses = pnl[
        pnl < 0
    ]

    total_pnl = safe_float(
        pnl.sum()
    )

    winning_count = len(
        wins
    )

    losing_count = len(
        losses
    )

    total_profit = safe_float(
        wins.sum()
    )

    total_loss = abs(
        safe_float(
            losses.sum()
        )
    )

    completed = len(
        df
    )

    win_rate = (

        winning_count
        /
        completed
        *
        100

        if completed

        else 0.0
    )

    if total_loss > 0:

        profit_factor = (
            total_profit
            /
            total_loss
        )

    else:

        profit_factor = 0.0

    return {

        "completed":
            completed,

        "total_pnl":
            total_pnl,

        "wins":
            winning_count,

        "losses":
            losing_count,

        "win_rate":
            win_rate,

        "profit_factor":
            profit_factor,
    }


# ============================================================
# PAPER BUY
# ============================================================

def submit_paper_buy(
    option_symbol,
):

    existing = find_position(
        option_symbol
    )

    if existing is not None:

        qty = position_qty(
            existing
        )

        if qty > 0:

            return (
                False,
                (
                    f"BUY blocked: existing "
                    f"position detected for "
                    f"{option_symbol} "
                    f"(Qty {qty:g})."
                ),
            )

    try:

        order = MarketOrderRequest(

            symbol=option_symbol,

            qty=1,

            side=OrderSide.BUY,

            time_in_force=
                TimeInForce.DAY,
        )

        submitted = (
            trading_client
            .submit_order(
                order_data=order
            )
        )

        order_id = str(
            get_attr(
                submitted,
                "id",
                "",
            )
        )

        return (

            True,

            (
                f"Paper BUY submitted for "
                f"{option_symbol}. "
                f"Order ID: {order_id}"
            ),
        )

    except Exception as exc:

        return (

            False,

            f"Paper BUY failed: {exc}",
        )


# ============================================================
# INITIAL REAL DATA
# ============================================================

try:

    account = get_account()

    market_clock = (
        get_market_clock()
    )

    positions = get_positions()

    orders = get_orders(
        limit=25
    )

    latest_spy_price, latest_spy_time = (
        get_latest_spy_trade()
    )

except Exception as exc:

    st.error(
        f"Unable to synchronize Alpaca account: {exc}"
    )

    st.stop()


# ============================================================
# MARKET ANALYSIS
# ============================================================

analysis = None
analysis_error = None

try:

    analysis = analyze_market()

except Exception as exc:

    analysis_error = str(
        exc
    )


# ============================================================
# OPTION SCAN
# ============================================================

selected_option = None

all_candidates = []

option_error = None

if latest_spy_price > 0:

    try:

        all_candidates = (
            scan_options(
                latest_spy_price
            )
        )

        if all_candidates:

            selected_option = (
                all_candidates[0].copy()
            )

    except Exception as exc:

        option_error = str(
            exc
        )


# ============================================================
# RISK
# ============================================================

risk = None

if selected_option:

    risk = calculate_risk(
        selected_option,
        account,
    )


# ============================================================
# PERFORMANCE
# ============================================================

trade_history = (
    load_trade_history()
)

performance = (
    calculate_performance(
        trade_history
    )
)

trade_state = (
    load_trade_state()
)


# ============================================================
# ACCOUNT VALUES
# ============================================================

equity = safe_float(
    get_attr(
        account,
        "equity",
        0,
    )
)

buying_power = safe_float(
    get_attr(
        account,
        "buying_power",
        0,
    )
)

cash = safe_float(
    get_attr(
        account,
        "cash",
        0,
    )
)

last_equity = safe_float(
    get_attr(
        account,
        "last_equity",
        equity,
    )
)

day_pnl = (
    equity
    -
    last_equity
)

open_option_positions = (
    find_option_positions()
)

market_open = bool(
    get_attr(
        market_clock,
        "is_open",
        False,
    )
)


# ============================================================
# HERO
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
# ACCOUNT OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-title">'
    '💰 Account Overview'
    '</div>',
    unsafe_allow_html=True,
)

cols = st.columns(5)

account_metrics = [

    (
        "Equity",
        money(equity),
        "",
    ),

    (
        "Buying Power",
        money(buying_power),
        "",
    ),

    (
        "Cash",
        money(cash),
        "",
    ),

    (
        "Day P&L",
        signed_money(day_pnl),
        (
            "negative"
            if day_pnl < 0
            else "positive"
        ),
    ),

    (
        "Open Positions",
        str(
            len(
                open_option_positions
            )
        ),
        "",
    ),
]

for col, (
    label,
    value,
    css_class,
) in zip(
    cols,
    account_metrics,
):

    with col:

        st.markdown(
            f"""
<div class="panel">

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
    '<div class="section-title">'
    '🌐 Market Status'
    '</div>',
    unsafe_allow_html=True,
)

cols = st.columns(3)

with cols[0]:

    market_color = (
        "#4ade80"
        if market_open
        else "#fbbf24"
    )

    market_text = (
        "US MARKET OPEN"
        if market_open
        else "US MARKET CLOSED"
    )

    st.markdown(
        f"""
<div class="panel">

    <div class="panel-title">

        <span style="
            color:{market_color};
        ">

            ● {market_text}

        </span>

    </div>

    <div class="small-muted">
        Alpaca market clock
    </div>

</div>
""",
        unsafe_allow_html=True,
    )


with cols[1]:

    price_text = (
        money(
            latest_spy_price
        )
        if latest_spy_price > 0
        else "UNAVAILABLE"
    )

    st.markdown(
        f"""
<div class="panel">

    <div class="panel-title">
        SPY Last IEX Trade
    </div>

    <div class="market-price">
        {price_text}
    </div>

    <div class="small-muted">
        Real Alpaca IEX trade
    </div>

</div>
""",
        unsafe_allow_html=True,
    )


with cols[2]:

    st.markdown(
        """
<div class="panel">

    <div class="panel-title">
        Agent Mode
    </div>

    <div class="market-price"
         style="font-size:22px;">
        Copilot
    </div>

    <div class="small-muted">
        Analysis + explicit dashboard confirmation
    </div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# WORKFLOW
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🧭 AlphaPilot Workflow'
    '</div>',
    unsafe_allow_html=True,
)

workflow_cols = st.columns(4)

workflow = [

    (
        "STEP 01",
        "🛡️ Configure Risk Guards",
        "✓ ACTIVE",
        "status-good",
    ),

    (
        "STEP 02",
        "🧠 AI Market Scan",
        (
            "✓ SCAN COMPLETE"
            if analysis
            else "⚠ DATA ERROR"
        ),
        (
            "status-info"
            if analysis
            else "status-bad"
        ),
    ),

    (
        "STEP 03",
        "🎯 Decision & Entry",

        (
            f"✓ {analysis['decision']} • "
            f"{analysis['confidence']:.0f}%"
            if analysis
            else "⚠ NO SCAN"
        ),

        (
            "status-info"
            if analysis
            else "status-warn"
        ),
    ),

    (
        "STEP 04",
        "📈 Monitor Performance",
        "✓ MONITORING",
        "status-good",
    ),
]

for col, item in zip(
    workflow_cols,
    workflow,
):

    with col:

        number, name, status, css = item

        st.markdown(
            f"""
<div class="workflow-card">

    <div class="workflow-number">
        {number}
    </div>

    <div class="workflow-name">
        {name}
    </div>

    <div class="workflow-status">

        <span class="{css}">
            {status}
        </span>

    </div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# AGENT CONTROLS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '⚡ Agent Controls'
    '</div>',
    unsafe_allow_html=True,
)

control_cols = st.columns(3)

with control_cols[0]:

    st.markdown(
        """
<div class="panel">

    <div class="panel-title">
        🤖 Copilot Decision Center
    </div>

    <div class="small-muted"
         style="margin-top:9px;">

        AlphaPilot analyzes real market data,
        evaluates options, and applies risk guards.

        <br><br>

        Paper order submission remains explicitly
        controlled from the dashboard.

    </div>

</div>
""",
        unsafe_allow_html=True,
    )


with control_cols[1]:

    if st.button(
        "🔄 Run Market Scan",
        use_container_width=True,
    ):

        st.rerun()


with control_cols[2]:

    if st.button(
        "↻ Refresh Dashboard",
        use_container_width=True,
    ):

        st.rerun()


# ============================================================
# AGENT TERMINAL
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🖥️ Agent Activity Terminal'
    '</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Real AlphaPilot execution and decision events. "
    "No fabricated AI thoughts or performance data."
)

activity = []

now = datetime.now(
    timezone.utc
)

activity.append(
    (
        now,
        "ok",
        "Connected to Alpaca PAPER "
        "trading environment",
    )
)

activity.append(
    (
        now,
        "ok",
        f"Account synchronized • "
        f"Equity {money(equity)}",
    )
)

for position in open_option_positions:

    position_symbol = str(
        get_attr(
            position,
            "symbol",
            "",
        )
    )

    qty = position_qty(
        position
    )

    entry = position_avg_entry(
        position
    )

    activity.append(
        (
            now,
            "info",
            f"Open position detected • "
            f"{position_symbol} • "
            f"Qty {qty:g}",
        )
    )

    activity.append(
        (
            now,
            "info",
            f"Position entry synchronized • "
            f"{money(entry)}",
        )
    )

if analysis:

    activity.append(
        (
            now,
            "ok",
            f"Market scan complete • "
            f"{analysis['bars']} daily bars • "
            f"Confidence "
            f"{analysis['confidence']:.0f}%",
        )
    )

    activity.append(
        (
            now,
            "info",
            f"SPY {money(analysis['price'])} • "
            f"SMA20 {money(analysis['sma20'])} • "
            f"SMA50 {money(analysis['sma50'])}",
        )
    )

    activity.append(
        (
            now,
            "info",
            f"Decision engine returned "
            f"{analysis['decision']}",
        )
    )

else:

    activity.append(
        (
            now,
            "error",
            f"Market scan failed: "
            f"{analysis_error}",
        )
    )

if selected_option:

    activity.append(
        (
            now,
            "ok",
            f"Option scan complete • "
            f"{len(all_candidates)} "
            f"candidates",
        )
    )

    activity.append(
        (
            now,
            "info",
            f"Top contract "
            f"{selected_option['symbol']} • "
            f"Score "
            f"{selected_option['score']:.2f}",
        )
    )

    if risk:

        activity.append(
            (
                now,
                (
                    "ok"
                    if risk["passed"]
                    else "error"
                ),
                (
                    f"Risk check "
                    f"{'PASSED' if risk['passed'] else 'FAILED'} • "
                    f"Cost {money(risk['cost'])}"
                ),
            )
        )

else:

    activity.append(
        (
            now,
            "warn",
            (
                "Option scan unavailable • "
                f"{option_error or 'No candidate'}"
            ),
        )
    )

activity.append(
    (
        now,
        "info",
        (
            "Market is OPEN"
            if market_open
            else "Market is CLOSED"
        ),
    )
)

terminal_html = (
    '<div class="terminal">'
)

for (
    timestamp,
    event_type,
    message,
) in activity:

    css_class = {

        "ok":
            "terminal-ok",

        "info":
            "terminal-info",

        "warn":
            "terminal-warn",

        "error":
            "terminal-error",

    }.get(
        event_type,
        "terminal-info",
    )

    icon = {

        "ok":
            "✓",

        "info":
            "→",

        "warn":
            "⚠",

        "error":
            "✕",

    }.get(
        event_type,
        "→",
    )

    terminal_html += (
        '<div class="terminal-line">'
        f'<span style="color:#475569;">'
        f'[{timestamp.strftime("%H:%M:%S")}]'
        f'</span> '
        f'<span class="{css_class}">'
        f'{icon} {message}'
        f'</span>'
        '</div>'
    )

terminal_html += (
    "</div>"
)

st.markdown(
    terminal_html,
    unsafe_allow_html=True,
)


# ============================================================
# COPILOT DECISION CENTER
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🤖 Copilot Decision Center'
    '</div>',
    unsafe_allow_html=True,
)

decision_cols = st.columns(
    [1, 2]
)

with decision_cols[0]:

    if analysis:

        confidence = (
            analysis["confidence"]
        )

        decision = (
            analysis["decision"]
        )

        if decision == "BUY":

            title = "🟢 BUY SIGNAL"

            title_color = (
                "#4ade80"
            )

        else:

            title = "🟡 NO TRADE"

            title_color = (
                "#fbbf24"
            )

        st.markdown(
            f"""
<div class="decision-panel">

    <div class="decision-title"
         style="color:{title_color};">

        {title}

    </div>

    <div class="small-muted"
         style="margin-top:8px;">

        Current technical conditions
        {'met' if decision == 'BUY' else 'did not meet'}
        the configured confidence threshold.

    </div>

    <div style="
        margin-top:14px;
        font-size:25px;
        font-weight:800;
        color:#f8fafc;
    ">

        {confidence:.1f}%

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
            """
<div class="decision-panel">

    <div class="decision-title"
         style="color:#f87171;">

        🔴 SCAN ERROR

    </div>

    <div class="small-muted"
         style="margin-top:10px;">

        No technical decision was generated
        because real historical SPY data was
        unavailable.

    </div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# TECHNICAL CONDITIONS
# ============================================================

with decision_cols[1]:

    st.markdown(
        '<div class="panel-title">'
        'Technical Conditions'
        '</div>',
        unsafe_allow_html=True,
    )

    if analysis:

        condition_rows = []

        for condition, passed in (
            analysis[
                "conditions"
            ].items()
        ):

            condition_rows.append(
                {
                    "Condition":
                        condition,

                    "Status":
                        (
                            "PASS"
                            if passed
                            else "FAIL"
                        ),
                }
            )

        condition_df = pd.DataFrame(
            condition_rows
        )

        st.dataframe(
            condition_df,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            f"""
<div class="small-muted">

    Data source: Alpaca IEX •
    {analysis['bars']} daily bars

    <br><br>

    Historical range:
    {fmt_datetime(analysis['start'])}
    →
    {fmt_datetime(analysis['end'])}

    <br><br>

    Technical data as-of:
    {fmt_datetime(analysis['as_of'])}

    <br><br>

    Scan time:
    {datetime.now(timezone.utc).isoformat()}

</div>
""",
            unsafe_allow_html=True,
        )

    else:

        st.error(
            f"Market scan failed: "
            f"{analysis_error}"
        )


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📊 Technical Analysis'
    '</div>',
    unsafe_allow_html=True,
)

if analysis:

    cols = st.columns(5)

    technical_metrics = [

        (
            "SPY",
            money(
                analysis["price"]
            ),
        ),

        (
            "SMA20",
            money(
                analysis["sma20"]
            ),
        ),

        (
            "SMA50",
            money(
                analysis["sma50"]
            ),
        ),

        (
            "RSI",
            f"{analysis['rsi']:.2f}",
        ),

        (
            "MACD",
            f"{analysis['macd']:.4f}",
        ),
    ]

    for col, (
        label,
        value,
    ) in zip(
        cols,
        technical_metrics,
    ):

        with col:

            st.markdown(
                f"""
<div class="panel">

    <div class="metric-label">
        {label}
    </div>

    <div class="metric-value"
         style="font-size:20px;">

        {value}

    </div>

</div>
""",
                unsafe_allow_html=True,
            )

else:

    st.warning(
        "Technical analysis unavailable."
    )


# ============================================================
# SELECTED OPTION
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🎯 Selected Option'
    '</div>',
    unsafe_allow_html=True,
)

if selected_option:

    cols = st.columns(5)

    option_metrics = [

        (
            "Contract",
            selected_option[
                "symbol"
            ],
        ),

        (
            "Strike",
            money(
                selected_option[
                    "strike"
                ]
            ),
        ),

        (
            "DTE",
            str(
                selected_option[
                    "dte"
                ]
            ),
        ),

        (
            "Open Interest",
            f"{selected_option['open_interest']:,}",
        ),

        (
            "Selection Score",
            f"{selected_option['score']:.2f}",
        ),
    ]

    for col, (
        label,
        value,
    ) in zip(
        cols,
        option_metrics,
    ):

        with col:

            st.markdown(
                f"""
<div class="panel">

    <div class="metric-label">
        {label}
    </div>

    <div class="metric-value"
         style="font-size:18px;">

        {value}

    </div>

</div>
""",
                unsafe_allow_html=True,
            )

    quote_cols = st.columns(3)

    with quote_cols[0]:

        st.metric(
            "Bid",
            money(
                selected_option[
                    "bid"
                ]
            ),
        )

    with quote_cols[1]:

        st.metric(
            "Ask",
            money(
                selected_option[
                    "ask"
                ]
            ),
        )

    with quote_cols[2]:

        st.metric(
            "Mid",
            money(
                selected_option[
                    "mid"
                ]
            ),
        )

else:

    st.warning(
        "Option scan unavailable: "
        f"{option_error or 'No real candidate selected.'}"
    )


# ============================================================
# RISK ASSESSMENT
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🛡️ Risk Assessment'
    '</div>',
    unsafe_allow_html=True,
)

if risk:

    risk_status = (
        "PASS"
        if risk["passed"]
        else "FAIL"
    )

    risk_class = (
        "risk-pass"
        if risk["passed"]
        else "risk-fail"
    )

    cols = st.columns(4)

    risk_metrics = [

        (
            "Risk Status",
            risk_status,
        ),

        (
            "Option Cost",
            money(
                risk["cost"]
            ),
        ),

        (
            "Max Account Risk",
            money(
                risk[
                    "max_account_risk"
                ]
            ),
        ),

        (
            "Max Exposure",
            money(
                risk[
                    "max_exposure"
                ]
            ),
        ),
    ]

    for col, (
        label,
        value,
    ) in zip(
        cols,
        risk_metrics,
    ):

        with col:

            css = (
                risk_class
                if label ==
                "Risk Status"
                else ""
            )

            st.markdown(
                f"""
<div class="panel">

    <div class="metric-label">
        {label}
    </div>

    <div class="metric-value {css}"
         style="font-size:18px;">

        {value}

    </div>

</div>
""",
                unsafe_allow_html=True,
            )

    st.caption(
        risk["reason"]
    )

else:

    st.info(
        "Risk assessment unavailable until "
        "a real option candidate is selected."
    )


# ============================================================
# PAPER ENTRY CONTROL
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🎯 Paper Entry Control'
    '</div>',
    unsafe_allow_html=True,
)

if selected_option:

    can_trade = (

        analysis is not None

        and
        analysis["decision"] ==
        "BUY"

        and
        risk is not None

        and
        risk["passed"]

        and
        market_open
    )

    if not market_open:

        st.info(
            "US market is closed. "
            "Paper order submission is disabled."
        )

    elif analysis and analysis[
        "decision"
    ] != "BUY":

        st.warning(
            f"Entry blocked: technical confidence "
            f"{analysis['confidence']:.1f}% is below "
            f"the required "
            f"{MIN_CONFIDENCE:.0f}%."
        )

    elif risk and not risk[
        "passed"
    ]:

        st.error(
            f"Entry blocked by risk guard: "
            f"{risk['reason']}"
        )

    else:

        st.success(
            "Real technical signal and risk checks passed."
        )

    entry_confirmed = st.checkbox(
        "I confirm this is a PAPER trade.",
        value=False,
        disabled=not can_trade,
    )

    if st.button(
        "🚀 Submit Paper BUY",
        use_container_width=True,
        disabled=(
            not can_trade
            or
            not entry_confirmed
        ),
    ):

        success, message = (
            submit_paper_buy(
                selected_option[
                    "symbol"
                ]
            )
        )

        if success:

            st.success(
                message
            )

            st.rerun()

        else:

            st.error(
                message
            )

else:

    st.info(
        "Paper entry unavailable because "
        "no real option contract was selected."
    )


# ============================================================
# ACTIVE OPTION CONTRACTS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📌 Active Option Contracts'
    '</div>',
    unsafe_allow_html=True,
)

if open_option_positions:

    for position in (
        open_option_positions
    ):

        position_symbol = str(
            get_attr(
                position,
                "symbol",
                "",
            )
        )

        qty = position_qty(
            position
        )

        entry = position_avg_entry(
            position
        )

        current = position_market_price(
            position
        )

        market_value = (
            position_market_value(
                position
            )
        )

        unrealized = (
            position_unrealized_pl(
                position
            )
        )

        return_pct = (
            position_unrealized_plpc(
                position
            )
        )

        stop_price = (
            entry
            *
            (
                1
                -
                STOP_LOSS_PCT
                /
                100
            )
        )

        target_price = (
            entry
            *
            (
                1
                +
                TAKE_PROFIT_PCT
                /
                100
            )
        )

        state_symbol = str(
            trade_state.get(
                "symbol",
                "",
            )
        )

        state_status = str(
            trade_state.get(
                "status",
                "OPEN",
            )
        )

        if (
            state_symbol
            !=
            position_symbol
        ):

            state_status = "OPEN"

        st.markdown(
            f"""
<div class="panel">

    <div class="contract-name">
        {position_symbol}
    </div>

    <div class="contract-subtitle">
        Active paper position • Alpaca
    </div>

</div>
""",
            unsafe_allow_html=True,
        )

        cols = st.columns(8)

        position_metrics = [

            (
                "Qty",
                f"{qty:g}",
            ),

            (
                "Entry",
                money(entry),
            ),

            (
                "Current",
                money(current),
            ),

            (
                "Market Value",
                money(market_value),
            ),

            (
                "Unrealized P&L",
                signed_money(
                    unrealized
                ),
            ),

            (
                "Return",
                signed_pct(
                    return_pct
                ),
            ),

            (
                "Stop",
                money(
                    stop_price
                ),
            ),

            (
                "Target",
                money(
                    target_price
                ),
            ),
        ]

        for col, (
            label,
            value,
        ) in zip(
            cols,
            position_metrics,
        ):

            with col:

                value_class = ""

                if (
                    label ==
                    "Unrealized P&L"
                    and
                    unrealized < 0
                ):

                    value_class = (
                        "negative"
                    )

                elif (
                    label ==
                    "Unrealized P&L"
                    and
                    unrealized > 0
                ):

                    value_class = (
                        "positive"
                    )

                elif (
                    label ==
                    "Return"
                    and
                    return_pct < 0
                ):

                    value_class = (
                        "negative"
                    )

                elif (
                    label ==
                    "Return"
                    and
                    return_pct > 0
                ):

                    value_class = (
                        "positive"
                    )

                st.markdown(
                    f"""
<div class="panel">

    <div class="metric-label">
        {label}
    </div>

    <div class="metric-value {value_class}"
         style="font-size:16px;">

        {value}

    </div>

</div>
""",
                    unsafe_allow_html=True,
                )

        st.markdown(
            f"""
<div class="panel"
     style="margin-top:10px;">

    Exit State:

    <strong style="
        color:#60a5fa;
    ">
        {state_status}
    </strong>

</div>
""",
            unsafe_allow_html=True,
        )

else:

    st.info(
        "No active SPY option positions."
    )


# ============================================================
# PERFORMANCE
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📈 Performance & Risk'
    '</div>',
    unsafe_allow_html=True,
)

cols = st.columns(5)

performance_metrics = [

    (
        "Completed Trades",
        str(
            performance[
                "completed"
            ]
        ),
        "",
    ),

    (
        "Total Realized P&L",
        signed_money(
            performance[
                "total_pnl"
            ]
        ),
        (
            "negative"
            if performance[
                "total_pnl"
            ] < 0
            else "positive"
        ),
    ),

    (
        "Win Rate",
        f"{performance['win_rate']:.2f}%",
        "",
    ),

    (
        "Winning Trades",
        str(
            performance[
                "wins"
            ]
        ),
        "",
    ),

    (
        "Profit Factor",
        f"{performance['profit_factor']:.2f}",
        "",
    ),
]

for col, (
    label,
    value,
    css_class,
) in zip(
    cols,
    performance_metrics,
):

    with col:

        st.markdown(
            f"""
<div class="panel">

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

st.markdown(
    '<div class="section-title">'
    '📈 Realized P&L Curve'
    '</div>',
    unsafe_allow_html=True,
)

if (
    trade_history is not None
    and
    not trade_history.empty
):

    chart_df = (
        trade_history.copy()
    )

    chart_df["P&L"] = pd.to_numeric(
        chart_df["P&L"],
        errors="coerce",
    ).fillna(0.0)

    chart_df[
        "Cumulative P&L"
    ] = (
        chart_df["P&L"]
        .cumsum()
    )

    chart_df.index = range(
        1,
        len(chart_df) + 1,
    )

    st.line_chart(
        chart_df[
            ["Cumulative P&L"]
        ],
        use_container_width=True,
        height=260,
    )

    st.caption(
        f"Realized P&L: "
        f"{signed_money(performance['total_pnl'])} "
        f"across "
        f"{performance['completed']} "
        f"completed trade(s)."
    )

else:

    st.info(
        "No completed trades available "
        "for the realized P&L curve."
    )


# ============================================================
# RECENT COMPLETED TRADES
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🧾 Recent Completed Trades'
    '</div>',
    unsafe_allow_html=True,
)

if (
    trade_history is not None
    and
    not trade_history.empty
):

    display_df = (
        trade_history
        .tail(10)
        .copy()
    )

    money_columns = [

        "Entry Price",

        "Exit Price",

        "Entry Value",

        "Exit Value",

        "P&L",
    ]

    for col in money_columns:

        if col in display_df.columns:

            display_df[col] = (
                display_df[col]
                .map(
                    lambda x:
                    money(x)
                )
            )

    if "Quantity" in (
        display_df.columns
    ):

        display_df[
            "Quantity"
        ] = (
            display_df[
                "Quantity"
            ].map(
                lambda x:
                f"{safe_float(x):g}"
            )
        )

    if "P&L %" in (
        display_df.columns
    ):

        display_df[
            "P&L %"
        ] = pd.to_numeric(
            display_df[
                "P&L %"
            ],
            errors="coerce",
        ).map(
            lambda x:
            f"{safe_float(x):.2f}%"
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No completed trades recorded."
    )


# ============================================================
# RECENT ALPACA ORDERS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🧾 Recent Alpaca Orders'
    '</div>',
    unsafe_allow_html=True,
)

if orders:

    order_rows = []

    for order in orders[:10]:

        created_at = get_attr(
            order,
            "created_at",
            None,
        )

        symbol = str(
            get_attr(
                order,
                "symbol",
                "",
            )
        )

        side = str(
            get_attr(
                order,
                "side",
                "",
            )
        ).upper()

        qty = get_attr(
            order,
            "qty",
            "",
        )

        filled_qty = get_attr(
            order,
            "filled_qty",
            "",
        )

        avg_fill = safe_float(
            get_attr(
                order,
                "filled_avg_price",
                0,
            )
        )

        status = str(
            get_attr(
                order,
                "status",
                "",
            )
        ).upper()

        order_rows.append(
            {

                "Created":
                    fmt_datetime(
                        created_at
                    ),

                "Symbol":
                    symbol,

                "Side":
                    side,

                "Qty":
                    str(qty),

                "Filled":
                    str(filled_qty),

                "Avg Fill":
                    (
                        money(
                            avg_fill
                        )
                        if avg_fill > 0
                        else "-"
                    ),

                "Status":
                    status,
            }
        )

    orders_df = pd.DataFrame(
        order_rows
    )

    st.dataframe(
        orders_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No Alpaca orders found."
    )


# ============================================================
# AUTOPILOT STATUS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🤖 Autopilot Status'
    '</div>',
    unsafe_allow_html=True,
)

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

        <br><br>

        Entry decisions are protected by confidence
        and risk guards.

        <br><br>

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
    '<div class="section-title">'
    '📌 Current Trade State'
    '</div>',
    unsafe_allow_html=True,
)

state_status = str(
    trade_state.get(
        "status",
        "NONE",
    )
)

state_symbol = str(
    trade_state.get(
        "symbol",
        "-",
    )
)

state_qty = trade_state.get(
    "quantity",
    0,
)

state_entry = safe_float(
    trade_state.get(
        "entry_price",
        0,
    )
)

state_cols = st.columns(4)

state_metrics = [

    (
        "Status",
        state_status,
    ),

    (
        "Symbol",
        state_symbol,
    ),

    (
        "Quantity",
        str(
            state_qty
        ),
    ),

    (
        "Entry",
        (
            money(
                state_entry
            )
            if state_entry > 0
            else "-"
        ),
    ),
]

for col, (
    label,
    value,
) in zip(
    state_cols,
    state_metrics,
):

    with col:

        st.markdown(
            f"""
<div class="panel">

    <div class="metric-label">
        {label}
    </div>

    <div class="metric-value"
         style="font-size:18px;">

        {value}

    </div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# WORKER INFORMATION
# ============================================================

st.markdown(
    '<div class="section-title">'
    '⚙️ Autonomous Worker Commands'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="panel">

    <div class="panel-title">

        AlphaPilot AI • Alpaca Paper Trading •
        Real Market Data • Real Orders •
        Real Trade History • No Fake Performance

    </div>

    <div class="small-muted"
         style="margin-top:10px;">

        Entry and exit workers operate independently
        from this dashboard.

        <br><br>

        The dashboard reads their real account,
        position, order and trade-state information.

    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer-note">

    AlphaPilot AI • Alpaca PAPER • IEX Market Data •
    Real Account State • Real Orders • Real Trade History

</div>
""",
    unsafe_allow_html=True,
)
