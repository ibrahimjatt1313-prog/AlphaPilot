
import os
import csv


# ============================================================
# ALPHAPILOT AI - PERFORMANCE ANALYZER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

LOG_FILE = os.path.join(
    BASE_DIR,
    "logs",
    "trades.csv"
)


# ============================================================
# LOAD TRADES
# ============================================================

def load_trades():

    if not os.path.exists(LOG_FILE):

        print("\nERROR: Trade log not found.")
        print("Expected file:")
        print(LOG_FILE)

        return []

    try:

        with open(
            LOG_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            trades = list(reader)

            return trades

    except Exception as e:

        print("\nERROR reading trade log:")
        print(e)

        return []


# ============================================================
# ANALYZE PERFORMANCE
# ============================================================

def analyze_performance(trades):

    if not trades:

        return None


    total_trades = len(trades)

    winning_trades = 0
    losing_trades = 0

    total_pnl = 0.0

    profits = []
    losses = []


    best_trade = None
    worst_trade = None


    for trade in trades:

        try:

            pnl = float(
                trade["pnl"]
            )

        except Exception:

            continue


        total_pnl += pnl


        # ----------------------------------------------------
        # WIN / LOSS
        # ----------------------------------------------------

        if pnl > 0:

            winning_trades += 1

            profits.append(pnl)

        elif pnl < 0:

            losing_trades += 1

            losses.append(pnl)


        # ----------------------------------------------------
        # BEST TRADE
        # ----------------------------------------------------

        if (
            best_trade is None
            or pnl > float(best_trade["pnl"])
        ):

            best_trade = trade


        # ----------------------------------------------------
        # WORST TRADE
        # ----------------------------------------------------

        if (
            worst_trade is None
            or pnl < float(worst_trade["pnl"])
        ):

            worst_trade = trade


    # ========================================================
    # WIN RATE
    # ========================================================

    if total_trades > 0:

        win_rate = (
            winning_trades
            / total_trades
        ) * 100

    else:

        win_rate = 0


    # ========================================================
    # AVERAGE PROFIT
    # ========================================================

    if profits:

        average_profit = (
            sum(profits)
            / len(profits)
        )

    else:

        average_profit = 0


    # ========================================================
    # AVERAGE LOSS
    # ========================================================

    if losses:

        average_loss = (
            sum(losses)
            / len(losses)
        )

    else:

        average_loss = 0


    # ========================================================
    # PROFIT FACTOR
    # ========================================================

    gross_profit = sum(profits)

    gross_loss = abs(
        sum(losses)
    )


    if gross_loss > 0:

        profit_factor = (
            gross_profit
            / gross_loss
        )

    else:

        profit_factor = 0


    return {

        "total_trades": total_trades,

        "winning_trades": winning_trades,

        "losing_trades": losing_trades,

        "win_rate": win_rate,

        "total_pnl": total_pnl,

        "average_profit": average_profit,

        "average_loss": average_loss,

        "profit_factor": profit_factor,

        "best_trade": best_trade,

        "worst_trade": worst_trade
    }


# ============================================================
# DISPLAY PERFORMANCE
# ============================================================

def display_performance(stats):

    print("\n" + "=" * 70)
    print("             ALPHAPILOT AI PERFORMANCE")
    print("=" * 70)


    print(
        "\nTotal Trades     :",
        stats["total_trades"]
    )

    print(
        "Winning Trades   :",
        stats["winning_trades"]
    )

    print(
        "Losing Trades    :",
        stats["losing_trades"]
    )

    print(
        "Win Rate         : %.2f%%"
        % stats["win_rate"]
    )


    print("\n" + "-" * 70)


    print(
        "Total P&L        : $%.2f"
        % stats["total_pnl"]
    )

    print(
        "Average Profit   : $%.2f"
        % stats["average_profit"]
    )

    print(
        "Average Loss     : $%.2f"
        % stats["average_loss"]
    )

    print(
        "Profit Factor    : %.2f"
        % stats["profit_factor"]
    )


    print("\n" + "-" * 70)


    # ========================================================
    # BEST TRADE
    # ========================================================

    best = stats["best_trade"]

    if best is not None:

        print(
            "Best Trade       :",
            best["symbol"]
        )

        print(
            "Best Trade P&L   : $%.2f"
            % float(best["pnl"])
        )

        print(
            "Best Trade Reason:",
           best.get("reason", best.get("Reason", "N/A"))
        )


    # ========================================================
    # WORST TRADE
    # ========================================================

    worst = stats["worst_trade"]

    if worst is not None:

        print(
            "\nWorst Trade      :",
            worst["symbol"]
        )

        print(
            "Worst Trade P&L  : $%.2f"
            % float(worst["pnl"])
        )

        print(
            "Worst Trade Reason:",
            worst.get("reason", worst.get("Reason", "N/A"))
        )


    print("\n" + "=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("             ALPHAPILOT AI PERFORMANCE")
    print("=" * 70)

    print("\nReading trade history...")

    trades = load_trades()


    print(
        "Trades Loaded     :",
        len(trades)
    )


    if not trades:

        print(
            "\nNo completed trades available."
        )

        print(
            "Performance analysis cannot be calculated yet."
        )

    else:

        stats = analyze_performance(
            trades
        )

        if stats is not None:

            display_performance(
                stats
            )


    print("\nPerformance analysis complete.")

