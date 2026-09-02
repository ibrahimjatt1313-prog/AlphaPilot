
import os
import csv
import json
from datetime import datetime, timezone

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest


# ============================================================
# ALPHAPILOT AI — AUTOMATIC EXIT ENGINE
# ============================================================

# Load project .env
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise ValueError(
        "Alpaca credentials missing. "
        "Make sure ALPACA_API_KEY and ALPACA_SECRET_KEY "
        "exist in the project's .env file."
    )


# ============================================================
# ALPACA PAPER CLIENTS
# ============================================================

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=True
)

option_data_client = OptionHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)


# ============================================================
# CONFIGURATION
# ============================================================

STOP_LOSS_PCT = 0.25
TAKE_PROFIT_PCT = 0.50

# Files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PENDING_EXIT_FILE = os.path.join(
    BASE_DIR,
    "agents",
    "pending_exits.json"
)

TRADE_HISTORY_FILE = os.path.join(
    BASE_DIR,
    "agents",
    "trade_history.csv"
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_pending_exits():
    """
    Load exits that were detected while the market was closed.
    """

    if not os.path.exists(PENDING_EXIT_FILE):
        return {}

    try:
        with open(PENDING_EXIT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def save_pending_exits(data):
    """
    Save pending exit conditions.
    """

    os.makedirs(
        os.path.dirname(PENDING_EXIT_FILE),
        exist_ok=True
    )

    with open(
        PENDING_EXIT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


def remove_pending_exit(symbol):
    """
    Remove pending exit after successful submission.
    """

    pending = load_pending_exits()

    if symbol in pending:
        del pending[symbol]
        save_pending_exits(pending)


# ============================================================
# MARKET STATUS
# ============================================================

def is_market_open():
    """
    Ask Alpaca whether the US equity/options market is open.
    """

    try:
        clock = trading_client.get_clock()

        return bool(clock.is_open)

    except Exception as error:

        print(
            f"⚠️ Unable to determine market status: {error}"
        )

        return False


# ============================================================
# OPTION PRICE
# ============================================================

def get_option_price(symbol):
    """
    Get latest option quote and calculate mid price.
    """

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=symbol
        )

        quotes = option_data_client.get_option_latest_quote(
            request
        )

        if symbol not in quotes:
            return 0.0

        quote = quotes[symbol]

        bid = float(quote.bid_price or 0)
        ask = float(quote.ask_price or 0)

        if bid > 0 and ask > 0:
            return (bid + ask) / 2

        if ask > 0:
            return ask

        if bid > 0:
            return bid

        return 0.0

    except Exception as error:

        print(
            f"⚠️ Could not get option price for {symbol}: {error}"
        )

        return 0.0


# ============================================================
# OPEN EXIT ORDER CHECK
# ============================================================

def exit_order_already_exists(symbol):
    """
    Prevent duplicate SELL orders.
    """

    try:

        orders = trading_client.get_orders()

        active_statuses = {
            "new",
            "accepted",
            "pending_new",
            "partially_filled"
        }

        for order in orders:

            if order.symbol != symbol:
                continue

            if order.side != OrderSide.SELL:
                continue

            status = getattr(
                order.status,
                "value",
                str(order.status)
            )

            if status in active_statuses:
                return True

        return False

    except Exception as error:

        print(
            f"⚠️ Could not check existing orders: {error}"
        )

        return False


# ============================================================
# TRADE HISTORY
# ============================================================

def ensure_trade_history_file():

    if os.path.exists(TRADE_HISTORY_FILE):
        return

    os.makedirs(
        os.path.dirname(TRADE_HISTORY_FILE),
        exist_ok=True
    )

    with open(
        TRADE_HISTORY_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "symbol",
            "quantity",
            "entry_price",
            "exit_price",
            "entry_value",
            "exit_value",
            "p&l",
            "p&l%",
            "entry_time",
            "exit_time",
            "reason"
        ])


def log_exit(
    symbol,
    quantity,
    entry_price,
    exit_price,
    reason
):
    """
    Record realized trade information.
    """

    ensure_trade_history_file()

    entry_value = entry_price * quantity * 100
    exit_value = exit_price * quantity * 100

    pnl = exit_value - entry_value

    if entry_value != 0:
        pnl_pct = (pnl / entry_value) * 100
    else:
        pnl_pct = 0

    with open(
        TRADE_HISTORY_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            symbol,
            quantity,
            round(entry_price, 4),
            round(exit_price, 4),
            round(entry_value, 2),
            round(exit_value, 2),
            round(pnl, 2),
            round(pnl_pct, 2),
            "",
            utc_now(),
            reason
        ])


# ============================================================
# SUBMIT EXIT
# ============================================================

def submit_exit(
    symbol,
    quantity,
    entry_price,
    current_price,
    reason
):
    """
    Submit SELL order to Alpaca Paper.
    """

    if not is_market_open():

        print()
        print("⏰ MARKET CLOSED")
        print()
        print(
            f"🛑 Exit condition detected for {symbol}"
        )
        print(
            f"Reason: {reason}"
        )
        print(
            "SELL order NOT submitted."
        )
        print(
            "Exit saved for next market session."
        )

        pending = load_pending_exits()

        pending[symbol] = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": entry_price,
            "last_price": current_price,
            "reason": reason,
            "detected_at": utc_now()
        }

        save_pending_exits(pending)

        return {
            "status": "MARKET_CLOSED",
            "symbol": symbol,
            "reason": reason
        }


    if exit_order_already_exists(symbol):

        print(
            f"🔒 Exit order already exists for {symbol}"
        )

        return {
            "status": "EXIT_ALREADY_SUBMITTED",
            "symbol": symbol
        }


    try:

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )

        order = trading_client.submit_order(
            order_data=order_request
        )

        order_id = str(order.id)

        print()
        print("🚀 PAPER EXIT ORDER SUBMITTED")
        print(
            f"Contract: {symbol}"
        )
        print(
            f"Quantity: {quantity}"
        )
        print(
            f"Reason: {reason}"
        )
        print(
            f"Order ID: {order_id}"
        )

        remove_pending_exit(symbol)

        return {
            "status": "EXIT_SUBMITTED",
            "symbol": symbol,
            "order_id": order_id,
            "reason": reason
        }

    except Exception as error:

        print()
        print(
            f"❌ Exit order failed: {error}"
        )

        return {
            "status": "EXIT_FAILED",
            "symbol": symbol,
            "reason": reason,
            "error": str(error)
        }


# ============================================================
# MONITOR POSITIONS
# ============================================================

def monitor_positions():

    print("=" * 60)
    print("AlphaPilot AI — Automatic Exit Engine")
    print("=" * 60)

    market_open = is_market_open()

    print(
        f"Market Status: "
        f"{'🟢 OPEN' if market_open else '🔴 CLOSED'}"
    )

    print()

    try:

        positions = trading_client.get_all_positions()

    except Exception as error:

        print(
            f"❌ Could not retrieve positions: {error}"
        )

        return []


    if not positions:

        print("No open positions.")

        return []


    results = []

    for position in positions:

        symbol = position.symbol

        # Current AlphaPilot implementation monitors SPY options.
        if not symbol.startswith("SPY"):
            continue

        try:

            quantity = abs(
                int(float(position.qty))
            )

            entry_price = float(
                position.avg_entry_price
            )

        except Exception:

            continue


        if quantity <= 0:
            continue


        current_price = get_option_price(symbol)

        if current_price <= 0:

            print(
                f"⚠️ No valid quote for {symbol}"
            )

            continue


        stop_price = (
            entry_price *
            (1 - STOP_LOSS_PCT)
        )

        target_price = (
            entry_price *
            (1 + TAKE_PROFIT_PCT)
        )


        current_return = (
            (current_price - entry_price)
            / entry_price
        ) * 100


        print(
            f"Contract: {symbol}"
        )

        print(
            f"Quantity: {quantity}"
        )

        print(
            f"Entry: ${entry_price:.2f}"
        )

        print(
            f"Current: ${current_price:.2f}"
        )

        print(
            f"Stop Loss: ${stop_price:.2f}"
        )

        print(
            f"Take Profit: ${target_price:.2f}"
        )

        print(
            f"Return: {current_return:.2f}%"
        )


        exit_reason = None


        # ====================================================
        # EXIT CONDITIONS
        # ====================================================

        if current_price <= stop_price:

            exit_reason = "STOP LOSS"

        elif current_price >= target_price:

            exit_reason = "TAKE PROFIT"


        result = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": current_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "return_pct": current_return,
            "exit_reason": exit_reason
        }


        # ====================================================
        # NO EXIT
        # ====================================================

        if exit_reason is None:

            print(
                "🟢 Position within risk limits."
            )

            print()

            results.append(result)

            continue


        # ====================================================
        # EXIT REQUIRED
        # ====================================================

        print()

        print(
            f"🛑 {exit_reason} TRIGGERED"
        )


        exit_result = submit_exit(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            current_price=current_price,
            reason=exit_reason
        )


        result.update(exit_result)

        results.append(result)

        print()


    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    results = monitor_positions()

    print()
    print("=" * 60)
    print("Exit Engine Complete")
    print("=" * 60)

    if not results:

        print("No monitored positions.")

    else:

        for result in results:

            print(
                f"{result['symbol']} → "
                f"{result.get('status', 'MONITORING')}"
            )
