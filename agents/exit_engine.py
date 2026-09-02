"""
AlphaPilot AI — Autonomous Options Exit Worker

Purpose:
    Monitor open Alpaca PAPER option positions and automatically exit
    when Stop Loss or Take Profit is triggered.

Trade Lifecycle:
    REAL BUY FILLED
        ↓
    trade_state.json
        ↓
    Exit Worker
        ↓
    Stop Loss / Take Profit
        ↓
    REAL SELL
        ↓
    SELL FILLED
        ↓
    Actual Alpaca Fill
        ↓
    Real P&L
        ↓
    trade_history.csv
        ↓
    trade_state.json cleared

IMPORTANT:
    - PAPER TRADING ONLY
    - No fake fills
    - No fake P&L
    - Trade history updated ONLY after Alpaca confirms SELL FILLED
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
    print("❌ ERROR: Alpaca API credentials are missing.")
    print("=" * 70)
    print()

    print("Set these in your AlphaPilot .env file:")
    print()
    print("ALPACA_API_KEY=YOUR_PAPER_API_KEY")
    print("ALPACA_SECRET_KEY=YOUR_PAPER_SECRET_KEY")
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
    print("🚀 AlphaPilot AI — Autonomous Exit Worker")
    print("=" * 70)

    print("Mode: ALPACA PAPER")

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

    print("Real fill confirmation: ENABLED")
    print("Real P&L logging: ENABLED")
    print("Trade State Integration: ENABLED")
    print("Restart Reconciliation: ENABLED")
    print("Fake P&L: DISABLED")

    print("=" * 70)
    print()


# ============================================================
# STATUS NORMALIZATION
# ============================================================

def normalize_order_status(order_status):
    """
    Convert Alpaca enum values such as:

        OrderStatus.FILLED
        OrderStatus.PARTIALLY_FILLED

    into:

        filled
        partially_filled
    """

    raw_status = str(order_status).strip().lower()

    # Handles enum representation:
    # OrderStatus.FILLED
    # ORDERSTATUS.FILLED
    # filled
    status = raw_status.split(".")[-1]

    return status


# ============================================================
# OPTION PRICE
# ============================================================

def get_option_price(symbol):
    """
    Get latest option quote.

    Preferred price:
        midpoint = (bid + ask) / 2

    Fallback:
        bid
        ask
    """

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=[symbol]
        )

        quotes = (
            option_data_client
            .get_option_latest_quote(request)
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

            return (bid + ask) / 2

        if bid > 0:
            return bid

        if ask > 0:
            return ask

        return None

    except Exception as exc:

        print(
            f"⚠️ Quote error for {symbol}: {exc}"
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
            f"❌ Unable to read positions: {exc}"
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

    Returns True if an active SELL order already exists.
    """

    try:

        orders = trading_client.get_orders(
            filter=None
        )

        active_statuses = {
            "new",
            "accepted",
            "pending_new",
            "partially_filled",
            "pending_replace",
            "pending_cancel",
            "calculated",
        }

        for order in orders:

            if order.symbol != symbol:
                continue

            if order.side != OrderSide.SELL:
                continue

            status = normalize_order_status(
                order.status
            )

            if status in active_statuses:

                return True

        return False

    except Exception as exc:

        print(
            f"⚠️ Could not check active SELL orders: {exc}"
        )

        # Fail safe:
        # If we cannot determine whether a SELL
        # already exists, do NOT submit another one.
        return True


# ============================================================
# POSITION ENTRY PRICE
# ============================================================

def get_entry_price(position, state=None):
    """
    Alpaca live position average entry price is
    the primary source of truth.

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
# DUPLICATE COMPLETED TRADE CHECK
# ============================================================

def completed_trade_already_logged(
    symbol,
    quantity,
    entry_price,
    exit_price,
    exit_time,
):
    """
    Prevent duplicate completed-trade rows.

    Uses the actual Alpaca fill timestamp when available.

    This is intentionally separate from active state protection.
    """

    ensure_trade_history_file()

    if not TRADE_HISTORY_FILE.exists():
        return False

    target_symbol = str(symbol)
    target_quantity = round(float(quantity), 4)
    target_entry = round(float(entry_price), 4)
    target_exit = round(float(exit_price), 4)

    target_exit_time = ""

    if exit_time:

        target_exit_time = str(exit_time)

        if "T" in target_exit_time:

            target_exit_time = (
                target_exit_time
                .replace("T", " ")
            )

        # Remove timezone suffix for comparison
        if "+" in target_exit_time:

            target_exit_time = (
                target_exit_time
                .split("+")[0]
            )

    try:

        with open(
            TRADE_HISTORY_FILE,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                try:

                    row_symbol = str(
                        row.get("symbol", "")
                    )

                    row_quantity = round(
                        float(
                            row.get(
                                "quantity",
                                0,
                            )
                        ),
                        4,
                    )

                    row_entry = round(
                        float(
                            row.get(
                                "entry_price",
                                0,
                            )
                        ),
                        4,
                    )

                    row_exit = round(
                        float(
                            row.get(
                                "exit_price",
                                0,
                            )
                        ),
                        4,
                    )

                    row_exit_time = str(
                        row.get(
                            "exit_time",
                            "",
                        )
                    )

                    if (
                        row_symbol == target_symbol
                        and row_quantity == target_quantity
                        and row_entry == target_entry
                        and row_exit == target_exit
                    ):

                        # If both timestamps are available,
                        # require matching timestamp.
                        if (
                            target_exit_time
                            and row_exit_time
                        ):

                            if (
                                row_exit_time
                                == target_exit_time
                            ):

                                return True

                        else:

                            return True

                except Exception:
                    continue

        return False

    except Exception as exc:

        print(
            f"⚠️ Could not inspect trade history: {exc}"
        )

        return False


# ============================================================
# WAIT FOR SELL FILL
# ============================================================

def wait_for_fill(
    order_id,
    symbol,
):
    """
    Wait for REAL Alpaca SELL fill.

    Important:
        Alpaca SDK can return:
            OrderStatus.FILLED

        instead of:
            filled

    normalize_order_status() handles both.

    After timeout, a final Alpaca reconciliation is performed.
    """

    print()
    print("⏳ Waiting for REAL SELL fill...")
    print(f"Order ID: {order_id}")
    print(f"Contract: {symbol}")

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

            status = normalize_order_status(
                order.status
            )

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

                filled_at = (
                    str(order.filled_at)
                    if order.filled_at
                    else ""
                )

                print()
                print(
                    "✅ ALPACA CONFIRMED SELL FILLED"
                )

                print(
                    f"Actual Fill Price: "
                    f"${filled_price:.4f}"
                    if filled_price
                    else
                    "Actual Fill Price: UNAVAILABLE"
                )

                print(
                    f"Filled Quantity: "
                    f"{filled_quantity}"
                )

                print(
                    f"Filled At: "
                    f"{filled_at or 'UNKNOWN'}"
                )

                return (
                    filled_price,
                    filled_quantity,
                    filled_at,
                    "filled",
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

                print()
                print(
                    f"❌ SELL ORDER FINAL STATUS: "
                    f"{status.upper()}"
                )

                return (
                    None,
                    0,
                    "",
                    status,
                )

        except Exception as exc:

            print(
                f"⚠️ Order status error: {exc}"
            )

        time.sleep(3)

    # ========================================================
    # FINAL RECONCILIATION
    # ========================================================

    print()
    print(
        "⏰ SELL confirmation timeout reached."
    )

    print(
        "🔎 Performing final Alpaca order reconciliation..."
    )

    try:

        final_order = (
            trading_client
            .get_order_by_id(
                order_id
            )
        )

        final_status = normalize_order_status(
            final_order.status
        )

        print(
            f"Final Alpaca status: "
            f"{final_status.upper()}"
        )

        # ----------------------------------------------------
        # ACTUALLY FILLED
        # ----------------------------------------------------

        if final_status == "filled":

            filled_price = (
                float(
                    final_order.filled_avg_price
                )
                if final_order.filled_avg_price
                else None
            )

            filled_quantity = (
                int(
                    float(
                        final_order.filled_qty
                    )
                )
                if final_order.filled_qty
                else 0
            )

            filled_at = (
                str(final_order.filled_at)
                if final_order.filled_at
                else ""
            )

            print()
            print(
                "✅ FINAL RECONCILIATION "
                "CONFIRMED SELL FILLED"
            )

            print(
                f"Actual Fill Price: "
                f"${filled_price:.4f}"
                if filled_price
                else
                "Actual Fill Price: UNAVAILABLE"
            )

            print(
                f"Filled Quantity: "
                f"{filled_quantity}"
            )

            print(
                f"Filled At: "
                f"{filled_at or 'UNKNOWN'}"
            )

            return (
                filled_price,
                filled_quantity,
                filled_at,
                "filled",
            )

        # ----------------------------------------------------
        # STILL NOT FILLED
        # ----------------------------------------------------

        print()
        print(
            "⚠️ SELL WAS NOT CONFIRMED FILLED."
        )

        print(
            "No completed trade will be recorded."
        )

        return (
            None,
            0,
            "",
            final_status,
        )

    except Exception as exc:

        print(
            f"❌ Final order reconciliation failed: {exc}"
        )

        return (
            None,
            0,
            "",
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
    exit_time="",
):
    """
    Write completed trade ONLY after a REAL
    Alpaca SELL FILLED confirmation.
    """

    ensure_trade_history_file()

    quantity = float(quantity)
    entry_price = float(entry_price)
    exit_price = float(exit_price)

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

    if not exit_time:

        exit_time = (
            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    else:

        exit_time = str(exit_time)

        if "T" in exit_time:

            exit_time = (
                exit_time
                .replace("T", " ")
            )

        # Remove timezone suffix.
        if "+" in exit_time:

            exit_time = (
                exit_time
                .split("+")[0]
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
                round(entry_price, 4),
                round(exit_price, 4),
                round(entry_value, 2),
                round(exit_value, 2),
                round(pnl, 2),
                round(pnl_percent, 2),
                entry_time,
                exit_time,
                reason,
            ]
        )

    print()
    print("=" * 70)
    print("✅ REALIZED PAPER TRADE SAVED")
    print("=" * 70)

    print(
        f"Contract:       {symbol}"
    )

    print(
        f"Quantity:       {quantity:g}"
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

    It only registers the currently observed live
    Alpaca position.
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
            "💾 EXISTING ALPACA POSITION REGISTERED"
        )

        print(
            f"Contract: {symbol}"
        )

        print(
            f"Quantity: {quantity}"
        )

        print(
            f"Entry Price: ${entry_price:.2f}"
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
            f"⚠️ Could not bootstrap trade state: {exc}"
        )

        return {}


# ============================================================
# RECONCILE SAVED EXIT ORDER
# ============================================================

def reconcile_exit_order():
    """
    Reconcile an EXIT_PENDING SELL order after:
        - worker restart
        - timeout
        - crash
        - temporary API issue

    Only an actual Alpaca FILLED order can create
    a completed trade record.
    """

    state = load_state()

    if not state:

        return False

    exit_order_id = state.get(
        "exit_order_id"
    )

    if not exit_order_id:

        return False

    status_from_state = str(
        state.get(
            "status",
            ""
        )
    ).upper()

    print()
    print("=" * 70)
    print("🔎 EXIT ORDER RECONCILIATION")
    print("=" * 70)

    print(
        f"Order ID: {exit_order_id}"
    )

    print(
        f"State status: {status_from_state}"
    )

    try:

        order = (
            trading_client
            .get_order_by_id(
                exit_order_id
            )
        )

        status = normalize_order_status(
            order.status
        )

        print(
            f"Alpaca status: {status.upper()}"
        )

        # ----------------------------------------------------
        # REAL FILLED
        # ----------------------------------------------------

        if status == "filled":

            filled_price = (
                float(
                    order.filled_avg_price
                )
                if order.filled_avg_price
                else 0.0
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

            filled_at = (
                str(order.filled_at)
                if order.filled_at
                else ""
            )

            if filled_price <= 0:

                print(
                    "❌ FILLED order has no valid "
                    "average fill price."
                )

                print(
                    "Trade will NOT be recorded."
                )

                return False

            if filled_quantity <= 0:

                print(
                    "❌ FILLED order has invalid quantity."
                )

                print(
                    "Trade will NOT be recorded."
                )

                return False

            symbol = state.get(
                "symbol",
                order.symbol,
            )

            entry_price = float(
                state.get(
                    "entry_price",
                    0,
                )
            )

            entry_time = state.get(
                "entry_time",
                "",
            )

            if entry_price <= 0:

                print(
                    "❌ State has invalid entry price."
                )

                print(
                    "Trade will NOT be recorded."
                )

                return False

            # ------------------------------------------------
            # DUPLICATE PROTECTION
            # ------------------------------------------------

            if completed_trade_already_logged(
                symbol=symbol,
                quantity=filled_quantity,
                entry_price=entry_price,
                exit_price=filled_price,
                exit_time=filled_at,
            ):

                print()
                print(
                    "⚠️ Trade already exists "
                    "in trade_history.csv."
                )

                print(
                    "No duplicate row will be added."
                )

                clear_state()

                print(
                    "🧹 Stale trade state cleared."
                )

                return True

            # ------------------------------------------------
            # REAL P&L
            # ------------------------------------------------

            entry_value = (
                entry_price
                * filled_quantity
                * OPTIONS_MULTIPLIER
            )

            exit_value = (
                filled_price
                * filled_quantity
                * OPTIONS_MULTIPLIER
            )

            pnl = (
                exit_value
                - entry_value
            )

            pnl_percent = (
                (
                    pnl
                    / entry_value
                )
                * 100
                if entry_value
                else 0.0
            )

            print()
            print(
                "✅ REAL SELL FILL CONFIRMED"
            )

            print(
                f"Symbol:        {symbol}"
            )

            print(
                f"Filled Qty:    {filled_quantity}"
            )

            print(
                f"Entry Price:   ${entry_price:.2f}"
            )

            print(
                f"Exit Price:    ${filled_price:.2f}"
            )

            print(
                f"Real P&L:      ${pnl:,.2f}"
            )

            print(
                f"Return:        {pnl_percent:.2f}%"
            )

            print(
                f"Filled At:     {filled_at or 'UNKNOWN'}"
            )

            # ------------------------------------------------
            # SAVE REAL TRADE
            # ------------------------------------------------

            log_completed_trade(
                symbol=symbol,
                quantity=filled_quantity,
                entry_price=entry_price,
                exit_price=filled_price,
                reason="STOP LOSS",
                entry_time=entry_time,
                exit_time=filled_at,
            )

            # ------------------------------------------------
            # CLEAR STATE ONLY AFTER LOGGING
            # ------------------------------------------------

            clear_state()

            print()
            print(
                "🧹 Trade state cleared."
            )

            print(
                "✅ EXIT RECONCILIATION COMPLETE."
            )

            return True

        # ----------------------------------------------------
        # FINAL FAILED ORDER
        # ----------------------------------------------------

        if status in {
            "canceled",
            "expired",
            "rejected",
            "suspended",
        }:

            print()
            print(
                f"⚠️ EXIT ORDER IS {status.upper()}."
            )

            # If position still exists, it can safely
            # return to OPEN and be evaluated again.
            live_position = find_position(
                state.get("symbol", "")
            )

            if live_position:

                mark_exit_open()

                print(
                    "Trade state returned to OPEN."
                )

            else:

                print(
                    "⚠️ No live position exists, "
                    "but SELL was not confirmed filled."
                )

                print(
                    "State will NOT be silently cleared."
                )

            return False

        # ----------------------------------------------------
        # STILL ACTIVE
        # ----------------------------------------------------

        print()
        print(
            "⏳ Exit order is still active."
        )

        print(
            "EXIT_PENDING state will be preserved."
        )

        return False

    except Exception as exc:

        print()
        print(
            f"❌ Exit reconciliation failed: {exc}"
        )

        return False


# ============================================================
# EXIT EXECUTION
# ============================================================

def execute_exit(
    position,
    current_price,
    reason,
):
    """
    Submit REAL Alpaca PAPER SELL order and wait
    for actual fill confirmation.
    """

    symbol = position.symbol

    quantity = get_position_quantity(
        position
    )

    state = load_state()

    entry_price = get_entry_price(
        position,
        state,
    )

    if quantity <= 0:

        print(
            f"❌ Invalid exit quantity for {symbol}"
        )

        return False

    if entry_price <= 0:

        print(
            f"❌ Invalid entry price for {symbol}"
        )

        return False

    print()
    print("=" * 70)
    print("🚀 EXIT EXECUTION")
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

    print(
        "Mode:            ALPACA PAPER"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # EXISTING EXIT PENDING
    # --------------------------------------------------------

    if state:

        state_symbol = state.get(
            "symbol"
        )

        state_status = state.get(
            "status"
        )

        if (
            state_symbol == symbol
            and state_status == "EXIT_PENDING"
        ):

            print()
            print(
                "⏳ EXIT ALREADY PENDING."
            )

            print(
                "Duplicate SELL prevented."
            )

            return False

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

        return False

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

            return False

    except Exception as exc:

        print()
        print(
            f"⚠️ Could not verify market status: {exc}"
        )

        return False

    # --------------------------------------------------------
    # SUBMIT REAL PAPER SELL
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
            "🚀 REAL PAPER SELL ORDER SUBMITTED"
        )

        print(
            f"Order ID: {order.id}"
        )

    except Exception as exc:

        print()
        print(
            "❌ SELL ORDER FAILED"
        )

        print(exc)

        return False

    # --------------------------------------------------------
    # SAVE EXIT PENDING STATE
    # --------------------------------------------------------

    try:

        mark_exit_pending(
            order.id
        )

        print(
            "💾 Exit order state saved."
        )

    except Exception as exc:

        print()
        print(
            f"⚠️ Could not save exit state: {exc}"
        )

        print(
            "⚠️ SAFETY STOP:"
        )

        print(
            "Do NOT submit another SELL manually."
        )

        return False

    # --------------------------------------------------------
    # WAIT FOR REAL FILL
    # --------------------------------------------------------

    (
        filled_price,
        filled_quantity,
        filled_at,
        status,
    ) = wait_for_fill(
        order.id,
        symbol,
    )

    # --------------------------------------------------------
    # SELL NOT CONFIRMED FILLED
    # --------------------------------------------------------

    if status != "filled":

        print()
        print(
            "⚠️ SELL WAS NOT CONFIRMED FILLED."
        )

        print(
            f"Final status: {status}"
        )

        print(
            "No completed trade recorded."
        )

        # ----------------------------------------------------
        # ACTIVE / TIMEOUT
        # ----------------------------------------------------

        if status in {
            "timeout",
            "new",
            "accepted",
            "pending_new",
            "partially_filled",
            "pending_replace",
            "pending_cancel",
            "calculated",
        }:

            print()
            print(
                "⏳ SELL order may still be active."
            )

            print(
                "EXIT_PENDING state preserved."
            )

            print(
                "Duplicate SELL protection remains active."
            )

            return False

        # ----------------------------------------------------
        # FINAL FAILURE
        # ----------------------------------------------------

        if status in {
            "canceled",
            "expired",
            "rejected",
            "suspended",
        }:

            try:

                live_position = find_position(
                    symbol
                )

                if live_position:

                    mark_exit_open()

                    print(
                        "Trade state returned to OPEN."
                    )

                else:

                    print()
                    print(
                        "⚠️ No live position found."
                    )

                    print(
                        "SELL was not confirmed FILLED."
                    )

                    print(
                        "State was NOT silently cleared."
                    )

            except Exception as exc:

                print(
                    f"⚠️ Could not restore state: {exc}"
                )

            return False

        return False

    # --------------------------------------------------------
    # VALIDATE REAL FILL PRICE
    # --------------------------------------------------------

    if filled_price is None:

        print()
        print(
            "❌ Alpaca reported FILLED "
            "but no fill price was returned."
        )

        print(
            "P&L will NOT be calculated."
        )

        return False

    if filled_price <= 0:

        print()
        print(
            "❌ Invalid Alpaca fill price."
        )

        print(
            "P&L will NOT be calculated."
        )

        return False

    # --------------------------------------------------------
    # VALIDATE REAL FILL QUANTITY
    # --------------------------------------------------------

    if filled_quantity <= 0:

        print()
        print(
            "❌ Invalid Alpaca filled quantity."
        )

        print(
            "P&L will NOT be calculated."
        )

        return False

    # --------------------------------------------------------
    # LOAD CURRENT STATE
    # --------------------------------------------------------

    state = load_state()

    entry_time = ""

    if state:

        entry_time = state.get(
            "entry_time",
            "",
        )

    # --------------------------------------------------------
    # DUPLICATE PROTECTION
    # --------------------------------------------------------

    if completed_trade_already_logged(
        symbol=symbol,
        quantity=filled_quantity,
        entry_price=entry_price,
        exit_price=filled_price,
        exit_time=filled_at,
    ):

        print()
        print(
            "⚠️ Completed trade already exists."
        )

        print(
            "No duplicate history row created."
        )

        try:

            clear_state()

            print(
                "🧹 Trade state cleared."
            )

        except Exception as exc:

            print(
                f"⚠️ Could not clear state: {exc}"
            )

        return True

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
        exit_time=filled_at,
    )

    # --------------------------------------------------------
    # CLEAR STATE ONLY AFTER SUCCESSFUL LOGGING
    # --------------------------------------------------------

    try:

        clear_state()

        print()
        print(
            "🧹 Trade state cleared."
        )

        print(
            "✅ Trade lifecycle completed."
        )

    except Exception as exc:

        print()
        print(
            "⚠️ Trade was completed but "
            "state could not be cleared:"
        )

        print(exc)

    return True


# ============================================================
# POSITION MONITOR
# ============================================================

def monitor_position(
    position,
):
    """
    Monitor one open SPY option position.
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

    if not state:

        print(
            f"⚠️ Could not create state for {symbol}"
        )

        return

    # --------------------------------------------------------
    # EXIT PENDING
    # --------------------------------------------------------

    if state.get("status") == "EXIT_PENDING":

        print()
        print(
            f"⏳ {symbol} has an EXIT_PENDING order."
        )

        print(
            "Waiting for Alpaca order completion."
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
            f"⚠️ Invalid quantity: {symbol}"
        )

        return

    if entry_price <= 0:

        print(
            f"⚠️ Invalid entry price: {symbol}"
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
            f"⚠️ No current quote available for {symbol}"
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
            f"🛑 STOP LOSS TRIGGERED: {symbol}"
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
            f"🎯 TAKE PROFIT TRIGGERED: {symbol}"
        )

        execute_exit(
            position=position,
            current_price=current_price,
            reason="TAKE PROFIT",
        )

        return


# ============================================================
# RECONCILE STATE BEFORE POSITION MONITORING
# ============================================================

def reconcile_state_before_monitoring():
    """
    Check whether a saved EXIT_PENDING order was completed
    while the worker was stopped/restarting.

    This is called before reading live positions.
    """

    state = load_state()

    if not state:

        return False

    exit_order_id = state.get(
        "exit_order_id"
    )

    if not exit_order_id:

        return False

    status = state.get(
        "status"
    )

    if status not in {
        "EXIT_PENDING",
        "OPEN",
    }:

        return False

    print()
    print(
        "🔄 Saved exit order detected."
    )

    return reconcile_exit_order()


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
            f"[{timestamp}] 🔄 CHECKING POSITIONS"
        )
        print("=" * 70)

        # ----------------------------------------------------
        # FIRST: RECONCILE SAVED EXIT
        # ----------------------------------------------------

        try:

            reconcile_state_before_monitoring()

        except Exception as exc:

            print()
            print(
                f"⚠️ Startup reconciliation error: {exc}"
            )

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
                f"⚠️ Market status error: {exc}"
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

            # ------------------------------------------------
            # IMPORTANT:
            # If there is no live position but a saved
            # exit order exists, attempt reconciliation.
            # ------------------------------------------------

            state = load_state()

            if state:

                if state.get(
                    "exit_order_id"
                ):

                    print()
                    print(
                        "🔎 No live position, "
                        "but saved exit order exists."
                    )

                    reconcile_exit_order()

                else:

                    if state.get(
                        "status"
                    ) == "OPEN":

                        print()
                        print(
                            "⚠️ Local state says OPEN "
                            "but Alpaca has no open position."
                        )

                        print(
                            "No automatic state deletion performed."
                        )

        else:

            print()
            print(
                f"📊 Open positions: {len(positions)}"
            )

            for position in positions:

                try:

                    # Only manage SPY options
                    # for this strategy.
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
                        f"{position.symbol}: {exc}"
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