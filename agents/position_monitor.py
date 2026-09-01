import os
import time

from dotenv import load_dotenv
from trade_logger import log_trade

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest


# ============================================================
# ALPHAPILOT AI - DYNAMIC POSITION MONITOR
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

CHECK_INTERVAL = 10

# Risk management
STOP_LOSS_PERCENT = 30.0
TAKE_PROFIT_PERCENT = 60.0

AUTO_EXIT = True


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("          ALPHAPILOT AI DYNAMIC POSITION MONITOR")
print("=" * 70)

print()
print("Mode              : PAPER TRADING")
print("Symbol            : AUTO DETECT")
print("Stop Loss         :", STOP_LOSS_PERCENT, "%")
print("Take Profit       :", TAKE_PROFIT_PERCENT, "%")
print("Auto Exit         :", AUTO_EXIT)
print("Check Interval    :", CHECK_INTERVAL, "seconds")


# ============================================================
# FIND OPEN OPTION POSITION
# ============================================================

def get_open_option_position():

    try:

        positions = trading_client.get_all_positions()

        for position in positions:

            symbol = str(position.symbol)

            # ------------------------------------------------
            # Options symbols normally start with the
            # underlying symbol followed by expiration/type.
            # For AlphaPilot we only want SPY option positions.
            # ------------------------------------------------

            if symbol.startswith("SPY"):

                qty = float(position.qty)

                if qty > 0:

                    return position

        return None

    except Exception as e:

        print("\nPOSITION ERROR:")
        print(e)

        return None


# ============================================================
# GET OPTION QUOTE
# ============================================================

def get_option_quote(symbol):

    try:

        request = OptionLatestQuoteRequest(
            symbol_or_symbols=symbol
        )

        quotes = option_client.get_option_latest_quote(
            request
        )

        quote = quotes[symbol]

        bid = quote.bid_price
        ask = quote.ask_price

        if bid is not None:
            bid = float(bid)

        if ask is not None:
            ask = float(ask)

        return bid, ask

    except Exception as e:

        print("\nOPTION PRICE ERROR:")
        print(e)

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
# CHECK EXISTING SELL ORDER
# ============================================================

def get_existing_sell_order(symbol):

    try:

        orders = trading_client.get_orders(
            filter="open"
        )

        for order in orders:

            if (
                order.symbol == symbol
                and order.side == OrderSide.SELL
            ):

                return order

        return None

    except Exception as e:

        print("\nOPEN ORDER ERROR:")
        print(e)

        return None


# ============================================================
# WAIT FOR EXIT ORDER
# ============================================================

def wait_for_exit_fill(
    order_id,
    symbol,
    entry_price,
    quantity,
    reason
):

    print("\n" + "=" * 70)
    print("             MONITORING EXIT ORDER")
    print("=" * 70)

    print("Order ID :", order_id)
    print("Symbol   :", symbol)
    print("Reason   :", reason)

    while True:

        try:

            order = trading_client.get_order_by_id(
                order_id
            )

        except Exception as e:

            print("\nEXIT ORDER CHECK ERROR:")
            print(e)

            time.sleep(CHECK_INTERVAL)

            continue

        status = str(
            order.status
        ).lower()

        print()
        print(
            "Exit Status :",
            order.status
        )

        print(
            "Filled Qty  :",
            order.filled_qty
        )

        # ----------------------------------------------------
        # FILLED
        # ----------------------------------------------------

        if "filled" in status:

            if order.filled_avg_price is None:

                print(
                    "\nERROR: Filled price unavailable."
                )

                return False

            exit_price = float(
                order.filled_avg_price
            )

            filled_quantity = float(
                order.filled_qty
            )

            exit_time = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print("\n" + "=" * 70)
            print("             EXIT ORDER FILLED")
            print("=" * 70)

            print(
                "Symbol      :",
                symbol
            )

            print(
                "Exit Price  : $%.2f"
                % exit_price
            )

            print(
                "Quantity    :",
                filled_quantity
            )

            print(
                "Reason      :",
                reason
            )

            # ------------------------------------------------
            # LOG TRADE
            # ------------------------------------------------

            try:

                log_trade(
                    symbol=symbol,
                    quantity=filled_quantity,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    entry_time="",
                    exit_time=exit_time,
                    reason=reason
                )

                print(
                    "\nTrade successfully logged."
                )

            except Exception as e:

                print(
                    "\nTRADE LOG ERROR:"
                )

                print(e)

                return False

            return True

        # ----------------------------------------------------
        # CANCELED
        # ----------------------------------------------------

        if (
            "canceled" in status
            or "cancelled" in status
        ):

            print("\nEXIT ORDER CANCELED.")

            return False

        # ----------------------------------------------------
        # REJECTED
        # ----------------------------------------------------

        if "rejected" in status:

            print("\nEXIT ORDER REJECTED.")

            return False

        # ----------------------------------------------------
        # EXPIRED
        # ----------------------------------------------------

        if "expired" in status:

            print("\nEXIT ORDER EXPIRED.")

            return False

        print(
            "Exit order still active..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# PLACE PAPER SELL
# ============================================================

def place_exit_order(
    symbol,
    quantity,
    bid,
    entry_price,
    reason
):

    if quantity <= 0:

        print(
            "ERROR: Invalid quantity."
        )

        return False

    if bid is None or bid <= 0:

        print(
            "ERROR: Invalid bid price."
        )

        return False

    # --------------------------------------------------------
    # DUPLICATE SELL PROTECTION
    # --------------------------------------------------------

    existing_order = get_existing_sell_order(
        symbol
    )

    if existing_order is not None:

        print("\n" + "=" * 70)
        print("       EXISTING SELL ORDER DETECTED")
        print("=" * 70)

        print(
            "Order ID :",
            existing_order.id
        )

        print(
            "Status   :",
            existing_order.status
        )

        print(
            "No duplicate SELL order will be submitted."
        )

        return wait_for_exit_fill(
            existing_order.id,
            symbol,
            entry_price,
            quantity,
            reason
        )

    # --------------------------------------------------------
    # SELL AT CURRENT BID
    # --------------------------------------------------------

    exit_price = round(
        float(bid),
        2
    )

    print("\n" + "=" * 70)
    print("             PREPARING PAPER SELL")
    print("=" * 70)

    print(
        "Symbol   :",
        symbol
    )

    print(
        "Side     : SELL"
    )

    print(
        "Quantity :",
        quantity
    )

    print(
        "Limit    : $%.2f"
        % exit_price
    )

    print(
        "Reason   :",
        reason
    )

    try:

        order_request = LimitOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=exit_price
        )

        order = trading_client.submit_order(
            order_request
        )

        print("\n" + "=" * 70)
        print("             PAPER SELL SUBMITTED")
        print("=" * 70)

        print(
            "Order ID :",
            order.id
        )

        print(
            "Status   :",
            order.status
        )

        return wait_for_exit_fill(
            order.id,
            symbol,
            entry_price,
            quantity,
            reason
        )

    except Exception as e:

        print(
            "\nSELL ORDER ERROR:"
        )

        print(e)

        return False


# ============================================================
# MAIN MONITOR
# ============================================================

print("\n")
print("Searching for open PAPER position...")
print("-" * 70)


while True:

    # ========================================================
    # AUTOMATICALLY FIND POSITION
    # ========================================================

    position = get_open_option_position()

    if position is None:

        print(
            "\nNo open SPY option position found."
        )

        print(
            "Waiting for an open position..."
        )

        time.sleep(
            CHECK_INTERVAL
        )

        continue


    # ========================================================
    # GET POSITION DATA
    # ========================================================

    symbol = str(
        position.symbol
    )

    quantity = float(
        position.qty
    )

    entry_price = float(
        position.avg_entry_price
    )


    # ========================================================
    # CALCULATE DYNAMIC RISK LEVELS
    # ========================================================

    stop_loss = (
        entry_price
        * (1 - STOP_LOSS_PERCENT / 100)
    )

    take_profit = (
        entry_price
        * (1 + TAKE_PROFIT_PERCENT / 100)
    )


    # ========================================================
    # GET CURRENT QUOTE
    # ========================================================

    bid, ask = get_option_quote(
        symbol
    )


    print("\n" + "-" * 70)

    print(
        "Time        :",
        time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        "Symbol      :",
        symbol
    )

    print(
        "Quantity    :",
        quantity
    )

    print(
        "Entry Price : $%.2f"
        % entry_price
    )

    print(
        "Stop Loss   : $%.2f"
        % stop_loss
    )

    print(
        "Take Profit : $%.2f"
        % take_profit
    )


    # ========================================================
    # QUOTE CHECK
    # ========================================================

    if bid is None and ask is None:

        print(
            "Current Quote: UNAVAILABLE"
        )

        time.sleep(
            CHECK_INTERVAL
        )

        continue


    # ========================================================
    # CURRENT PRICE
    # ========================================================

    if bid is not None and ask is not None:

        current_price = (
            bid + ask
        ) / 2

    elif bid is not None:

        current_price = bid

    else:

        current_price = ask


    print(
        "Bid         : $%.2f"
        % bid
        if bid is not None
        else "Bid         : N/A"
    )

    print(
        "Ask         : $%.2f"
        % ask
        if ask is not None
        else "Ask         : N/A"
    )

    print(
        "Mid         : $%.2f"
        % current_price
    )


    # ========================================================
    # P&L
    # ========================================================

    pnl, pnl_percent = calculate_pnl(
        entry_price,
        current_price,
        quantity
    )

    print(
        "P&L         : $%.2f"
        % pnl
    )

    print(
        "P&L %%       : %.2f%%"
        % pnl_percent
    )


    # ========================================================
    # STOP LOSS
    # ========================================================

    if current_price <= stop_loss:

        print("\n" + "=" * 70)
        print("             STOP LOSS SIGNAL")
        print("=" * 70)

        print(
            "Current Price : $%.2f"
            % current_price
        )

        print(
            "Stop Loss     : $%.2f"
            % stop_loss
        )

        print(
            "Estimated P&L : $%.2f"
            % pnl
        )

        if AUTO_EXIT:

            success = place_exit_order(
                symbol,
                quantity,
                bid,
                entry_price,
                "STOP LOSS"
            )

            if success:

                print(
                    "\nSTOP LOSS EXIT COMPLETED."
                )

            else:

                print(
                    "\nSTOP LOSS EXIT FAILED."
                )

            break

        else:

            print(
                "\nAUTO EXIT DISABLED."
            )

    # ========================================================
    # TAKE PROFIT
    # ========================================================

    if current_price >= take_profit:

        print("\n" + "=" * 70)
        print("             TAKE PROFIT SIGNAL")
        print("=" * 70)

        print(
            "Current Price : $%.2f"
            % current_price
        )

        print(
            "Take Profit   : $%.2f"
            % take_profit
        )

        print(
            "Estimated P&L : $%.2f"
            % pnl
        )

        if AUTO_EXIT:

            success = place_exit_order(
                symbol,
                quantity,
                bid,
                entry_price,
                "TAKE PROFIT"
            )

            if success:

                print(
                    "\nTAKE PROFIT EXIT COMPLETED."
                )

            else:

                print(
                    "\nTAKE PROFIT EXIT FAILED."
                )

            break

        else:

            print(
                "\nAUTO EXIT DISABLED."
            )


    # ========================================================
    # POSITION STATUS
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


    time.sleep(
        CHECK_INTERVAL
    )


# ============================================================
# END
# ============================================================

print("\n" + "=" * 70)
print("          POSITION MONITOR COMPLETE")
print("=" * 70)