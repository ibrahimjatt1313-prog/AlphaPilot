"""
AlphaPilot AI — Autonomous Options Exit Worker

Purpose:
    Monitor open Alpaca PAPER option positions and automatically exit
    when Stop Loss or Take Profit is triggered.

Trade Lifecycle:
    Real BUY FILLED
        ↓
    trade_state.json
        ↓
    Exit Worker
        ↓
    Stop Loss / Take Profit
        ↓
    Real SELL
        ↓
    SELL FILLED
        ↓
    Actual P&L
        ↓
    trade_history.csv
        ↓
    trade_state.json cleared

IMPORTANT:
    - PAPER TRADING ONLY
    - No fake fills
    - No fake P&L
    - Trade history is updated ONLY after Alpaca confirms SELL FILLED
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from agents.trade_state import (
    load_state,
    save_state,
    clear_state,
    mark_exit_pending,
    mark_exit_open,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TRADE_HISTORY_FILE = (
    BASE_DIR / "agents" / "trade_history.csv"
)

CHECK_INTERVAL = 30

STOP_LOSS_PCT = 0.25
TAKE_PROFIT_PCT = 0.50

OPTIONS_MULTIPLIER = 100

ORDER_FILL_TIMEOUT = 60

PAPER_TRADING = True


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

try:

    from dotenv import load_dotenv

    load_dotenv(
        BASE_DIR / ".env"
    )

except Exception:
    pass


# ============================================================
# CREDENTIALS
# ============================================================

API_KEY = os.getenv(
    "ALPACA_API_KEY"
)

SECRET_KEY = os.getenv(
    "ALPACA_SECRET_KEY"
)


if not API_KEY or not SECRET_KEY:

    print()
    print("=" * 70)
    print(
        "❌ ERROR: Alpaca API credentials are missing."
    )
    print("=" * 70)
    print()

    print(
        "Set these in your AlphaPilot .env file:"
    )

    print()
    print(
        "ALPACA_API_KEY=YOUR_PAPER_API_KEY"
    )

    print(
        "ALPACA_SECRET_KEY=YOUR_PAPER_SECRET_KEY"
    )

    print()

    raise SystemExit(1)


# ============================================================
# ALPACA CLIENTS
# ============================================================

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=PAPER_TRADING,
)

option_data_client = OptionHistoricalDataClient(
    API_KEY,
    SECRET_KEY,
)


# ============================================================
# DISPLAY HEADER
# ============================================================

def print_header():

    print()
    print("=" * 70)
    print(
        "🚀 AlphaPilot AI — Autonomous Exit Worker"
    )
    print("=" * 70)

    print(
        "Mode: ALPACA PAPER"
    )

    print(
        f"Check interval: "
        f"{CHECK_INTERVAL} seconds"
    )

    print(
        f"Stop Loss: "
        f"{STOP_LOSS_PCT * 100:.0f}%"
    )

    print(
        f"Take Profit: "
        f"{TAKE_PROFIT_PCT * 100:.0f}%"
    )

    print(
        "Real fill confirmation: ENABLED"
    )

    print(
        "Real P&L logging: ENABLED"
    )

    print(
        "Trade State Integration: ENABLED"
    )

    print(
        "Fake P&L: DISABLED"
    )

    print("=" * 70)
    print()


# ============================================================
# OPTION PRICE
# ============================================================

def get_option_price(symbol):
    """
    Get latest option quote.

    Uses:
        midpoint = (bid + ask) / 2

    Falls back to bid or ask if only one side
    is available.
    """

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
            f"⚠️ Quote error for "
            f"{symbol}: {exc}"
        )

        return None


# ============================================================
# OPEN POSITIONS
# ============================================================

def get_open_positions():

    try:

        return (
            trading_client
            .get_all_positions()
        )

    except Exception as exc:

        print(
            f"❌ Unable to read positions: "
            f"{exc}"
        )

        return []


# ============================================================
# FIND SPECIFIC POSITION
# ============================================================

def find_position(symbol):

    positions = get_open_positions()

    for position in positions:

        if position.symbol == symbol:

            return position

    return None


# ============================================================
# ACTIVE SELL ORDER PROTECTION
# ============================================================

def has_active_sell_order(symbol):
    """
    Prevent duplicate SELL orders.
    """

    try:

        orders = trading_client.get_orders(
            filter=None
        )

        for order in orders:

            if order.symbol != symbol:
                continue

            if order.side != OrderSide.SELL:
                continue

            status = str(
                order.status
            ).lower()

            if status in {
                "new",
                "accepted",
                "pending_new",
                "partially_filled",
                "pending_replace",
            }:

                return True

        return False

    except Exception as exc:

        print(
            f"⚠️ Could not check active "
            f"SELL orders: {exc}"
        )

        # Fail safe.
        return True


# ============================================================
# POSITION ENTRY PRICE
# ============================================================

def get_entry_price(position, state=None):
    """
    Alpaca live position avg_entry_price is the
    primary source of truth.

    trade_state.json is used as fallback.
    """

    try:

        price = float(
            position.avg_entry_price
        )

        if price > 0:
            return price

    except Exception:
        pass

    if state:

        try:

            price = float(
                state.get(
                    "entry_price",
                    0,
                )
            )

            if price > 0:
                return price

        except Exception:
            pass

    return 0.0


# ============================================================
# POSITION QUANTITY
# ============================================================

def get_position_quantity(position):

    try:

        return abs(
            int(
                float(
                    position.qty
                )
            )
        )

    except Exception:

        return 0


# ============================================================
# TRADE HISTORY FILE
# ============================================================

def ensure_trade_history_file():

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
# DUPLICATE TRADE PROTECTION
# ============================================================

def trade_already_logged(
    symbol,
    entry_order_id=None,
):
    """
    Protect against duplicate completed-trade
    records.

    IMPORTANT:
    A previous trade with the same symbol should
    NOT permanently block a future trade.

    Therefore this checks the active trade state's
    entry order when available.
    """

    state = load_state()

    if not state:
        return False

    if state.get("symbol") != symbol:
        return False

    if entry_order_id:

        if (
            str(
                state.get(
                    "entry_order_id",
                    "",
                )
            )
            != str(entry_order_id)
        ):
            return False

    return (
        state.get("status")
        == "EXIT_PENDING"
    )


# ============================================================
# WAIT FOR SELL FILL
# ============================================================

def wait_for_fill(
    order_id,
    symbol,
):

    print()
    print(
        "⏳ Waiting for REAL SELL fill..."
    )

    print(
        f"Order ID: {order_id}"
    )

    print(
        f"Contract: {symbol}"
    )

    start_time = time.time()

    while (
        time.time() - start_time
        < ORDER_FILL_TIMEOUT
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
                f"SELL status: "
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
            # FAILED
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
                f"⚠️ Order status error: "
                f"{exc}"
            )

        time.sleep(3)

    print()
    print(
        "⏰ SELL fill confirmation timeout."
    )

    print(
        "No completed trade will be recorded."
    )

    return (
        None,
        0,
        "timeout",
    )


# ============================================================
# LOG COMPLETED TRADE
# ============================================================

def log_completed_trade(
    symbol,
    quantity,
    entry_price,
    exit_price,
    reason,
    entry_time="",
):
    """
    Write completed trade ONLY after a REAL
    Alpaca SELL FILLED confirmation.
    """

    ensure_trade_history_file()

    entry_value = (
        entry_price
        * quantity
        * OPTIONS_MULTIPLIER
    )

    exit_value = (
        exit_price
        * quantity
        * OPTIONS_MULTIPLIER
    )

    pnl = (
        exit_value
        - entry_value
    )

    if entry_value != 0:

        pnl_percent = (
            pnl
            / entry_value
        ) * 100

    else:

        pnl_percent = 0.0

    exit_time = (
        datetime.now()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    with open(
        TRADE_HISTORY_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                symbol,
                quantity,
                round(
                    entry_price,
                    4,
                ),
                round(
                    exit_price,
                    4,
                ),
                round(
                    entry_value,
                    2,
                ),
                round(
                    exit_value,
                    2,
                ),
                round(
                    pnl,
                    2,
                ),
                round(
                    pnl_percent,
                    2,
                ),
                entry_time,
                exit_time,
                reason,
            ]
        )

    print()
    print("=" * 70)
    print(
        "✅ REALIZED PAPER TRADE SAVED"
    )
    print("=" * 70)

    print(
        f"Contract:       {symbol}"
    )

    print(
        f"Quantity:       {quantity}"
    )

    print(
        f"Entry Price:    ${entry_price:.2f}"
    )

    print(
        f"Actual Exit:    ${exit_price:.2f}"
    )

    print(
        f"Entry Value:    ${entry_value:,.2f}"
    )

    print(
        f"Exit Value:     ${exit_value:,.2f}"
    )

    print(
        f"Realized P&L:   ${pnl:,.2f}"
    )

    print(
        f"Return:         {pnl_percent:.2f}%"
    )

    print(
        f"Exit Reason:    {reason}"
    )

    print(
        f"Entry Time:     {entry_time or 'UNKNOWN'}"
    )

    print(
        f"Exit Time:      {exit_time}"
    )

    print("=" * 70)
    print()


# ============================================================
# BOOTSTRAP EXISTING POSITION
# ============================================================

def bootstrap_state_from_position(
    position,
):
    """
    If an existing Alpaca position was opened before
    trade_state integration, create a state from the
    live position.

    This does NOT create a fake trade.

    It only records the currently observed live
    Alpaca position so the Exit Worker can manage it.
    """

    state = load_state()

    if state:

        return state

    symbol = position.symbol

    quantity = get_position_quantity(
        position
    )

    entry_price = get_entry_price(
        position
    )

    if quantity <= 0:
        return {}

    if entry_price <= 0:
        return {}

    try:

        state = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": entry_price,
            "entry_value": (
                entry_price
                * quantity
                * OPTIONS_MULTIPLIER
            ),
            "entry_time": "",
            "entry_order_id": "",
            "exit_order_id": None,
            "status": "OPEN",
            "bootstrapped": True,
        }

        save_state(state)

        print()
        print(
            "💾 EXISTING ALPACA POSITION "
            "REGISTERED"
        )

        print(
            f"Contract: "
            f"{symbol}"
        )

        print(
            f"Quantity: "
            f"{quantity}"
        )

        print(
            f"Entry Price: "
            f"${entry_price:.2f}"
        )

        print(
            "Source: LIVE ALPACA POSITION"
        )

        print(
            "No fake trade created."
        )

        print()

        return state

    except Exception as exc:

        print(
            f"⚠️ Could not bootstrap "
            f"trade state: {exc}"
        )

        return {}


# ============================================================
# EXIT EXECUTION
# ============================================================

def execute_exit(
    position,
    current_price,
    reason,
):
    """
    Submit REAL PAPER SELL.

    Completed trade is recorded ONLY after
    Alpaca confirms SELL = FILLED.
    """

    symbol = position.symbol

    state = load_state()

    if (
        not state
        or state.get("symbol") != symbol
    ):

        state = (
            bootstrap_state_from_position(
                position
            )
        )

    quantity = get_position_quantity(
        position
    )

    entry_price = get_entry_price(
        position,
        state,
    )

    if quantity <= 0:

        print(
            f"⚠️ Invalid quantity "
            f"for {symbol}"
        )

        return

    if entry_price <= 0:

        print(
            f"⚠️ Invalid entry price "
            f"for {symbol}"
        )

        return

    print()
    print("=" * 70)
    print(
        "🚨 EXIT EXECUTION"
    )
    print("=" * 70)

    print(
        f"Contract:       {symbol}"
    )

    print(
        f"Quantity:       {quantity}"
    )

    print(
        f"Entry:          ${entry_price:.2f}"
    )

    print(
        f"Current Quote:  ${current_price:.2f}"
    )

    print(
        f"Reason:         {reason}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # ACTIVE SELL PROTECTION
    # --------------------------------------------------------

    if has_active_sell_order(symbol):

        print()
        print(
            "⚠️ Active SELL order already exists."
        )

        print(
            "Duplicate SELL prevented."
        )

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

            print()
            print(
                "⏰ MARKET CLOSED"
            )

            print(
                "SELL order NOT submitted."
            )

            print(
                "Exit condition remains active."
            )

            print(
                "Worker will retry automatically."
            )

            return

    except Exception as exc:

        print()
        print(
            f"⚠️ Could not verify market "
            f"status: {exc}"
        )

        return

    # --------------------------------------------------------
    # SUBMIT SELL
    # --------------------------------------------------------

    try:

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )

        order = (
            trading_client
            .submit_order(
                order_data=order_request
            )
        )

        print()
        print(
            "🚀 REAL PAPER SELL "
            "ORDER SUBMITTED"
        )

        print(
            f"Order ID: {order.id}"
        )

        # ----------------------------------------------------
        # SAVE EXIT PENDING STATE
        # ----------------------------------------------------

        try:

            mark_exit_pending(
                order.id
            )

            print(
                "💾 Exit order state saved."
            )

        except Exception as exc:

            print(
                f"⚠️ Could not save exit "
                f"state: {exc}"
            )

    except Exception as exc:

        print()
        print(
            "❌ SELL ORDER FAILED"
        )

        print(exc)

        return

    # --------------------------------------------------------
    # WAIT FOR REAL FILL
    # --------------------------------------------------------

    (
        filled_price,
        filled_quantity,
        status,
    ) = wait_for_fill(
        order.id,
        symbol,
    )

    # --------------------------------------------------------
    # SELL NOT FILLED
    # --------------------------------------------------------

    if status != "filled":

        print()
        print(
            "⚠️ SELL WAS NOT CONFIRMED FILLED"
        )

        print(
            f"Final status: {status}"
        )

        print(
            "No completed trade recorded."
        )

        # If order failed/canceled, return state
        # to OPEN so another exit can be attempted.
        if status in {
            "canceled",
            "expired",
            "rejected",
            "suspended",
            "timeout",
        }:

            try:

                mark_exit_open()

                print(
                    "Trade state returned to OPEN."
                )

            except Exception as exc:

                print(
                    f"⚠️ Could not restore "
                    f"trade state: {exc}"
                )

        return

    # --------------------------------------------------------
    # VALIDATE REAL FILL
    # --------------------------------------------------------

    if not filled_price:

        print()
        print(
            "❌ Alpaca reported FILLED "
            "but no filled average price "
            "was returned."
        )

        print(
            "P&L will NOT be calculated."
        )

        return

    if filled_quantity <= 0:

        print()
        print(
            "❌ Alpaca reported FILLED "
            "but quantity is invalid."
        )

        print(
            "P&L will NOT be calculated."
        )

        return

    # --------------------------------------------------------
    # GET ENTRY TIME FROM STATE
    # --------------------------------------------------------

    state = load_state()

    entry_time = ""

    if state:

        entry_time = state.get(
            "entry_time",
            "",
        )

    # --------------------------------------------------------
    # SAVE REAL COMPLETED TRADE
    # --------------------------------------------------------

    log_completed_trade(
        symbol=symbol,
        quantity=filled_quantity,
        entry_price=entry_price,
        exit_price=filled_price,
        reason=reason,
        entry_time=entry_time,
    )

    # --------------------------------------------------------
    # CLEAR STATE ONLY AFTER SUCCESSFUL
    # TRADE LOGGING
    # --------------------------------------------------------

    try:

        clear_state()

        print(
            "🧹 Trade state cleared."
        )

        print(
            "✅ Trade lifecycle completed."
        )

    except Exception as exc:

        print(
            f"⚠️ Trade was completed but "
            f"state could not be cleared: "
            f"{exc}"
        )


# ============================================================
# POSITION MONITOR
# ============================================================

def monitor_position(
    position,
):
    """
    Monitor one open option position.
    """

    symbol = position.symbol

    quantity = get_position_quantity(
        position
    )

    state = load_state()

    # --------------------------------------------------------
    # MAKE SURE STATE EXISTS
    # --------------------------------------------------------

    if (
        not state
        or state.get("symbol") != symbol
    ):

        state = (
            bootstrap_state_from_position(
                position
            )
        )

    # --------------------------------------------------------
    # EXIT PENDING
    # --------------------------------------------------------

    if state.get("status") == "EXIT_PENDING":

        print(
            f"⏳ {symbol} has an "
            f"EXIT_PENDING order."
        )

        print(
            "Waiting for Alpaca order "
            "completion."
        )

        return

    # --------------------------------------------------------
    # ENTRY PRICE
    # --------------------------------------------------------

    entry_price = get_entry_price(
        position,
        state,
    )

    if quantity <= 0:

        print(
            f"⚠️ Invalid quantity: "
            f"{symbol}"
        )

        return

    if entry_price <= 0:

        print(
            f"⚠️ Invalid entry price: "
            f"{symbol}"
        )

        return

    # --------------------------------------------------------
    # CURRENT PRICE
    # --------------------------------------------------------

    current_price = get_option_price(
        symbol
    )

    if current_price is None:

        print(
            f"⚠️ No current quote "
            f"available for {symbol}"
        )

        return

    # --------------------------------------------------------
    # STOP / TARGET
    # --------------------------------------------------------

    stop_loss = (
        entry_price
        * (1 - STOP_LOSS_PCT)
    )

    take_profit = (
        entry_price
        * (1 + TAKE_PROFIT_PCT)
    )

    current_return = (
        (
            current_price
            - entry_price
        )
        / entry_price
    ) * 100

    print(
        f"{symbol} | "
        f"Qty {quantity} | "
        f"Entry ${entry_price:.2f} | "
        f"Current ${current_price:.2f} | "
        f"SL ${stop_loss:.2f} | "
        f"TP ${take_profit:.2f} | "
        f"Return {current_return:.2f}%"
    )

    # --------------------------------------------------------
    # STOP LOSS
    # --------------------------------------------------------

    if current_price <= stop_loss:

        print()
        print(
            f"🛑 STOP LOSS TRIGGERED: "
            f"{symbol}"
        )

        execute_exit(
            position=position,
            current_price=current_price,
            reason="STOP LOSS",
        )

        return

    # --------------------------------------------------------
    # TAKE PROFIT
    # --------------------------------------------------------

    if current_price >= take_profit:

        print()
        print(
            f"🎯 TAKE PROFIT TRIGGERED: "
            f"{symbol}"
        )

        execute_exit(
            position=position,
            current_price=current_price,
            reason="TAKE PROFIT",
        )

        return


# ============================================================
# MAIN WORKER
# ============================================================

def run_worker():

    print_header()

    while True:

        timestamp = (
            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        print()
        print("=" * 70)
        print(
            f"[{timestamp}] 🔄 "
            f"CHECKING POSITIONS"
        )
        print("=" * 70)

        # ----------------------------------------------------
        # MARKET STATUS
        # ----------------------------------------------------

        try:

            clock = (
                trading_client
                .get_clock()
            )

            if clock.is_open:

                print(
                    "🟢 US MARKET OPEN"
                )

            else:

                print(
                    "🔴 US MARKET CLOSED"
                )

        except Exception as exc:

            print(
                f"⚠️ Market status error: "
                f"{exc}"
            )

        # ----------------------------------------------------
        # POSITIONS
        # ----------------------------------------------------

        positions = get_open_positions()

        if not positions:

            print()
            print(
                "📭 No open positions."
            )

        else:

            print()
            print(
                f"📊 Open positions: "
                f"{len(positions)}"
            )

            for position in positions:

                try:

                    # Only manage SPY options
                    # for this AlphaPilot strategy.
                    if not position.symbol.startswith(
                        "SPY"
                    ):

                        continue

                    monitor_position(
                        position
                    )

                except Exception as exc:

                    print(
                        f"❌ Position error "
                        f"{position.symbol}: "
                        f"{exc}"
                    )

        print()
        print(
            f"⏳ Next check in "
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
            "🛑 AlphaPilot Exit Worker "
            "stopped by user."
        )
        print("=" * 70)
        print()

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "❌ EXIT WORKER CRASHED"
        )
        print("=" * 70)

        print(exc)

        print("=" * 70)
        print()
