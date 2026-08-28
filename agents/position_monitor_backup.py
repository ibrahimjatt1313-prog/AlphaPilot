import os
import time

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest


# ============================================================
# ALPHAPILOT AI - POSITION MONITOR
# ============================================================

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    print("ERROR: Alpaca API keys not found.")
    raise SystemExit


# ============================================================
# ALPACA CONNECTION
# ============================================================

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=True
)

option_client = OptionHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)


# ============================================================
# SETTINGS
# ============================================================

SYMBOL = "SPY260904C00772000"

CHECK_INTERVAL = 10

# Safety stop
STOP_LOSS = 1.77

# IMPORTANT:
# Take profit MUST be above entry price.
# Current entry was approximately $4.85.
TAKE_PROFIT = 7.76

# Do not automatically exit unless explicitly enabled.
AUTO_EXIT = True


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             ALPHAPILOT AI POSITION MONITOR")
print("=" * 70)

print("\nMode          : PAPER TRADING")
print("Option        :", SYMBOL)
print("Stop Loss     : $%.2f" % STOP_LOSS)
print("Take Profit   : $%.2f" % TAKE_PROFIT)
print("Auto Exit     :", AUTO_EXIT)
print("Check Interval:", CHECK_INTERVAL, "seconds")


# ============================================================
# GET OPEN POSITION
# ============================================================

def get_position():

    try:

        position = trading_client.get_open_position(
            SYMBOL
        )

        return position

    except Exception:

        return None


# ============================================================
# CHECK EXISTING EXIT ORDERS
# ============================================================

def has_open_exit_order():

    try:

        orders = trading_client.get_orders(
            filter="open"
        )

        for order in orders:

            if (
                order.symbol == SYMBOL
                and order.side == OrderSide.SELL
            ):
                return True

        return False

    except Exception as e:

        print("\nError checking open orders:", e)

        return False


# ============================================================
# GET OPTION QUOTE
# ============================================================

def get_option_quote():

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=SYMBOL
        )

        quotes = option_client.get_option_latest_quote(
            request
        )

        quote = quotes[SYMBOL]

        bid = quote.bid_price
        ask = quote.ask_price

        return bid, ask

    except Exception as e:

        print("\nPrice Error:", e)

        return None, None


# ============================================================
# CALCULATE P&L
# ============================================================

def calculate_pnl(
    entry_price,
    current_price,
    quantity
):

    multiplier = 100

    pnl = (
        current_price
        - entry_price
    ) * quantity * multiplier

    invested = (
        entry_price
        * quantity
        * multiplier
    )

    if invested > 0:

        pnl_percent = (
            pnl / invested
        ) * 100

    else:

        pnl_percent = 0

    return pnl, pnl_percent


# ============================================================
# PLACE EXIT ORDER
# ============================================================

def place_exit_order(quantity, bid):

    if quantity <= 0:
        print("ERROR: Invalid position quantity.")
        return False

    if bid is None or bid <= 0:
        print("ERROR: Invalid bid price.")
        return False

    # --------------------------------------------------------
    # Protect against duplicate SELL orders
    # --------------------------------------------------------

    if has_open_exit_order():

        print("\nAn existing SELL order already exists.")
        print("No duplicate exit order will be placed.")

        return False

    # --------------------------------------------------------
    # Use current bid as limit price
    # --------------------------------------------------------

    exit_price = round(float(bid), 2)

    print("\nPreparing PAPER SELL order...")
    print("--------------------------------")

    print("Symbol   :", SYMBOL)
    print("Side     : SELL")
    print("Quantity :", quantity)
    print("Limit    : $%.2f" % exit_price)

    try:

        order_request = LimitOrderRequest(
            symbol=SYMBOL,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=exit_price
        )

        order = trading_client.submit_order(
            order_request
        )

        print("\n" + "=" * 70)
        print("             EXIT ORDER SUBMITTED")
        print("=" * 70)

        print("Order ID :", order.id)
        print("Status   :", order.status)
        print("Symbol   :", order.symbol)
        print("Quantity :", order.qty)
        print("Side     :", order.side)

        print("\nPAPER SELL ORDER SUCCESSFUL")

        return True

    except Exception as e:

        print("\nERROR placing exit order:")
        print(e)

        return False


# ============================================================
# MAIN MONITOR
# ============================================================

print("\n")
print("Checking for open position...")
print("-" * 70)


while True:

    position = get_position()

    # --------------------------------------------------------
    # NO POSITION
    # --------------------------------------------------------

    if position is None:

        print(
            "\nNo open position found for:",
            SYMBOL
        )

        print(
            "Position may have been closed."
        )

        break


    # --------------------------------------------------------
    # POSITION FOUND
    # --------------------------------------------------------

    quantity = float(position.qty)

    entry_price = float(
        position.avg_entry_price
    )

    bid, ask = get_option_quote()


    print("\n" + "-" * 70)

    print(
        "Time :",
        time.strftime("%Y-%m-%d %H:%M:%S")
    )

    print("Symbol   :", SYMBOL)
    print("Quantity :", quantity)

    print(
        "Entry Price : $%.2f"
        % entry_price
    )


    # --------------------------------------------------------
    # QUOTE UNAVAILABLE
    # --------------------------------------------------------

    if bid is None and ask is None:

        print(
            "Current Quote : UNAVAILABLE"
        )

        time.sleep(CHECK_INTERVAL)

        continue


    # --------------------------------------------------------
    # CALCULATE MONITOR PRICE
    # --------------------------------------------------------

    if bid is not None and ask is not None:

        current_price = (
            float(bid)
            + float(ask)
        ) / 2

    elif bid is not None:

        current_price = float(bid)

    else:

        current_price = float(ask)


    print(
        "Bid        : $%.2f"
        % float(bid)
        if bid is not None
        else "Bid        : N/A"
    )

    print(
        "Ask        : $%.2f"
        % float(ask)
        if ask is not None
        else "Ask        : N/A"
    )

    print(
        "Mid        : $%.2f"
        % current_price
    )


    # --------------------------------------------------------
    # P&L
    # --------------------------------------------------------

    pnl, pnl_percent = calculate_pnl(
        entry_price,
        current_price,
        quantity
    )

    print(
        "P&L        : $%.2f"
        % pnl
    )

    print(
        "P&L %%      : %.2f%%"
        % pnl_percent
    )


    # ========================================================
    # SAFETY VALIDATION
    # ========================================================

    if TAKE_PROFIT <= entry_price:

        print("\n" + "=" * 70)
        print("ERROR: INVALID TAKE PROFIT")
        print("=" * 70)

        print(
            "Entry Price : $%.2f"
            % entry_price
        )

        print(
            "Take Profit : $%.2f"
            % TAKE_PROFIT
        )

        print(
            "\nTake Profit must be ABOVE entry price."
        )

        break


    # ========================================================
    # STOP LOSS
    # ========================================================

    if current_price <= STOP_LOSS:

        print("\n" + "=" * 70)
        print("             STOP LOSS SIGNAL")
        print("=" * 70)

        print(
            "Current Price : $%.2f"
            % current_price
        )

        print(
            "Stop Loss     : $%.2f"
            % STOP_LOSS
        )

        print(
            "Estimated P&L : $%.2f"
            % pnl
        )

        if AUTO_EXIT:

            print("\nRisk condition triggered.")

            place_exit_order(
                quantity,
                bid
            )

        else:

            print(
                "\nAUTO EXIT DISABLED."
            )

        break


    # ========================================================
    # TAKE PROFIT
    # ========================================================

    if current_price >= TAKE_PROFIT:

        print("\n" + "=" * 70)
        print("             TAKE PROFIT SIGNAL")
        print("=" * 70)

        print(
            "Current Price : $%.2f"
            % current_price
        )

        print(
            "Take Profit   : $%.2f"
            % TAKE_PROFIT
        )

        print(
            "Estimated P&L : $%.2f"
            % pnl
        )

        if AUTO_EXIT:

            print("\nProfit target reached.")

            place_exit_order(
                quantity,
                bid
            )

        else:

            print(
                "\nAUTO EXIT DISABLED."
            )

        break


    # ========================================================
    # POSITION STILL ACTIVE
    # ========================================================

    if pnl >= 0:

        print(
            "\nPosition Status: PROFIT"
        )

    else:

        print(
            "\nPosition Status: LOSS"
        )

    print(
        "Position Status: MONITORING"
    )

    time.sleep(CHECK_INTERVAL)


# ============================================================
# END
# ============================================================

print("\n" + "=" * 70)
print("             POSITION MONITOR COMPLETE")
print("=" * 70)