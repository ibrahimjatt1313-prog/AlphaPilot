# ============================================================
# ALPHAPILOT AI - DECISION ENGINE
# ============================================================

import sys
import os

# Allow Python to find our project folders
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from strategies.signal_engine import analyze_symbol
from options.contract_selector import (
    get_current_price,
    select_contracts,
    options_client,
    OptionChainRequest,
    UNDERLYING
)
from options.risk_manager import (
    calculate_contract_quantity,
    risk_gate
)


# ============================================================
# SETTINGS
# ============================================================

SYMBOLS = [
    "SPY",
    "QQQ",
    "NVDA",
    "AAPL",
    "TSLA"
]

ACCOUNT_SIZE = 100_000


# ============================================================
# ANALYZE ONE SYMBOL
# ============================================================

def analyze_stock(symbol):

    print("\n" + "-" * 70)
    print(f"ANALYZING: {symbol}")
    print("-" * 70)

    # --------------------------------------------------------
    # STEP 1: SIGNAL
    # --------------------------------------------------------

    try:

        signal = analyze_symbol(symbol)

    except Exception as e:

        print("Signal error:", e)

        return None

    if not signal:

        print("No market data available.")

        return None

    direction = signal["signal"]

    print(
        f"Price      : ${signal['price']:.2f}"
    )

    print(
        f"SMA20      : {signal['sma20']:.2f}"
    )

    print(
        f"SMA50      : {signal['sma50']:.2f}"
    )

    print(
        f"Momentum   : {signal['momentum']:.2f}%"
    )

    print(
        f"Volatility : {signal['volatility']:.2f}%"
    )

    print(
        f"AI Signal  : {direction}"
    )

    # --------------------------------------------------------
    # NO TRADE
    # --------------------------------------------------------

    if direction == "NO TRADE":

        print("Decision   : NO TRADE")

        return {
            "symbol": symbol,
            "signal": direction,
            "decision": "NO TRADE"
        }

    # --------------------------------------------------------
    # STEP 2: GET OPTION CHAIN
    # --------------------------------------------------------

    print("\nGetting options chain...")

    try:

        request = OptionChainRequest(
            underlying_symbol=symbol
        )

        chain = options_client.get_option_chain(
            request
        )

        print(
            f"Contracts received: {len(chain)}"
        )

    except Exception as e:

        print("Options error:", e)

        return None

    # --------------------------------------------------------
    # STEP 3: CURRENT PRICE
    # --------------------------------------------------------

    try:

        current_price = get_current_price(
            symbol
        )

    except Exception as e:

        print("Price error:", e)

        return None

    # --------------------------------------------------------
    # STEP 4: SELECT OPTIONS
    # --------------------------------------------------------

    candidates = select_contracts(
        chain,
        current_price,
        direction
    )

    if not candidates:

        print("No suitable option found.")

        return {
            "symbol": symbol,
            "signal": direction,
            "decision": "NO TRADE"
        }

    # Best candidate
    best = candidates[0]

    print("\nBEST OPTION CANDIDATE")
    print("---------------------")

    print(
        f"Contract : {best['symbol']}"
    )

    print(
        f"Type     : {best['type']}"
    )

    print(
        f"Strike   : ${best['strike']:.2f}"
    )

    print(
        f"Bid      : ${best['bid']:.2f}"
    )

    print(
        f"Ask      : ${best['ask']:.2f}"
    )

    print(
        f"Spread   : {best['spread']:.2f}%"
    )

    print(
        f"Delta    : {best['delta']:.4f}"
    )

    if best["iv"] is not None:

        print(
            f"IV       : {best['iv']:.2%}"
        )

    print(
        f"Score    : {best['score']}"
    )

    # --------------------------------------------------------
    # STEP 5: POSITION SIZE
    # --------------------------------------------------------

    # Use ask price because that is approximately
    # what a buyer may pay.

    option_price = best["ask"]

    quantity = calculate_contract_quantity(
        option_price,
        ACCOUNT_SIZE
    )

    print(
        f"\nSuggested Quantity: {quantity}"
    )

    # --------------------------------------------------------
    # STEP 6: RISK GATE
    # --------------------------------------------------------

    risk_result = risk_gate(
        option_price,
        quantity,
        ACCOUNT_SIZE
    )

    print("\nRISK GATE")
    print("---------")

    print(
        "Approved:",
        risk_result["approved"]
    )

    print(
        "Reason:",
        risk_result["reason"]
    )

    # --------------------------------------------------------
    # STEP 7: FINAL DECISION
    # --------------------------------------------------------

    if not risk_result["approved"]:

        print("\nFINAL DECISION: NO TRADE")

        return {
            "symbol": symbol,
            "signal": direction,
            "decision": "NO TRADE",
            "reason": risk_result["reason"]
        }

    print("\nFINAL DECISION: TRADE CANDIDATE")

    print(
        f"Contracts : {quantity}"
    )

    print(
        f"Estimated Cost : "
        f"${risk_result['total_cost']:,.2f}"
    )

    print(
        f"Estimated Risk : "
        f"${risk_result['total_risk']:,.2f}"
    )

    print(
        f"Stop Loss : "
        f"${risk_result['stop_loss']:.2f}"
    )

    print(
        f"Take Profit : "
        f"${risk_result['take_profit']:.2f}"
    )

    return {

        "symbol": symbol,

        "signal": direction,

        "decision": "TRADE CANDIDATE",

        "contract": best["symbol"],

        "option_type": best["type"],

        "strike": best["strike"],

        "bid": best["bid"],

        "ask": best["ask"],

        "delta": best["delta"],

        "iv": best["iv"],

        "score": best["score"],

        "quantity": quantity,

        "total_cost": risk_result["total_cost"],

        "total_risk": risk_result["total_risk"],

        "stop_loss": risk_result["stop_loss"],

        "take_profit": risk_result["take_profit"],

        "risk_reward": risk_result["risk_reward"]
    }


# ============================================================
# MAIN AI SCANNER
# ============================================================

def run_alpha_pilot():

    print("\n")
    print("=" * 70)
    print("                 ALPHAPILOT AI")
    print("              AUTONOMOUS DECISION ENGINE")
    print("=" * 70)

    print(
        f"\nAccount Size: ${ACCOUNT_SIZE:,.2f}"
    )

    print(
        "\nStarting autonomous market analysis..."
    )

    results = []

    # --------------------------------------------------------
    # Analyze every stock
    # --------------------------------------------------------

    for symbol in SYMBOLS:

        try:

            result = analyze_stock(
                symbol
            )

            if result:

                results.append(result)

        except Exception as e:

            print(
                f"\n{symbol} failed:"
            )

            print(e)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n\n")
    print("=" * 70)
    print("                 ALPHAPILOT SUMMARY")
    print("=" * 70)

    trade_candidates = []

    for result in results:

        print(
            f"\n{result['symbol']}"
        )

        print(
            f"Signal   : {result['signal']}"
        )

        print(
            f"Decision : {result['decision']}"
        )

        if result["decision"] == "TRADE CANDIDATE":

            print(
                f"Option   : {result['contract']}"
            )

            print(
                f"Quantity : {result['quantity']}"
            )

            trade_candidates.append(
                result
            )

    # --------------------------------------------------------
    # BEST FINAL CANDIDATE
    # --------------------------------------------------------

    if trade_candidates:

        trade_candidates.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        best_trade = trade_candidates[0]

        print("\n")
        print("=" * 70)
        print("             BEST AI TRADE CANDIDATE")
        print("=" * 70)

        print(
            f"\nSymbol       : "
            f"{best_trade['symbol']}"
        )

        print(
            f"Signal       : "
            f"{best_trade['signal']}"
        )

        print(
            f"Option       : "
            f"{best_trade['contract']}"
        )

        print(
            f"Quantity     : "
            f"{best_trade['quantity']}"
        )

        print(
            f"Estimated Cost: "
            f"${best_trade['total_cost']:,.2f}"
        )

        print(
            f"Estimated Risk: "
            f"${best_trade['total_risk']:,.2f}"
        )

        print(
            f"Stop Loss    : "
            f"${best_trade['stop_loss']:.2f}"
        )

        print(
            f"Take Profit  : "
            f"${best_trade['take_profit']:.2f}"
        )

        print(
            f"Risk/Reward  : "
            f"{best_trade['risk_reward']:.2f}"
        )

        print("\nAI STATUS: READY FOR EXECUTION")

    else:

        print("\n")
        print("=" * 70)
        print("             AI DECISION: NO TRADE")
        print("=" * 70)

        print(
            "\nNo candidate passed all filters."
        )

    # ========================================================
    # SAFETY MESSAGE
    # ========================================================

    print("\n")
    print("=" * 70)
    print("IMPORTANT: NO ORDER WAS PLACED")
    print("=" * 70)

    return results


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    run_alpha_pilot()