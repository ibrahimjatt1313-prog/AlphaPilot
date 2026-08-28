import os
import time

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient

from trade_logger import log_trade


# ============================================================
# ALPHAPILOT AI - EXIT ORDER MONITOR
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


# ============================================================
# SETTINGS
# ============================================================

ORDER_ID = None

SYMBOL = "SPY260904C00772000"

CHECK_INTERVAL = 10

ENTRY_PRICE = 4.85

QUANTITY = 3

REASON = "AUTO EXIT"


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             ALPHAPILOT AI EXIT ORDER MONITOR")
print("=" * 70)

print("\nMode          : PAPER TRADING")
print("Symbol        :", SYMBOL)
print("Quantity      :", QUANTITY)
print("Entry Price   : $%.2f" % ENTRY_PRICE)
print("Check Interval:", CHECK_INTERVAL, "seconds")


# ============================================================
# GET ORDER
# ============================================================

def get_order():

    try:

        if not ORDER_ID:

            print("\nERROR: ORDER_ID is not set.")

            return None

        order = trading_client.get_order_by_id(
            ORDER_ID
        )

        return order

    except Exception as e:

        print("\nOrder Error:", e)

        return None


# ============================================================
# MAIN
# ============================================================

print("\nWaiting for SELL order to fill...")
print("-" * 70)


while True:

    order = get_order()

    if order is None:

        time.sleep(CHECK_INTERVAL)

        continue


    print("\n" + "-" * 70)

    print(
        "Time :",
        time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        "Order Status :",
        order.status
    )

    print(
        "Symbol       :",
        order.symbol
    )

    print(
        "Side         :",
        order.side
    )

    print(
        "Quantity     :",
        order.qty
    )

    print(
        "Filled Qty   :",
        order.filled_qty
    )


    # ========================================================
    # FILLED
    # ========================================================

    if str(order.status).lower().endswith("filled"):

        filled_price = float(
            order.filled_avg_price
        )

        exit_time = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print("\n" + "=" * 70)
        print("             SELL ORDER FILLED")
        print("=" * 70)

        print(
            "Exit Price : $%.2f"
            % filled_price
        )

        print(
            "Quantity   :",
            order.filled_qty
        )


        # ----------------------------------------------------
        # LOG TRADE
        # ----------------------------------------------------

        log_trade(

            symbol=SYMBOL,

            quantity=float(order.filled_qty),

            entry_price=ENTRY_PRICE,

            exit_price=filled_price,

            entry_time="",

            exit_time=exit_time,

            reason=REASON
        )


        print("\nTrade has been saved to trade_history.csv.")

        break


    # ========================================================
    # CANCELED / EXPIRED / REJECTED
    # ========================================================

    status = str(
        order.status
    ).lower()


    if (
        "canceled" in status
        or "expired" in status
        or "rejected" in status
    ):

        print("\n" + "=" * 70)
        print("             EXIT ORDER NOT FILLED")
        print("=" * 70)

        print(
            "Final Status :",
            order.status
        )

        break


    # ========================================================
    # STILL ACTIVE
    # ========================================================

    print(
        "\nExit order is still active."
    )

    time.sleep(
        CHECK_INTERVAL
    )


# ============================================================
# END
# ============================================================

print("\n" + "=" * 70)
print("             EXIT ORDER MONITOR COMPLETE")
print("=" * 70)