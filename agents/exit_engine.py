
"""
AlphaPilot AI — Autonomous Options Exit Worker

Purpose:
    Monitor open Alpaca PAPER option positions and automatically exit
    when Stop Loss or Take Profit is triggered.

Important:
    - PAPER TRADING ONLY
    - No fake fills
    - Trade history is updated only after Alpaca confirms FILLED
    - Uses the actual filled average SELL price for realized P&L
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


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TRADE_HISTORY_FILE = BASE_DIR / "agents" / "trade_history.csv"

CHECK_INTERVAL = 30

STOP_LOSS_PCT = 0.25
TAKE_PROFIT_PCT = 0.50

OPTIONS_MULTIPLIER = 100

ORDER_FILL_TIMEOUT = 60

# Only PAPER trading is allowed by this worker.
PAPER_TRADING = True


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")

except Exception:
    pass


API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


if not API_KEY or not SECRET_KEY:
    print()
    print("=" * 60)
    print("ERROR: Alpaca API credentials are missing.")
    print("=" * 60)
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
# DISPLAY
# ============================================================

def print_header():
    print()
    print("=" * 70)
    print("🚀 AlphaPilot AI — Autonomous Exit Worker")
    print("=" * 70)
    print("Mode: ALPACA PAPER")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Stop Loss: {STOP_LOSS_PCT * 100:.0f}%")
    print(f"Take Profit: {TAKE_PROFIT_PCT * 100:.0f}%")
    print("Real fill confirmation: ENABLED")
    print("Real P&L logging: ENABLED")
    print("=" * 70)
    print()


# ============================================================
# PRICE HELPERS
# ============================================================

def get_option_price(symbol):
    """
    Get latest option quote.

    Uses midpoint between bid and ask when both are available.
    Falls back to bid or ask if only one side exists.
    """

    try:
        request = OptionLatestQuoteRequest(
            symbol_or_symbols=[symbol]
        )

        quotes = option_data_client.get_option_latest_quote(request)

        quote = quotes.get(symbol)

        if quote is None:
            return None

        bid = float(quote.bid_price or 0)
        ask = float(quote.ask_price or 0)

        if bid > 0 and ask > 0:
            return (bid + ask) / 2

        if bid > 0:
            return bid

        if ask > 0:
            return ask

        return None

    except Exception as exc:
        print(f"⚠️ Quote error for {symbol}: {exc}")
        return None


# ============================================================
# POSITION HELPERS
# ============================================================

def get_open_positions():
    """
    Return all currently open Alpaca positions.
    """

    try:
        return trading_client.get_all_positions()

    except Exception as exc:
        print(f"❌ Unable to read positions: {exc}")
        return []


# ============================================================
# ACTIVE SELL ORDER PROTECTION
# ============================================================

def has_active_sell_order(symbol):
    """
    Prevent duplicate SELL orders for the same option contract.
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

            status = str(order.status).lower()

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
        print(f"⚠️ Could not check active orders: {exc}")
        return False


# ============================================================
# ORDER STATUS
# ============================================================

def wait_for_fill(order_id, symbol):
    """
    Wait for Alpaca to confirm that the SELL order is filled.

    Returns:
        filled_price, filled_quantity, status

    If the order is not filled within the timeout, no trade is
    written to the trade history.
    """

    print()
    print(f"⏳ Waiting for SELL order fill...")
    print(f"Order ID: {order_id}")
    print(f"Contract: {symbol}")

    start_time = time.time()

    while time.time() - start_time < ORDER_FILL_TIMEOUT:

        try:
            order = trading_client.get_order_by_id(order_id)

            status = str(order.status).lower()

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Order status: {status.upper()}"
            )

            if status == "filled":

                filled_price = (
                    float(order.filled_avg_price)
                    if order.filled_avg_price
                    else None
                )

                filled_quantity = (
                    int(float(order.filled_qty))
                    if order.filled_qty
                    else 0
                )

                return (
                    filled_price,
                    filled_quantity,
                    status,
                )

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
            print(f"⚠️ Order status error: {exc}")

        time.sleep(3)

    print()
    print("⏰ Fill confirmation timeout.")
    print("The trade will NOT be recorded as completed.")

    return None, 0, "timeout"


# ============================================================
# TRADE HISTORY
# ============================================================

def ensure_trade_history_file():
    """
    Create trade history file if it doesn't exist.
    """

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


def trade_already_logged(symbol, exit_order_id=None):
    """
    Basic duplicate protection.

    The existing CSV does not necessarily contain an order ID,
    so symbol + recent exit time is used as the practical guard.
    """

    if not TRADE_HISTORY_FILE.exists():
        return False

    try:

        with open(
            TRADE_HISTORY_FILE,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                if row.get("symbol") != symbol:
                    continue

                exit_price = row.get("exit_price", "")

                if exit_price:
                    return True

        return False

    except Exception:
        return False


def get_entry_price(position):
    """
    Read the average entry price from the live Alpaca position.
    """

    try:
        return float(position.avg_entry_price)

    except Exception:
        return 0.0


def get_position_quantity(position):
    """
    Return absolute position quantity.
    """

    try:
        return abs(int(float(position.qty)))

    except Exception:
        return 0


def log_completed_trade(
    symbol,
    quantity,
    entry_price,
    exit_price,
    reason,
):
    """
    Record only a confirmed FILLED exit.

    P&L:
        (exit - entry) * quantity * 100
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

    pnl = exit_value - entry_value

    if entry_value != 0:
        pnl_percent = (
            pnl / entry_value
        ) * 100
    else:
        pnl_percent = 0

    exit_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
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
                "",
                exit_time,
                reason,
            ]
        )

    print()
    print("=" * 70)
    print("✅ REALIZED PAPER TRADE SAVED")
    print("=" * 70)
    print(f"Contract:       {symbol}")
    print(f"Quantity:       {quantity}")
    print(f"Entry Price:    ${entry_price:.2f}")
    print(f"Actual Exit:    ${exit_price:.2f}")
    print(f"Entry Value:    ${entry_value:,.2f}")
    print(f"Exit Value:     ${exit_value:,.2f}")
    print(f"Realized P&L:   ${pnl:,.2f}")
    print(f"Return:         {pnl_percent:.2f}%")
    print(f"Exit Reason:    {reason}")
    print(f"Exit Time:      {exit_time}")
    print("=" * 70)
    print()


# ============================================================
# EXIT EXECUTION
# ============================================================

def execute_exit(
    position,
    current_price,
    reason,
):
    """
    Submit SELL order and record trade only after FILLED.
    """

    symbol = position.symbol

    quantity = get_position_quantity(position)

    entry_price = get_entry_price(position)

    if quantity <= 0:
        print(f"⚠️ Invalid quantity for {symbol}")
        return

    if entry_price <= 0:
        print(f"⚠️ Invalid entry price for {symbol}")
        return

    print()
    print("🚨 EXIT EXECUTION")
    print("-" * 70)
    print(f"Contract:       {symbol}")
    print(f"Quantity:       {quantity}")
    print(f"Entry:          ${entry_price:.2f}")
    print(f"Current Quote:  ${current_price:.2f}")
    print(f"Reason:         {reason}")
    print("-" * 70)

    if has_active_sell_order(symbol):

        print(
            "⚠️ Active SELL order already exists."
        )

        print(
            "Duplicate SELL prevented."
        )

        return

    # --------------------------------------------------------
    # MARKET STATUS CHECK
    # --------------------------------------------------------

    try:

        clock = trading_client.get_clock()

        if not clock.is_open:

            print()
            print("⏰ MARKET CLOSED")
            print(
                "SELL order NOT submitted."
            )
            print(
                "Worker will retry automatically."
            )

            return

    except Exception as exc:

        print(
            f"⚠️ Could not verify market status: {exc}"
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

        order = trading_client.submit_order(
            order_data=order_request
        )

        print()
        print("🚀 PAPER SELL ORDER SUBMITTED")
        print(f"Order ID: {order.id}")
        print(f"Contract: {symbol}")

    except Exception as exc:

        print()
        print("❌ SELL ORDER FAILED")
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
    # FILL RESULT
    # --------------------------------------------------------

    if status != "filled":

        print()
        print("⚠️ SELL WAS NOT CONFIRMED FILLED")
        print(f"Final status: {status}")
        print()
        print(
            "No completed trade was written."
        )

        return

    if not filled_price or filled_quantity <= 0:

        print()
        print(
            "❌ Alpaca reported FILLED but "
            "fill information was incomplete."
        )

        return

    # --------------------------------------------------------
    # DUPLICATE LOG PROTECTION
    # --------------------------------------------------------

    if trade_already_logged(symbol):

        print()
        print(
            "⚠️ Trade appears to already exist "
            "in trade_history.csv."
        )

        print(
            "Duplicate history entry prevented."
        )

        return

    # --------------------------------------------------------
    # SAVE REALIZED TRADE
    # --------------------------------------------------------

    log_completed_trade(
        symbol=symbol,
        quantity=filled_quantity,
        entry_price=entry_price,
        exit_price=filled_price,
        reason=reason,
    )


# ============================================================
# POSITION ANALYSIS
# ============================================================

def monitor_position(position):
    """
    Analyze one open position.
    """

    symbol = position.symbol

    quantity = get_position_quantity(position)

    entry_price = get_entry_price(position)

    if quantity <= 0 or entry_price <= 0:
        return

    current_price = get_option_price(symbol)

    if current_price is None:

        print(
            f"⚠️ No current quote available for {symbol}"
        )

        return

    stop_loss = (
        entry_price
        * (1 - STOP_LOSS_PCT)
    )

    take_profit = (
        entry_price
        * (1 + TAKE_PROFIT_PCT)
    )

    current_return = (
        (current_price - entry_price)
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
# MAIN WORKER LOOP
# ============================================================

def run_worker():

    print_header()

    while True:

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print()
        print(
            f"[{timestamp}] 🔄 Checking positions..."
        )

        try:

            clock = trading_client.get_clock()

            if clock.is_open:

                print(
                    f"[{timestamp}] 🟢 US MARKET OPEN"
                )

            else:

                print(
                    f"[{timestamp}] 🔴 US MARKET CLOSED"
                )

        except Exception as exc:

            print(
                f"[{timestamp}] ⚠️ "
                f"Market status error: {exc}"
            )

            time.sleep(CHECK_INTERVAL)

            continue

        positions = get_open_positions()

        if not positions:

            print(
                "📭 No open positions."
            )

        else:

            print(
                f"📊 Open positions: {len(positions)}"
            )

            for position in positions:

                try:

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

        time.sleep(CHECK_INTERVAL)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        run_worker()

    except KeyboardInterrupt:

        print()
        print("=" * 70)
        print("🛑 AlphaPilot Exit Worker stopped by user.")
        print("=" * 70)
        print()

    except Exception as exc:

        print()
        print("=" * 70)
        print("❌ EXIT WORKER CRASHED")
        print("=" * 70)
        print(exc)
        print("=" * 70)
        print()
