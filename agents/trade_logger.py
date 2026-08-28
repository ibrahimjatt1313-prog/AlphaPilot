
import os
import csv
from datetime import datetime


# ============================================================
# ALPHAPILOT AI - TRADE LOGGER
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = os.path.join(
    BASE_DIR,
    "logs"
)

LOG_FILE = os.path.join(
    LOG_DIR,
    "trades.csv"
)


# ============================================================
# CREATE LOG DIRECTORY
# ============================================================

def ensure_log_directory():

    if not os.path.exists(LOG_DIR):

        os.makedirs(LOG_DIR)


# ============================================================
# CREATE CSV FILE
# ============================================================

def ensure_log_file():

    ensure_log_directory()

    if not os.path.exists(LOG_FILE):

        with open(
            LOG_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "trade_id",
                "symbol",
                "quantity",
                "entry_price",
                "exit_price",
                "pnl",
                "pnl_percent",
                "entry_time",
                "exit_time",
                "reason"
            ])


# ============================================================
# LOG TRADE
# ============================================================

def log_trade(
    symbol,
    quantity,
    entry_price,
    exit_price,
    entry_time,
    exit_time,
    reason
):

    try:

        ensure_log_file()

        quantity = float(quantity)
        entry_price = float(entry_price)
        exit_price = float(exit_price)

        multiplier = 100

        pnl = (
            exit_price
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


        trade_id = datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )


        with open(
            LOG_FILE,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([

                trade_id,

                symbol,

                quantity,

                round(entry_price, 2),

                round(exit_price, 2),

                round(pnl, 2),

                round(pnl_percent, 2),

                entry_time,

                exit_time,

                reason
            ])


        print("\n" + "=" * 70)
        print("             TRADE LOGGED")
        print("=" * 70)

        print("Trade ID    :", trade_id)
        print("Symbol      :", symbol)
        print("Quantity    :", quantity)
        print("Entry Price : $%.2f" % entry_price)
        print("Exit Price  : $%.2f" % exit_price)
        print("P&L         : $%.2f" % pnl)
        print("P&L %%       : %.2f%%" % pnl_percent)
        print("Reason      :", reason)
        print("Log File    :", LOG_FILE)

        print("=" * 70)

        return True


    except Exception as e:

        print("\nERROR writing trade log:")
        print(e)

        return False


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("             ALPHAPILOT AI TRADE LOGGER")
    print("=" * 70)

    print("\nTesting trade logger...")

    success = log_trade(

        symbol="TEST_OPTION",

        quantity=1,

        entry_price=4.84,

        exit_price=5.50,

        entry_time=datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        exit_time=datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        reason="TEST TRADE"
    )


    if success:

        print("\nTrade logger test SUCCESSFUL.")

        print(
            "\nCSV location:"
        )

        print(LOG_FILE)

    else:

        print(
            "\nTrade logger test FAILED."
        )

    print("\n" + "=" * 70)
