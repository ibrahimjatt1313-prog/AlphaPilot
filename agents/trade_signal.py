
import os
from datetime import datetime

from dotenv import load_dotenv

from ai_decision import (
    get_live_quote,
    get_historical_bars,
    analyze_market
)

from option_selector import (
    get_spy_price,
    get_option_contracts,
    select_contracts
)


# ============================================================
# ALPHAPILOT AI - TRADE SIGNAL ENGINE
# ============================================================

load_dotenv()


# ============================================================
# SETTINGS
# ============================================================

SYMBOL = "SPY"

MIN_CONFIDENCE = 70


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             ALPHAPILOT AI TRADE SIGNAL")
print("=" * 70)

print()
print("Mode              : PAPER TRADING")
print("Underlying        :", SYMBOL)
print("Minimum Confidence:", str(MIN_CONFIDENCE) + "%")


# ============================================================
# GET TECHNICAL DECISION
# ============================================================

def get_technical_signal():

    quote = get_live_quote()

    if quote["mid"] is None:

        return {
            "ready": False,
            "decision": "NO TRADE",
            "confidence": 0,
            "reason": "Live SPY price unavailable."
        }

    bars = get_historical_bars()

    analysis = analyze_market(
        bars,
        quote["mid"]
    )

    if not analysis["ready"]:

        return {
            "ready": False,
            "decision": "NO TRADE",
            "confidence": 0,
            "reason": analysis["reason"]
        }

    return {
        "ready": True,
        "decision": analysis["decision"],
        "confidence": analysis["confidence"],
        "reasons": analysis["reasons"],
        "price": analysis["price"],
        "sma20": analysis["sma20"],
        "sma50": analysis["sma50"],
        "rsi14": analysis["rsi14"],
        "macd": analysis["macd"],
        "macd_signal": analysis["macd_signal"],
        "macd_histogram": analysis["macd_histogram"],
        "current_volume": analysis["current_volume"],
        "average_volume": analysis["average_volume"]
    }


# ============================================================
# GET BEST OPTION
# ============================================================

def get_best_option():

    spy_price = get_spy_price()

    if spy_price is None:

        return None

    contracts = get_option_contracts()

    if not contracts:

        return None

    selected = select_contracts(
        contracts,
        spy_price
    )

    if not selected:

        return None

    return selected[0]


# ============================================================
# CREATE FINAL TRADE SIGNAL
# ============================================================

def create_trade_signal():

    technical = get_technical_signal()

    if not technical["ready"]:

        return {
            "symbol": SYMBOL,
            "decision": "NO TRADE",
            "confidence": 0,
            "option": None,
            "reason": technical["reason"],
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }


    # --------------------------------------------------------
    # Technical decision must be BUY
    # --------------------------------------------------------

    if technical["decision"] != "BUY":

        return {
            "symbol": SYMBOL,
            "decision": "NO TRADE",
            "confidence": technical["confidence"],
            "option": None,
            "reason": (
                "Technical conditions do not meet "
                "the BUY requirement."
            ),
            "reasons": technical["reasons"],
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }


    # --------------------------------------------------------
    # Confidence check
    # --------------------------------------------------------

    if technical["confidence"] < MIN_CONFIDENCE:

        return {
            "symbol": SYMBOL,
            "decision": "NO TRADE",
            "confidence": technical["confidence"],
            "option": None,
            "reason": (
                "Confidence below minimum requirement."
            ),
            "reasons": technical["reasons"],
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }


    # --------------------------------------------------------
    # Find best option
    # --------------------------------------------------------

    option = get_best_option()

    if option is None:

        return {
            "symbol": SYMBOL,
            "decision": "NO TRADE",
            "confidence": technical["confidence"],
            "option": None,
            "reason": (
                "No suitable CALL option found."
            ),
            "reasons": technical["reasons"],
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }


    # --------------------------------------------------------
    # Final BUY signal
    # --------------------------------------------------------

    return {
        "symbol": SYMBOL,

        "decision": "BUY",

        "confidence": technical["confidence"],

        "reason": (
            "Technical BUY conditions passed "
            "and suitable option was found."
        ),

        "reasons": technical["reasons"],

        "option": option,

        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("             TECHNICAL SIGNAL")
    print("=" * 70)


    signal = create_trade_signal()


    # ========================================================
    # DISPLAY SIGNAL
    # ========================================================

    print()

    print(
        "Symbol     :",
        signal["symbol"]
    )

    print(
        "Decision   :",
        signal["decision"]
    )

    print(
        "Confidence :",
        str(signal["confidence"]) + "%"
    )

    print(
        "Reason     :",
        signal["reason"]
    )


    # ========================================================
    # REASONS
    # ========================================================

    if signal.get("reasons"):

        print()

        print("Reasons:")

        for reason in signal["reasons"]:

            print(
                " -",
                reason
            )


    # ========================================================
    # OPTION
    # ========================================================

    option = signal.get("option")


    if option is not None:

        print("\n" + "=" * 70)
        print("             SELECTED OPTION")
        print("=" * 70)

        print(
            "Symbol        :",
            option["symbol"]
        )

        print(
            "Strike        : $%.2f"
            % option["strike"]
        )

        print(
            "Expiration    :",
            option["expiration"]
        )

        print(
            "Distance      : $%.2f"
            % option["distance"]
        )

        print(
            "Open Interest :",
            int(option["open_interest"])
        )

        print(
            "Selection Score:",
            option["score"]
        )


    # ========================================================
    # FINAL ACTION
    # ========================================================

    print("\n" + "=" * 70)
    print("             FINAL SIGNAL")
    print("=" * 70)


    if signal["decision"] == "BUY":

        print("BUY SIGNAL READY")

        print(
            "Confidence:",
            str(signal["confidence"]) + "%"
        )

        if option is not None:

            print(
                "Option:",
                option["symbol"]
            )

        print()
        print(
            "NO ORDER IS PLACED BY THIS MODULE."
        )

    else:

        print("NO TRADE")

        print(
            "No order will be placed."
        )


    # ========================================================
    # TIMESTAMP
    # ========================================================

    print()

    print(
        "Timestamp  :",
        signal["timestamp"]
    )

    print("=" * 70)

    print(
        "\nTrade signal test complete."
    )
