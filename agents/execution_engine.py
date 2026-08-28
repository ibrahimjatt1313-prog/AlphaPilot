import os

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


# ============================================================
# ALPHAPILOT AI - PAPER EXECUTION ENGINE
# ============================================================

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    print("ERROR: Alpaca API keys not found in .env")
    raise SystemExit


# ============================================================
# CONNECT TO ALPACA PAPER ACCOUNT
# ============================================================

client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=True
)


# ============================================================
# TRADE SETTINGS
# ============================================================

OPTION_SYMBOL = "SPY260904C00772000"

QUANTITY = 3

# Use the current best ask from your selector.
LIMIT_PRICE = 4.85

MAX_TRADE_COST = 5000.00


# ============================================================
# DISPLAY HEADER
# ============================================================

print("=" * 70)
print("              ALPHAPILOT AI EXECUTION ENGINE")
print("=" * 70)

print("\nExecution Mode : PAPER TRADING")
print("Option        :", OPTION_SYMBOL)
print("Quantity      :", QUANTITY)
print("Limit Price   : $%.2f" % LIMIT_PRICE)


# ============================================================
# ACCOUNT CHECK
# ============================================================

try:

    account = client.get_account()

    print("\nAccount Status :", account.status)
    print("Buying Power   : $%s" % account.buying_power)
    print("Portfolio      : $%s" % account.portfolio_value)

except Exception as e:

    print("\nERROR: Could not access Alpaca account.")
    print(e)
    raise SystemExit


# ============================================================
# SAFETY CHECK 1 — PAPER ACCOUNT
# ============================================================

if not account:

    print("\nERROR: Account unavailable.")
    raise SystemExit


# ============================================================
# SAFETY CHECK 2 — QUANTITY
# ============================================================

if QUANTITY <= 0:

    print("\nRISK GATE: REJECTED")
    print("Reason: Quantity must be greater than zero.")

    raise SystemExit


# ============================================================
# SAFETY CHECK 3 — PRICE
# ============================================================

if LIMIT_PRICE <= 0:

    print("\nRISK GATE: REJECTED")
    print("Reason: Invalid option price.")

    raise SystemExit


# ============================================================
# OPTIONS COST
# ============================================================

# One option contract normally represents 100 shares.

estimated_cost = (
    LIMIT_PRICE
    * 100
    * QUANTITY
)

print("\nEstimated Cost : $%.2f" % estimated_cost)


# ============================================================
# SAFETY CHECK 4 — MAX POSITION
# ============================================================

if estimated_cost > MAX_TRADE_COST:

    print("\nRISK GATE: REJECTED")
    print(
        "Reason: Estimated trade cost exceeds "
        "maximum position size."
    )

    print(
        "Maximum allowed: $%.2f"
        % MAX_TRADE_COST
    )

    raise SystemExit


# ============================================================
# FINAL CONFIRMATION
# ============================================================

print("\n" + "-" * 70)
print("                    FINAL RISK GATE")
print("-" * 70)

print("Account       : PAPER")
print("Contract      :", OPTION_SYMBOL)
print("Side          : BUY")
print("Quantity      :", QUANTITY)
print("Limit Price   : $%.2f" % LIMIT_PRICE)
print("Estimated Cost: $%.2f" % estimated_cost)

print("\nRisk Gate: APPROVED")


# ============================================================
# PLACE PAPER OPTIONS ORDER
# ============================================================

print("\nPlacing PAPER order...")

try:

    order_request = LimitOrderRequest(
        symbol=OPTION_SYMBOL,
        qty=QUANTITY,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        limit_price=LIMIT_PRICE
    )

    order = client.submit_order(
        order_data=order_request
    )

    print("\n" + "=" * 70)
    print("                 ORDER SUBMITTED")
    print("=" * 70)

    print("Order ID :", order.id)
    print("Status   :", order.status)
    print("Symbol   :", order.symbol)
    print("Quantity :", order.qty)
    print("Side     :", order.side)

    print("\nALPHAPILOT PAPER ORDER SUCCESSFUL")

except Exception as e:

    print("\n" + "=" * 70)
    print("                  ORDER FAILED")
    print("=" * 70)

    print(e)


# ============================================================
# END
# ============================================================

print("\n" + "=" * 70)
print("             EXECUTION ENGINE COMPLETE")
print("=" * 70)