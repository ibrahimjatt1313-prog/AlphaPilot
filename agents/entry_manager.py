
import os
from datetime import datetime

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest

from trade_signal import create_trade_signal


# ============================================================
# ALPHAPILOT AI - ENTRY MANAGER
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
# ALPACA CLIENTS
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

SYMBOL = "SPY"

QUANTITY = 1

MIN_CONFIDENCE = 70

MAX_POSITION_VALUE = 500.00


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             ALPHAPILOT AI ENTRY MANAGER")
print("=" * 70)

print()

print(
    "Mode              : PAPER TRADING"
)

print(
    "Underlying        :",
    SYMBOL
)

print(
    "Quantity          :",
    QUANTITY
)

print(
    "Min Confidence    :",
    str(MIN_CONFIDENCE) + "%"
)

print(
    "Max Position      : $%.2f"
    % MAX_POSITION_VALUE
)


# ============================================================
# EXISTING POSITION CHECK
# ============================================================

def has_existing_position():

    try:

        positions = trading_client.get_all_positions()

        for position in positions:

            qty = float(position.qty)

            if qty != 0:

                print(
                    "\nExisting position found:",
                    position.symbol,
                    "Qty:",
                    position.qty
                )

                return True

        return False

    except Exception as e:

        print("\nERROR checking positions:")
        print(e)

        # Fail closed.
        return True


# ============================================================
# OPEN ORDER CHECK
# ============================================================

def has_open_orders():

    try:

        request = GetOrdersRequest(
            status=QueryOrderStatus.OPEN
        )

        orders = trading_client.get_orders(
            filter=request
        )

        if orders:

            print(
                "\nOpen orders found:",
                len(orders)
            )

            for order in orders:

                print(
                    " -",
                    order.symbol,
                    order.side,
                    order.qty,
                    order.status
                )

            return True

        return False

    except Exception as e:

        print("\nERROR checking open orders:")
        print(e)

        # Fail closed.
        return True


# ============================================================
# OPTION QUOTE
# ============================================================

def get_option_quote(option_symbol):

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=option_symbol
        )

        quotes = option_client.get_option_latest_quote(
            request
        )

        quote = quotes[option_symbol]

        bid = quote.bid_price
        ask = quote.ask_price

        if bid is None or ask is None:

            return None


        bid = float(bid)
        ask = float(ask)


        if bid <= 0 or ask <= 0:

            return None


        if ask < bid:

            return None


        mid = (
            bid + ask
        ) / 2


        return {

            "bid": bid,

            "ask": ask,

            "mid": mid

        }


    except Exception as e:

        print("\nOPTION QUOTE ERROR:")
        print(e)

        return None


# ============================================================
# VALIDATE ORDER
# ============================================================

def validate_order(
    option_symbol,
    quantity,
    limit_price
):

    if not option_symbol:

        print("\nORDER BLOCKED")
        print("Option symbol is missing.")

        return False


    if quantity <= 0:

        print("\nORDER BLOCKED")
        print("Invalid quantity.")

        return False


    if limit_price <= 0:

        print("\nORDER BLOCKED")
        print("Invalid limit price.")

        return False


    estimated_cost = (
        limit_price
        * quantity
        * 100
    )


    print("\n" + "=" * 70)
    print("             ORDER SAFETY CHECK")
    print("=" * 70)

    print(
        "Option          :",
        option_symbol
    )

    print(
        "Side            : BUY"
    )

    print(
        "Quantity        :",
        quantity
    )

    print(
        "Limit Price     : $%.2f"
        % limit_price
    )

    print(
        "Estimated Cost  : $%.2f"
        % estimated_cost
    )


    # --------------------------------------------------------
    # MAX POSITION VALUE
    # --------------------------------------------------------

    if estimated_cost > MAX_POSITION_VALUE:

        print("\nORDER BLOCKED")

        print(
            "Estimated cost exceeds MAX_POSITION_VALUE."
        )

        print(
            "Maximum allowed : $%.2f"
            % MAX_POSITION_VALUE
        )

        return False


    # --------------------------------------------------------
    # EXISTING POSITION
    # --------------------------------------------------------

    if has_existing_position():

        print("\nORDER BLOCKED")

        print(
            "An existing position already exists."
        )

        return False


    # --------------------------------------------------------
    # OPEN ORDERS
    # --------------------------------------------------------

    if has_open_orders():

        print("\nORDER BLOCKED")

        print(
            "An open order already exists."
        )

        return False


    return True


# ============================================================
# PLACE PAPER ORDER
# ============================================================

def place_entry_order(
    option_symbol,
    quantity,
    limit_price
):

    if not validate_order(
        option_symbol,
        quantity,
        limit_price
    ):

        return False


    # --------------------------------------------------------
    # FINAL ORDER PREVIEW
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("             FINAL PAPER ORDER")
    print("=" * 70)

    print(
        "Symbol   :",
        option_symbol
    )

    print(
        "Side     : BUY"
    )

    print(
        "Quantity :",
        quantity
    )

    print(
        "Price    : $%.2f"
        % limit_price
    )

    print()

    print(
        "Paper trading mode is ACTIVE."
    )

    print(
        "Submitting PAPER order..."
    )


    # --------------------------------------------------------
    # CREATE ORDER
    # --------------------------------------------------------

    try:

        order_request = LimitOrderRequest(

            symbol=option_symbol,

            qty=quantity,

            side=OrderSide.BUY,

            time_in_force=TimeInForce.DAY,

            limit_price=limit_price

        )


        order = trading_client.submit_order(
            order_request
        )


        print("\n" + "=" * 70)
        print("             PAPER ORDER SUBMITTED")
        print("=" * 70)

        print(
            "Order ID :",
            order.id
        )

        print(
            "Symbol   :",
            order.symbol
        )

        print(
            "Side     :",
            order.side
        )

        print(
            "Quantity :",
            order.qty
        )

        print(
            "Status   :",
            order.status
        )

        print()

        print(
            "PAPER BUY ORDER SUBMITTED SUCCESSFULLY."
        )

        return True


    except Exception as e:

        print("\nERROR placing paper order:")
        print(e)

        return False


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("             TRADE SIGNAL")
    print("=" * 70)


    # --------------------------------------------------------
    # GET FINAL SIGNAL
    # --------------------------------------------------------

    signal = create_trade_signal()


    # --------------------------------------------------------
    # DISPLAY SIGNAL
    # --------------------------------------------------------

    print()

    print(
        "Symbol     :",
        signal.get("symbol", SYMBOL)
    )

    print(
        "Decision   :",
        signal.get("decision", "NO TRADE")
    )

    print(
        "Confidence :",
        str(
            signal.get("confidence", 0)
        ) + "%"
    )

    print(
        "Reason     :",
        signal.get(
            "reason",
            "No reason provided."
        )
    )


    # --------------------------------------------------------
    # REASONS
    # --------------------------------------------------------

    reasons = signal.get(
        "reasons",
        []
    )


    if reasons:

        print()

        print("Reasons:")

        for reason in reasons:

            print(
                " -",
                reason
            )


    # ========================================================
    # DECISION SAFETY
    # ========================================================

    decision = signal.get(
        "decision",
        "NO TRADE"
    )

    confidence = signal.get(
        "confidence",
        0
    )


    if decision != "BUY":

        print("\n" + "=" * 70)
        print("             NO ORDER")
        print("=" * 70)

        print(
            "AI decision is not BUY."
        )

        print(
            "Entry manager will NOT place an order."
        )

        print("=" * 70)

        raise SystemExit


    # ========================================================
    # CONFIDENCE SAFETY
    # ========================================================

    if confidence < MIN_CONFIDENCE:

        print("\n" + "=" * 70)
        print("             NO ORDER")
        print("=" * 70)

        print(
            "Confidence below minimum requirement."
        )

        print(
            "Required :",
            str(MIN_CONFIDENCE) + "%"
        )

        print(
            "Received :",
            str(confidence) + "%"
        )

        print("=" * 70)

        raise SystemExit


    # ========================================================
    # OPTION
    # ========================================================

    option = signal.get(
        "option"
    )


    if not option:

        print("\n" + "=" * 70)
        print("             NO ORDER")
        print("=" * 70)

        print(
            "No option was returned by trade_signal.py."
        )

        print("=" * 70)

        raise SystemExit


    option_symbol = option.get(
        "symbol"
    )


    if not option_symbol:

        print("\nNO ORDER")

        print(
            "Option symbol is missing."
        )

        raise SystemExit


    # ========================================================
    # OPTION INFORMATION
    # ========================================================

    print("\n" + "=" * 70)
    print("             OPTION SELECTION")
    print("=" * 70)

    print(
        "Selected Option :",
        option_symbol
    )

    print(
        "Strike          : $%.2f"
        % float(option["strike"])
    )

    print(
        "Expiration      :",
        option["expiration"]
    )

    print(
        "Distance        : $%.2f"
        % float(option["distance"])
    )

    print(
        "Open Interest   :",
        int(option["open_interest"])
    )

    print(
        "Selection Score :",
        option["score"]
    )


    # ========================================================
    # OPTION QUOTE
    # ========================================================

    print("\n" + "=" * 70)
    print("             OPTION QUOTE")
    print("=" * 70)


    option_quote = get_option_quote(
        option_symbol
    )


    if option_quote is None:

        print(
            "NO ORDER"
        )

        print(
            "Option quote unavailable."
        )

        raise SystemExit


    print(
        "Bid : $%.2f"
        % option_quote["bid"]
    )

    print(
        "Ask : $%.2f"
        % option_quote["ask"]
    )

    print(
        "Mid : $%.2f"
        % option_quote["mid"]
    )


    # ========================================================
    # ENTRY PRICE
    # ========================================================

    # Conservative entry:
    # do not pay above the current ask.

    entry_price = round(
        option_quote["ask"],
        2
    )


    estimated_cost = (
        entry_price
        * QUANTITY
        * 100
    )


    print()

    print(
        "Entry Limit Price : $%.2f"
        % entry_price
    )

    print(
        "Estimated Cost    : $%.2f"
        % estimated_cost
    )


    # ========================================================
    # PLACE PAPER ORDER
    # ========================================================

    order_success = place_entry_order(

        option_symbol,

        QUANTITY,

        entry_price

    )


    # ========================================================
    # RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("             ENTRY MANAGER COMPLETE")
    print("=" * 70)

    print(
        "Order Submitted :",
        "YES" if order_success else "NO"
    )

    print(
        "Timestamp        :",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 70)

