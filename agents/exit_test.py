import os
from datetime import datetime

from dotenv import load_dotenv

from trade_logger import log_trade


# ============================================================
# ALPHAPILOT AI - SAFE EXIT TEST
# PAPER SIMULATION ONLY
# ============================================================

load_dotenv()

print("=" * 70)
print("             ALPHAPILOT AI EXIT TEST")
print("=" * 70)

print()
print("Mode        : PAPER SIMULATION")
print("Real Order  : DISABLED")
print("Real Position: NOT TOUCHED")
print()


# ============================================================
# SIMULATED TRADE
# ============================================================

SYMBOL = "TEST_EXIT_OPTION"
QUANTITY = 1.0

ENTRY_PRICE = 4.84
EXIT_PRICE = 5.50

REASON = "SIMULATED TAKE PROFIT"


# ============================================================
# CALCULATE P&L
# ============================================================

MULTIPLIER = 100

PNL = (
    EXIT_PRICE - ENTRY_PRICE
) * QUANTITY * MULTIPLIER

INVESTED = (
    ENTRY_PRICE
    * QUANTITY
    * MULTIPLIER
)

PNL_PERCENT = (
    PNL / INVESTED
) * 100


# ============================================================
# DISPLAY
# ============================================================

print("=" * 70)
print("             SIMULATED EXIT")
print("=" * 70)

print("Symbol       :", SYMBOL)
print("Quantity     :", QUANTITY)
print("Entry Price  : $%.2f" % ENTRY_PRICE)
print("Exit Price   : $%.2f" % EXIT_PRICE)
print("P&L          : $%.2f" % PNL)
print("P&L %%        : %.2f%%" % PNL_PERCENT)
print("Reason       :", REASON)


# ============================================================
# LOG SIMULATED TRADE
# ============================================================

print("\nLogging simulated completed trade...")

try:

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    log_trade(
        symbol=SYMBOL,
        quantity=QUANTITY,
        entry_price=ENTRY_PRICE,
        exit_price=EXIT_PRICE,
        entry_time=timestamp,
        exit_time=timestamp,
        reason=REASON
    )

    print()
    print("=" * 70)
    print("             EXIT TEST SUCCESSFUL")
    print("=" * 70)

    print()
    print("Simulated trade logged successfully.")
    print("No Alpaca order was submitted.")
    print("No real/paper position was modified.")

except Exception as e:

    print()
    print("=" * 70)
    print("             EXIT TEST FAILED")
    print("=" * 70)

    print()
    print("Error:")
    print(e)

    raise SystemExit(1)


print()
print("=" * 70)
print("             EXIT TEST COMPLETE")
print("=" * 70)