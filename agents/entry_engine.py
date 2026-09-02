"""
AlphaPilot AI — Autonomous Options Entry Worker

PAPER TRADING ONLY

Flow:
    Live SPY market data
        ↓
    Technical AI signal
        ↓
    Confidence >= 70%
        ↓
    CALL option scan
        ↓
    Best contract selection
        ↓
    Risk checks
        ↓
    Market open check
        ↓
    PAPER BUY
        ↓
    Real fill confirmation
        ↓
    Save REAL trade state
        ↓
    Autonomous Exit Worker

No fake trades.
No fake fills.
No fake P&L.

Trade state is created ONLY after Alpaca confirms BUY = FILLED.
Completed trade history is created by the Exit Worker ONLY after
Alpaca confirms SELL = FILLED.
"""

import csv
import os
import time
from datetime import datetime, date, timedelta
from pathlib import Path

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
    OptionLatestQuoteRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOptionContractsRequest,
    MarketOrderRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
)

from agents.trade_state import (
    create_open_trade,
    is_open,
)


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TRADE_HISTORY_FILE = (
    BASE_DIR / "agents" / "trade_history.csv"
)

SYMBOL = "SPY"

# AI
CONFIDENCE_THRESHOLD = 70

# Options
MIN_DTE = 7
MAX_DTE = 30
MAX_STRIKE_DISTANCE = 15.0
MIN_OPEN_INTEREST = 100

# Risk
MAX_ACCOUNT_RISK_PCT = 0.01
MAX_ACCOUNT_EXPOSURE_PCT = 0.05

# Maximum number of contracts per trade
MAX_CONTRACTS = 1

# Worker
CHECK_INTERVAL = 60

# Options multiplier
OPTIONS_MULTIPLIER = 100

# Paper only
PAPER_TRADING = True


# ============================================================
# LOAD .ENV
# ============================================================

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")

except Exception:
    pass


# ============================================================
# CREDENTIALS
# ============================================================

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


if not API_KEY or not SECRET_KEY:

    print()
    print("=" * 70)
    print("❌ Alpaca credentials are missing.")
    print("=" * 70)
    print()
    print("Make sure your .env contains:")
    print()
    print("ALPACA_API_KEY=YOUR_PAPER_API_KEY")
    print("ALPACA_SECRET_KEY=YOUR_PAPER_SECRET_KEY")
    print()

    raise SystemExit(1)


# ============================================================
# CLIENTS
# ============================================================

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=PAPER_TRADING,
)

stock_data_client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY,
)

option_data_client = OptionHistoricalDataClient(
    API_KEY,
    SECRET_KEY,
)


# ============================================================
# HEADER
# ============================================================

def print_header():

    print()
    print("=" * 70)
    print("🚀 AlphaPilot AI — Autonomous Entry Worker")
    print("=" * 70)

    print("Mode: ALPACA PAPER")
    print(f"Symbol: {SYMBOL}")

    print(
        f"AI Confidence Threshold: "
        f"{CONFIDENCE_THRESHOLD}%"
    )

    print(
        f"Option DTE: "
        f"{MIN_DTE}–{MAX_DTE} days"
    )

    print(
        f"Max Strike Distance: "
        f"${MAX_STRIKE_DISTANCE:.2f}"
    )

    print(
        f"Minimum Open Interest: "
        f"{MIN_OPEN_INTEREST}"
    )

    print(
        f"Max Account Risk: "
        f"{MAX_ACCOUNT_RISK_PCT * 100:.1f}%"
    )

    print(
        f"Max Exposure: "
        f"{MAX_ACCOUNT_EXPOSURE_PCT * 100:.1f}%"
    )

    print(
        f"Maximum Contracts: "
        f"{MAX_CONTRACTS}"
    )

    print("Paper BUY: ENABLED")
    print("Real Fill Confirmation: ENABLED")
    print("Trade State Persistence: ENABLED")
    print("Fake Trades: DISABLED")

    print("=" * 70)
    print()


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calculate_sma(values, period):

    if len(values) < period:
        return None

    return sum(values[-period:]) / period


def calculate_rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(
        len(values) - period,
        len(values),
    ):

        change = values[i] - values[i - 1]

        if change > 0:

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(abs(change))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100.0

    rs = average_gain / average_loss

    return 100 - (
        100 / (1 + rs)
    )


def calculate_ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(values[:period]) / period

    for price in values[period:]:

        ema = (
            (price - ema)
            * multiplier
        ) + ema

    return ema


def calculate_macd(values):

    if len(values) < 35:
        return None, None

    ema12 = calculate_ema(
        values,
        12,
    )

    ema26 = calculate_ema(
        values,
        26,
    )

    if ema12 is None or ema26 is None:
        return None, None

    macd = ema12 - ema26

    # Current AlphaPilot strategy uses zero
    # as the bullish MACD baseline.
    signal = 0.0

    return macd, signal


# ============================================================
# MARKET DATA
# ============================================================

def get_spy_data():

    try:

        request = StockBarsRequest(
            symbol_or_symbols=[SYMBOL],
            timeframe=TimeFrame.Day,
            limit=100,
            feed=DataFeed.IEX,
        )

        bars = stock_data_client.get_stock_bars(
            request
        )

        data = bars.data.get(
            SYMBOL,
            [],
        )

        if len(data) < 50:

            print(
                "⚠️ Not enough SPY historical data."
            )

            return None

        closes = [
            float(bar.close)
            for bar in data
        ]

        volumes = [
            float(bar.volume)
            for bar in data
        ]

        current_price = closes[-1]

        sma20 = calculate_sma(
            closes,
            20,
        )

        sma50 = calculate_sma(
            closes,
            50,
        )

        rsi = calculate_rsi(
            closes,
        )

        macd, signal = calculate_macd(
            closes,
        )

        recent_volumes = volumes[-20:]

        average_volume = (
            sum(recent_volumes)
            / len(recent_volumes)
        )

        current_volume = volumes[-1]

        volume_confirmed = (
            current_volume >= average_volume
        )

        return {
            "price": current_price,
            "sma20": sma20,
            "sma50": sma50,
            "rsi": rsi,
            "macd": macd,
            "signal": signal,
            "volume": current_volume,
            "average_volume": average_volume,
            "volume_confirmed": volume_confirmed,
        }

    except Exception as exc:

        print(
            f"❌ SPY market data error: {exc}"
        )

        return None


# ============================================================
# AI SIGNAL
# ============================================================

def generate_signal(data):

    conditions = []

    # --------------------------------------------------------
    # PRICE > SMA20
    # --------------------------------------------------------

    price_above_sma20 = (
        data["price"]
        > data["sma20"]
    )

    conditions.append(
        price_above_sma20
    )

    # --------------------------------------------------------
    # SMA20 > SMA50
    # --------------------------------------------------------

    bullish_trend = (
        data["sma20"]
        > data["sma50"]
    )

    conditions.append(
        bullish_trend
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi_supportive = (
        data["rsi"] is not None
        and 45 <= data["rsi"] <= 70
    )

    conditions.append(
        rsi_supportive
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    macd_bullish = (
        data["macd"] is not None
        and data["macd"] > 0
    )

    conditions.append(
        macd_bullish
    )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    conditions.append(
        data["volume_confirmed"]
    )

    passed = sum(
        1
        for condition in conditions
        if condition
    )

    confidence = (
        passed
        / len(conditions)
    ) * 100

    signal = (
        "BUY"
        if confidence >= CONFIDENCE_THRESHOLD
        else "NO TRADE"
    )

    return {
        "signal": signal,
        "confidence": confidence,
        "passed": passed,
        "total": len(conditions),
    }


# ============================================================
# DISPLAY AI DECISION
# ============================================================

def print_ai_decision(
    data,
    decision,
):

    print()
    print("🧠 LIVE AI DECISION")
    print("-" * 70)

    print(
        f"SPY Price:       "
        f"${data['price']:.2f}"
    )

    print(
        f"SMA20:           "
        f"${data['sma20']:.2f}"
    )

    print(
        f"SMA50:           "
        f"${data['sma50']:.2f}"
    )

    print(
        f"RSI:             "
        f"{data['rsi']:.2f}"
    )

    print(
        f"MACD:            "
        f"{data['macd']:.4f}"
    )

    print(
        f"Volume:          "
        f"{'CONFIRMED' if data['volume_confirmed'] else 'WEAK'}"
    )

    print()

    print(
        f"Conditions: "
        f"{decision['passed']}/"
        f"{decision['total']}"
    )

    print(
        f"Confidence: "
        f"{decision['confidence']:.0f}%"
    )

    print(
        f"AI Signal: "
        f"{decision['signal']}"
    )

    print("-" * 70)


# ============================================================
# POSITION PROTECTION
# ============================================================

def has_open_option_position():

    try:

        positions = (
            trading_client
            .get_all_positions()
        )

        for position in positions:

            symbol = str(
                position.symbol
            )

            if symbol.startswith("SPY"):

                print(
                    f"⚠️ Existing SPY position: "
                    f"{symbol}"
                )

                return True

        return False

    except Exception as exc:

        print(
            f"⚠️ Option position check error: "
            f"{exc}"
        )

        # Fail safe:
        # if we cannot verify positions,
        # do not enter.
        return True


# ============================================================
# TRADE STATE PROTECTION
# ============================================================

def has_saved_trade_state():

    try:

        if is_open():

            print()
            print(
                "🛑 ENTRY BLOCKED"
            )

            print(
                "An AlphaPilot trade state "
                "is already OPEN."
            )

            print(
                "Waiting for Exit Worker "
                "to complete the lifecycle."
            )

            return True

        return False

    except Exception as exc:

        print(
            f"⚠️ Trade state check error: "
            f"{exc}"
        )

        # Fail safe.
        return True


# ============================================================
# ACCOUNT
# ============================================================

def get_account():

    try:

        return (
            trading_client
            .get_account()
        )

    except Exception as exc:

        print(
            f"❌ Account error: "
            f"{exc}"
        )

        return None


# ============================================================
# RISK MANAGER
# ============================================================

def risk_check(
    account,
    option_price,
    quantity,
):

    if account is None:
        return False

    try:

        equity = float(
            account.equity
        )

        buying_power = float(
            account.buying_power
        )

    except Exception as exc:

        print(
            f"❌ Account value error: "
            f"{exc}"
        )

        return False

    if equity <= 0:

        print(
            "❌ Invalid account equity."
        )

        return False

    if option_price <= 0:

        print(
            "❌ Invalid option price."
        )

        return False

    if quantity <= 0:

        print(
            "❌ Invalid quantity."
        )

        return False

    # --------------------------------------------------------
    # PREMIUM EXPOSURE
    # --------------------------------------------------------

    contract_cost = (
        option_price
        * quantity
        * OPTIONS_MULTIPLIER
    )

    max_exposure = (
        equity
        * MAX_ACCOUNT_EXPOSURE_PCT
    )

    # --------------------------------------------------------
    # STOP-LOSS RISK
    #
    # Current strategy:
    # 25% stop loss.
    #
    # Example:
    # $2.00 option
    # $200 premium
    # 25% stop
    # Approx risk = $50
    # --------------------------------------------------------

    STOP_LOSS_PCT = 0.25

    estimated_stop_loss_risk = (
        contract_cost
        * STOP_LOSS_PCT
    )

    max_risk = (
        equity
        * MAX_ACCOUNT_RISK_PCT
    )

    print()
    print("🛡️ RISK CHECK")
    print("-" * 70)

    print(
        f"Account Equity: "
        f"${equity:,.2f}"
    )

    print(
        f"Buying Power: "
        f"${buying_power:,.2f}"
    )

    print(
        f"Option Mid Price: "
        f"${option_price:.2f}"
    )

    print(
        f"Contracts: "
        f"{quantity}"
    )

    print(
        f"Estimated Cost: "
        f"${contract_cost:,.2f}"
    )

    print(
        f"Estimated 25% SL Risk: "
        f"${estimated_stop_loss_risk:,.2f}"
    )

    print(
        f"Maximum Risk Budget: "
        f"${max_risk:,.2f}"
    )

    print(
        f"Maximum Exposure: "
        f"${max_exposure:,.2f}"
    )

    # --------------------------------------------------------
    # RISK LIMIT
    # --------------------------------------------------------

    if estimated_stop_loss_risk > max_risk:

        print()
        print(
            "❌ Risk rejected:"
        )

        print(
            "Estimated stop-loss risk "
            "exceeds the 1% account risk budget."
        )

        return False

    # --------------------------------------------------------
    # EXPOSURE LIMIT
    # --------------------------------------------------------

    if contract_cost > max_exposure:

        print()
        print(
            "❌ Risk rejected:"
        )

        print(
            "Option exposure exceeds "
            "the 5% account exposure limit."
        )

        return False

    # --------------------------------------------------------
    # BUYING POWER
    # --------------------------------------------------------

    if contract_cost > buying_power:

        print()
        print(
            "❌ Risk rejected:"
        )

        print(
            "Insufficient buying power."
        )

        return False

    print()
    print(
        "✅ Risk check passed."
    )

    print(
        "Risk budget: APPROVED"
    )

    print(
        "Exposure: APPROVED"
    )

    print(
        "Buying power: APPROVED"
    )

    print("-" * 70)

    return True


# ============================================================
# OPTION SCANNER
# ============================================================

def scan_call_options(
    underlying_price,
):

    try:

        today = date.today()

        min_expiration = (
            today
            + timedelta(
                days=MIN_DTE
            )
        )

        max_expiration = (
            today
            + timedelta(
                days=MAX_DTE
            )
        )

        request = GetOptionContractsRequest(
            underlying_symbols=[SYMBOL],
            type="call",
            expiration_date_gte=min_expiration,
            expiration_date_lte=max_expiration,
            strike_price_gte=(
                underlying_price
                - MAX_STRIKE_DISTANCE
            ),
            strike_price_lte=(
                underlying_price
                + MAX_STRIKE_DISTANCE
            ),
            limit=1000,
        )

        response = (
            trading_client
            .get_option_contracts(
                request
            )
        )

        contracts = (
            response.option_contracts
        )

        candidates = []

        for contract in contracts:

            if not contract.tradable:
                continue

            strike = float(
                contract.strike_price
            )

            distance = abs(
                strike
                - underlying_price
            )

            if (
                distance
                > MAX_STRIKE_DISTANCE
            ):
                continue

            open_interest = (
                int(contract.open_interest)
                if contract.open_interest
                else 0
            )

            if (
                open_interest
                < MIN_OPEN_INTEREST
            ):
                continue

            expiration = (
                contract.expiration_date
            )

            dte = (
                expiration
                - today
            ).days

            if (
                dte < MIN_DTE
                or dte > MAX_DTE
            ):
                continue

            candidates.append(
                {
                    "symbol": contract.symbol,
                    "strike": strike,
                    "expiration": expiration,
                    "dte": dte,
                    "open_interest": open_interest,
                    "distance": distance,
                }
            )

        if not candidates:
            return []

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        max_distance = max(
            item["distance"]
            for item in candidates
        )

        max_oi = max(
            item["open_interest"]
            for item in candidates
        )

        for item in candidates:

            distance_score = (
                1
                - (
                    item["distance"]
                    / max_distance
                    if max_distance > 0
                    else 0
                )
            )

            oi_score = (
                item["open_interest"]
                / max_oi
                if max_oi > 0
                else 0
            )

            dte_score = (
                1
                - (
                    abs(
                        item["dte"]
                        - 14
                    )
                    / 16
                )
            )

            item["score"] = (
                distance_score * 45
                + oi_score * 30
                + dte_score * 25
            )

        candidates.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return candidates

    except Exception as exc:

        print(
            f"❌ Option scanner error: "
            f"{exc}"
        )

        return []


# ============================================================
# OPTION QUOTE
# ============================================================

def get_option_price(symbol):

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=[symbol]
        )

        quotes = (
            option_data_client
            .get_option_latest_quote(
                request
            )
        )

        quote = quotes.get(symbol)

        if quote is None:
            return None

        bid = float(
            quote.bid_price or 0
        )

        ask = float(
            quote.ask_price or 0
        )

        # Prefer midpoint.
        if bid > 0 and ask > 0:

            return (
                bid + ask
            ) / 2

        if bid > 0:
            return bid

        if ask > 0:
            return ask

        return None

    except Exception as exc:

        print(
            f"⚠️ Option quote error "
            f"{symbol}: {exc}"
        )

        return None


# ============================================================
# TRADE HISTORY INITIALIZATION
# ============================================================

def ensure_trade_history():

    TRADE_HISTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not TRADE_HISTORY_FILE.exists():

        with open(
            TRADE_HISTORY_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "symbol",
                    "quantity",
                    "entry_price",
                    "exit_price",
                    "entry_value",
                    "exit_value",
                    "pnl",
                    "pnl_percent",
                    "entry_time",
                    "exit_time",
                    "reason",
                ]
            )


# ============================================================
# WAIT FOR BUY FILL
# ============================================================

def wait_for_buy_fill(
    order_id,
    symbol,
):

    print()
    print(
        "⏳ Waiting for REAL PAPER BUY fill..."
    )

    start_time = time.time()

    while (
        time.time() - start_time
        < 60
    ):

        try:

            order = (
                trading_client
                .get_order_by_id(
                    order_id
                )
            )

            status = str(
                order.status
            ).lower()

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"{symbol} BUY status: "
                f"{status.upper()}"
            )

            # ------------------------------------------------
            # REAL FILLED
            # ------------------------------------------------

            if status == "filled":

                filled_price = (
                    float(
                        order.filled_avg_price
                    )
                    if order.filled_avg_price
                    else None
                )

                filled_quantity = (
                    int(
                        float(
                            order.filled_qty
                        )
                    )
                    if order.filled_qty
                    else 0
                )

                return (
                    filled_price,
                    filled_quantity,
                    status,
                )

            # ------------------------------------------------
            # FINAL FAILURE
            # ------------------------------------------------

            if status in {
                "canceled",
                "expired",
                "rejected",
                "suspended",
            }:

                return (
                    None,
                    0,
                    status,
                )

        except Exception as exc:

            print(
                f"⚠️ Fill check error: "
                f"{exc}"
            )

        time.sleep(3)

    return (
        None,
        0,
        "timeout",
    )


# ============================================================
# SUBMIT PAPER BUY
# ============================================================

def submit_paper_buy(
    symbol,
    quantity,
):

    try:

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )

        print()
        print("=" * 70)
        print(
            "🚀 SUBMITTING REAL ALPACA PAPER BUY"
        )
        print("=" * 70)

        print(
            f"Contract: {symbol}"
        )

        print(
            f"Quantity: {quantity}"
        )

        print(
            "Account: ALPACA PAPER"
        )

        print(
            "Order Type: MARKET"
        )

        print("=" * 70)

        order = (
            trading_client
            .submit_order(
                order_data=order_request
            )
        )

        print()
        print(
            "✅ BUY ORDER SUBMITTED"
        )

        print(
            f"Order ID: {order.id}"
        )

        return order

    except Exception as exc:

        print()
        print(
            "❌ PAPER BUY FAILED"
        )

        print(exc)

        return None


# ============================================================
# SAVE REAL ENTRY STATE
# ============================================================

def save_real_entry_state(
    symbol,
    quantity,
    filled_price,
    order_id,
):

    try:

        state = create_open_trade(
            symbol=symbol,
            quantity=quantity,
            entry_price=filled_price,
            entry_order_id=order_id,
        )

        print()
        print("=" * 70)
        print(
            "💾 REAL TRADE STATE SAVED"
        )
        print("=" * 70)

        print(
            f"Symbol:       {state['symbol']}"
        )

        print(
            f"Quantity:     {state['quantity']}"
        )

        print(
            f"Entry Price:  "
            f"${state['entry_price']:.2f}"
        )

        print(
            f"Entry Value:  "
            f"${state['entry_value']:,.2f}"
        )

        print(
            f"Entry Order:  "
            f"{state['entry_order_id']}"
        )

        print(
            f"Entry Time:   "
            f"{state['entry_time']}"
        )

        print(
            f"Status:       "
            f"{state['status']}"
        )

        print("=" * 70)

        return True

    except Exception as exc:

        print()
        print(
            "❌ CRITICAL: Could not save "
            "trade state."
        )

        print(exc)

        return False


# ============================================================
# MAIN ENTRY CHECK
# ============================================================

def run_entry_check():

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    print()
    print("=" * 70)
    print(
        f"[{timestamp}] 🔄 ENTRY CHECK"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # INITIALIZE TRADE HISTORY FILE
    # --------------------------------------------------------

    ensure_trade_history()

    # --------------------------------------------------------
    # TRADE STATE PROTECTION
    # --------------------------------------------------------

    if has_saved_trade_state():

        return

    # --------------------------------------------------------
    # MARKET STATUS
    # --------------------------------------------------------

    try:

        clock = (
            trading_client
            .get_clock()
        )

        if not clock.is_open:

            print(
                "🔴 US MARKET CLOSED"
            )

            print(
                "No BUY order will be submitted."
            )

            return

        print(
            "🟢 US MARKET OPEN"
        )

    except Exception as exc:

        print(
            f"❌ Market status error: "
            f"{exc}"
        )

        return

    # --------------------------------------------------------
    # EXISTING POSITION
    # --------------------------------------------------------

    if has_open_option_position():

        print()
        print(
            "🛑 ENTRY BLOCKED"
        )

        print(
            "An existing SPY option position "
            "is already open."
        )

        print(
            "Duplicate position prevented."
        )

        return

    # --------------------------------------------------------
    # MARKET DATA
    # --------------------------------------------------------

    data = get_spy_data()

    if data is None:
        return

    # --------------------------------------------------------
    # AI SIGNAL
    # --------------------------------------------------------

    decision = generate_signal(
        data
    )

    print_ai_decision(
        data,
        decision,
    )

    # --------------------------------------------------------
    # BUY FILTER
    # --------------------------------------------------------

    if decision["signal"] != "BUY":

        print()
        print(
            "🟡 NO TRADE"
        )

        print(
            "AI confidence is below "
            f"{CONFIDENCE_THRESHOLD}%."
        )

        print(
            "No BUY order submitted."
        )

        return

    print()
    print(
        "🟢 BUY SIGNAL APPROVED"
    )

    # --------------------------------------------------------
    # OPTION SCAN
    # --------------------------------------------------------

    candidates = scan_call_options(
        data["price"]
    )

    if not candidates:

        print(
            "❌ No suitable CALL option found."
        )

        return

    selected = candidates[0]

    print()
    print("⚙️ OPTION SELECTION")
    print("-" * 70)

    print(
        f"Contract:       "
        f"{selected['symbol']}"
    )

    print(
        f"Strike:         "
        f"${selected['strike']:.2f}"
    )

    print(
        f"Expiration:     "
        f"{selected['expiration']}"
    )

    print(
        f"DTE:            "
        f"{selected['dte']}"
    )

    print(
        f"Open Interest:  "
        f"{selected['open_interest']}"
    )

    print(
        f"Distance:       "
        f"${selected['distance']:.2f}"
    )

    print(
        f"Selection Score:"
        f" {selected['score']:.2f}"
    )

    print("-" * 70)

    # --------------------------------------------------------
    # OPTION QUOTE
    # --------------------------------------------------------

    option_price = get_option_price(
        selected["symbol"]
    )

    if option_price is None:

        print(
            "❌ No valid option quote."
        )

        return

    print(
        f"Option Mid Price: "
        f"${option_price:.2f}"
    )

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    quantity = MAX_CONTRACTS

    # --------------------------------------------------------
    # ACCOUNT
    # --------------------------------------------------------

    account = get_account()

    if account is None:
        return

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    if not risk_check(
        account,
        option_price,
        quantity,
    ):

        print()
        print(
            "🛑 ENTRY BLOCKED BY "
            "RISK MANAGER"
        )

        return

    # --------------------------------------------------------
    # FINAL CONFIRMATION
    # --------------------------------------------------------

    estimated_cost = (
        option_price
        * quantity
        * OPTIONS_MULTIPLIER
    )

    print()
    print("=" * 70)
    print(
        "🚀 FINAL PAPER ENTRY APPROVAL"
    )
    print("=" * 70)

    print(
        "Signal:          BUY"
    )

    print(
        f"Confidence:      "
        f"{decision['confidence']:.0f}%"
    )

    print(
        f"Contract:        "
        f"{selected['symbol']}"
    )

    print(
        f"Quantity:        "
        f"{quantity}"
    )

    print(
        f"Estimated Price: "
        f"${option_price:.2f}"
    )

    print(
        f"Estimated Cost:  "
        f"${estimated_cost:,.2f}"
    )

    print()
    print(
        "⚠️ THIS WILL SUBMIT A REAL "
        "ALPACA PAPER ORDER."
    )

    print(
        "No live-money order can be submitted "
        "by this worker."
    )

    print("=" * 70)

    # --------------------------------------------------------
    # SUBMIT
    # --------------------------------------------------------

    order = submit_paper_buy(
        selected["symbol"],
        quantity,
    )

    if order is None:
        return

    # --------------------------------------------------------
    # FILL
    # --------------------------------------------------------

    (
        filled_price,
        filled_quantity,
        status,
    ) = wait_for_buy_fill(
        order.id,
        selected["symbol"],
    )

    # --------------------------------------------------------
    # NOT FILLED
    # --------------------------------------------------------

    if status != "filled":

        print()
        print(
            "⚠️ BUY WAS NOT CONFIRMED FILLED."
        )

        print(
            f"Final status: {status}"
        )

        print(
            "No trade state created."
        )

        print(
            "No trade history entry created."
        )

        return

    # --------------------------------------------------------
    # VALIDATE FILL
    # --------------------------------------------------------

    if not filled_price:

        print()
        print(
            "❌ Filled price unavailable."
        )

        print(
            "Trade state will NOT be created."
        )

        return

    if filled_quantity <= 0:

        print()
        print(
            "❌ Filled quantity unavailable."
        )

        print(
            "Trade state will NOT be created."
        )

        return

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    entry_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    entry_value = (
        filled_price
        * filled_quantity
        * OPTIONS_MULTIPLIER
    )

    print()
    print("=" * 70)
    print(
        "✅ REAL PAPER BUY FILLED"
    )
    print("=" * 70)

    print(
        f"Contract:      "
        f"{selected['symbol']}"
    )

    print(
        f"Quantity:      "
        f"{filled_quantity}"
    )

    print(
        f"Actual Fill:   "
        f"${filled_price:.2f}"
    )

    print(
        f"Position Cost: "
        f"${entry_value:,.2f}"
    )

    print(
        f"Entry Time:    "
        f"{entry_time}"
    )

    print(
        f"Order ID:      "
        f"{order.id}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # SAVE STATE ONLY AFTER REAL FILL
    # --------------------------------------------------------

    state_saved = save_real_entry_state(
        symbol=selected["symbol"],
        quantity=filled_quantity,
        filled_price=filled_price,
        order_id=order.id,
    )

    if not state_saved:

        print()
        print("=" * 70)
        print(
            "🚨 WARNING"
        )
        print("=" * 70)

        print(
            "Alpaca confirmed the BUY as FILLED,"
        )

        print(
            "but AlphaPilot could not save "
            "the local trade state."
        )

        print(
            "DO NOT submit another BUY manually."
        )

        print(
            "The Alpaca position is the "
            "source of truth."
        )

        print("=" * 70)

        return

    # --------------------------------------------------------
    # EXIT HANDOFF
    # --------------------------------------------------------

    print()
    print(
        "👁️ EXIT WORKER HANDOFF READY"
    )

    print(
        "The Exit Worker can now monitor:"
    )

    print(
        f"  Contract: "
        f"{selected['symbol']}"
    )

    print(
        f"  Entry: "
        f"${filled_price:.2f}"
    )

    print(
        "  Stop Loss: 25%"
    )

    print(
        "  Take Profit: 50%"
    )

    print()
    print(
        "🛡️ Trade lifecycle:"
    )

    print(
        "BUY FILLED"
        " → STATE SAVED"
        " → EXIT MONITOR"
        " → SELL FILLED"
        " → REAL P&L"
    )


# ============================================================
# WORKER
# ============================================================

def run_worker():

    print_header()

    while True:

        try:

            run_entry_check()

        except Exception as exc:

            print()
            print(
                f"❌ Entry worker error: "
                f"{exc}"
            )

        print()
        print(
            f"⏳ Next entry check in "
            f"{CHECK_INTERVAL} seconds..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        run_worker()

    except KeyboardInterrupt:

        print()
        print("=" * 70)
        print(
            "🛑 AlphaPilot Entry Worker stopped."
        )
        print("=" * 70)
        print()

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "❌ ENTRY WORKER CRASHED"
        )
        print("=" * 70)

        print(exc)

        print("=" * 70)
        print()
