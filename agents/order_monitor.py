
import os
import time
from datetime import datetime

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus


# ============================================================
# ALPHAPILOT AI - AUTO ORDER MONITOR
# ============================================================

load_dotenv()


# ============================================================
# API KEYS
# ============================================================

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

UNDERLYING = "SPY"

CHECK_INTERVAL = 10

MAX_CHECKS = 30


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("          ALPHAPILOT AI AUTO ORDER MONITOR")
print("=" * 70)

print()
print("Mode              : PAPER TRADING")
print("Underlying         :", UNDERLYING)
print("Order ID           : AUTO DETECT")
print("Check Interval     :", CHECK_INTERVAL, "seconds")
print("Maximum Checks     :", MAX_CHECKS)


# ============================================================
# GET OPEN ORDERS
# ============================================================

def get_open_orders():

    try:

        request = GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            limit=100,
            nested=True
        )

        orders = trading_client.get_orders(
            filter=request
        )

        return list(orders)

    except Exception as e:

        print("\nERROR finding orders:")
        print(e)

        return []


# ============================================================
# FIND LATEST SPY OPTION BUY ORDER
# ============================================================

def find_latest_buy_order():

    orders = get_open_orders()

    candidates = []

    for order in orders:

        try:

            symbol = str(order.symbol)

            side = order.side

            # ------------------------------------------------
            # We only want BUY orders
            # ------------------------------------------------

            if side != OrderSide.BUY:
                continue

            # ------------------------------------------------
            # We only want SPY option contracts
            # ------------------------------------------------

            if not symbol.startswith("SPY"):
                continue

            # ------------------------------------------------
            # Option symbols are longer than normal SPY
            # ------------------------------------------------

            if len(symbol) < 10:
                continue

            candidates.append(order)

        except Exception:
            continue


    if not candidates:

        return None


    # Latest order first
    candidates.sort(
        key=lambda x: (
            x.created_at
            if x.created_at is not None
            else datetime.min
        ),
        reverse=True
    )

    return candidates[0]


# ============================================================
# DISPLAY ORDER
# ============================================================

def display_order(order):

    print("\n" + "=" * 70)
    print("             ORDER STATUS")
    print("=" * 70)

    print(
        "Order ID       :",
        order.id
    )

    print(
        "Symbol         :",
        order.symbol
    )

    print(
        "Side           :",
        order.side
    )

    print(
        "Quantity       :",
        order.qty
    )

    print(
        "Limit Price    :",
        order.limit_price
    )

    print(
        "Status         :",
        order.status
    )

    print(
        "Filled Qty     :",
        order.filled_qty
    )

    print(
        "Filled Avg     :",
        order.filled_avg_price
    )

    print(
        "Created At     :",
        order.created_at
    )

    print(
        "Updated At     :",
        order.updated_at
    )


# ============================================================
# CHECK SPECIFIC ORDER
# ============================================================

def get_order_by_id(order_id):

    try:

        return trading_client.get_order_by_id(
            order_id
        )

    except Exception as e:

        print("\nERROR reading order:")
        print(e)

        return None


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("             STARTING AUTO ORDER MONITOR")
    print("=" * 70)

    print()
    print("Searching for latest PAPER BUY order...")
    print("No new order will be submitted.")


    # ========================================================
    # FIRST FIND ORDER
    # ========================================================

    order = find_latest_buy_order()


    if order is None:

        print("\n" + "=" * 70)
        print("             NO BUY ORDER FOUND")
        print("=" * 70)

        print()
        print(
            "No open SPY option BUY order was found."
        )

        print(
            "This is normal if the Entry Manager"
        )

        print(
            "did not submit an order."
        )

        print("=" * 70)

        raise SystemExit


    ORDER_ID = order.id


    print("\n" + "=" * 70)
    print("             ORDER FOUND")
    print("=" * 70)

    print(
        "Order ID :",
        ORDER_ID
    )

    print(
        "Symbol   :",
        order.symbol
    )

    print(
        "Status   :",
        order.status
    )


    # ========================================================
    # MONITOR ORDER
    # ========================================================

    for check_number in range(
        1,
        MAX_CHECKS + 1
    ):

        print("\n" + "-" * 70)

        print(
            "Check",
            "%d/%d" % (
                check_number,
                MAX_CHECKS
            )
        )

        print(
            "Time:",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        order = get_order_by_id(
            ORDER_ID
        )


        # ----------------------------------------------------
        # API ERROR
        # ----------------------------------------------------

        if order is None:

            print(
                "\nUnable to read order status."
            )

            time.sleep(
                CHECK_INTERVAL
            )

            continue


        display_order(order)


        status = str(
            order.status
        ).lower()


        # ====================================================
        # FILLED
        # ====================================================

        if "filled" in status:

            print("\n" + "=" * 70)
            print("             ORDER FILLED")
            print("=" * 70)

            print()
            print(
                "PAPER ORDER FILLED SUCCESSFULLY."
            )

            print(
                "Symbol       :",
                order.symbol
            )

            print(
                "Filled Qty   :",
                order.filled_qty
            )

            print(
                "Average Price:",
                order.filled_avg_price
            )

            print()
            print(
                "NEXT STEP:"
            )

            print(
                "Position monitor can now track"
            )

            print(
                "Stop Loss and Take Profit."
            )

            print("=" * 70)

            break


        # ====================================================
        # CANCELED
        # ====================================================

        if "canceled" in status:

            print("\n" + "=" * 70)
            print("             ORDER CANCELED")
            print("=" * 70)

            print(
                "No position should be created"
                " by this order."
            )

            print("=" * 70)

            break


        # ====================================================
        # REJECTED
        # ====================================================

        if "rejected" in status:

            print("\n" + "=" * 70)
            print("             ORDER REJECTED")
            print("=" * 70)

            print(
                "Alpaca rejected the PAPER order."
            )

            print("=" * 70)

            break


        # ====================================================
        # EXPIRED
        # ====================================================

        if "expired" in status:

            print("\n" + "=" * 70)
            print("             ORDER EXPIRED")
            print("=" * 70)

            print(
                "The order expired without filling."
            )

            print("=" * 70)

            break


        # ====================================================
        # STILL ACTIVE
        # ====================================================

        print()

        print(
            "Order is still active."
        )

        print(
            "Current status:",
            order.status
        )

        print(
            "Waiting",
            CHECK_INTERVAL,
            "seconds..."
        )


        time.sleep(
            CHECK_INTERVAL
        )


    # ========================================================
    # COMPLETE
    # ========================================================

    print("\n" + "=" * 70)
    print("             ORDER MONITOR COMPLETE")
    print("=" * 70)

    print(
        "Timestamp :",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 70)
