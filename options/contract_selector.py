import os
from datetime import datetime

from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical import OptionHistoricalDataClient

from alpaca.data.requests import (
    StockLatestQuoteRequest,
    OptionChainRequest
)


# ============================================================
# 1. LOAD ALPACA CREDENTIALS
# ============================================================

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise RuntimeError(
        "ERROR: Alpaca API keys not found in .env"
    )


# ============================================================
# 2. CONNECT TO ALPACA
# ============================================================

stock_client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)

options_client = OptionHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)


# ============================================================
# 3. SETTINGS
# ============================================================

UNDERLYING = "SPY"

MIN_DELTA = 0.30
MAX_DELTA = 0.70

MAX_SPREAD_PERCENT = 10.0

TOP_CANDIDATES = 10

# Prefer options that are reasonably close to expiry,
# but avoid extremely short-dated contracts.
MIN_DTE = 2
MAX_DTE = 21


# ============================================================
# 4. CURRENT STOCK PRICE
# ============================================================

def get_current_price(symbol):

    request = StockLatestQuoteRequest(
        symbol_or_symbols=symbol
    )

    quotes = stock_client.get_stock_latest_quote(
        request
    )

    quote = quotes[symbol]

    bid = quote.bid_price
    ask = quote.ask_price

    if bid is not None and ask is not None:
        return (bid + ask) / 2

    if ask is not None:
        return ask

    return bid


# ============================================================
# 5. BID / ASK SPREAD
# ============================================================

def calculate_spread_percent(bid, ask):

    if bid is None or ask is None:
        return None

    if ask <= 0:
        return None

    midpoint = (bid + ask) / 2

    if midpoint <= 0:
        return None

    return ((ask - bid) / midpoint) * 100


# ============================================================
# 6. OPTION TYPE
# ============================================================

def get_option_type(symbol):

    # OCC option format:
    #
    # SPY260831C00772000
    #          ^
    #          C = Call
    #          P = Put

    if len(symbol) < 10:
        return "UNKNOWN"

    option_marker = symbol[-9]

    if option_marker == "C":
        return "CALL"

    if option_marker == "P":
        return "PUT"

    return "UNKNOWN"


# ============================================================
# 7. STRIKE
# ============================================================

def get_strike(symbol):

    try:

        strike_part = symbol[-8:]

        return int(strike_part) / 1000

    except Exception:

        return None


# ============================================================
# 8. EXPIRATION DATE
# ============================================================

def get_expiration(symbol):

    try:

        # OCC format:
        #
        # SPY260831C00772000
        #     260831
        #     YYMMDD

        date_part = symbol[-15:-9]

        return datetime.strptime(
            date_part,
            "%y%m%d"
        ).date()

    except Exception:

        return None


# ============================================================
# 9. DTE
# ============================================================

def get_dte(symbol):

    expiration = get_expiration(symbol)

    if expiration is None:
        return None

    today = datetime.now().date()

    return (
        expiration - today
    ).days


# ============================================================
# 10. NORMALIZED SCORE HELPER
# ============================================================

def clamp(value, minimum=0.0, maximum=1.0):

    return max(
        minimum,
        min(value, maximum)
    )


# ============================================================
# 11. STRIKE SCORE
# ============================================================

def calculate_strike_score(
    strike,
    underlying_price
):

    if strike is None:
        return 0

    distance = abs(
        strike - underlying_price
    ) / underlying_price

    distance_percent = distance * 100

    # 0% distance = 100 score
    #
    # Score gradually decreases as strike
    # moves away from underlying price.

    score = 100 - (
        distance_percent * 20
    )

    return clamp(
        score / 100
    ) * 100


# ============================================================
# 12. DELTA SCORE
# ============================================================

def calculate_delta_score(delta):

    if delta is None:
        return 0

    delta = abs(delta)

    # Ideal target around 0.50 delta.
    #
    # This gives a smooth score instead of
    # simply giving everyone 30 points.

    distance = abs(
        delta - 0.50
    )

    score = 100 - (
        distance * 250
    )

    return clamp(
        score / 100
    ) * 100


# ============================================================
# 13. SPREAD SCORE
# ============================================================

def calculate_spread_score(
    spread_percent
):

    if spread_percent is None:
        return 0

    if spread_percent >= MAX_SPREAD_PERCENT:
        return 0

    # Smaller spread = better score.

    score = 100 - (
        spread_percent
        / MAX_SPREAD_PERCENT
        * 100
    )

    return clamp(
        score / 100
    ) * 100


# ============================================================
# 14. IV SCORE
# ============================================================

def calculate_iv_score(iv):

    if iv is None:
        return 50


    if iv <= 0.20:
        return 100

    if iv <= 0.40:
        return 90

    if iv <= 0.60:
        return 75

    if iv <= 0.80:
        return 60

    if iv <= 1.00:
        return 45

    return 30


# ============================================================
# 15. DTE SCORE
# ============================================================

def calculate_dte_score(dte):

    if dte is None:
        return 50

    # Prefer roughly 7-14 DTE for this strategy.

    if 7 <= dte <= 14:
        return 100

    if 5 <= dte <= 16:
        return 90

    if 3 <= dte <= 21:
        return 75

    if dte >= 2:
        return 50

    return 0


# ============================================================
# 16. FINAL CONTRACT SCORE
# ============================================================

def score_contract(
    option_type,
    strike,
    underlying_price,
    bid,
    ask,
    iv,
    delta,
    dte
):

    # --------------------------------------------------------
    # Individual scores
    # --------------------------------------------------------

    strike_score = calculate_strike_score(
        strike,
        underlying_price
    )

    delta_score = calculate_delta_score(
        delta
    )

    spread_percent = calculate_spread_percent(
        bid,
        ask
    )

    spread_score = calculate_spread_score(
        spread_percent
    )

    iv_score = calculate_iv_score(
        iv
    )

    dte_score = calculate_dte_score(
        dte
    )

    # --------------------------------------------------------
    # Weighted score
    # --------------------------------------------------------
    #
    # Delta       = 30%
    # Spread      = 25%
    # Strike      = 20%
    # DTE         = 15%
    # IV          = 10%
    #
    # Total       = 100%
    #

    final_score = (

        delta_score * 0.30

        + spread_score * 0.25

        + strike_score * 0.20

        + dte_score * 0.15

        + iv_score * 0.10
    )

    return round(
        final_score,
        2
    )


# ============================================================
# 17. SELECT CONTRACTS
# ============================================================

def select_contracts(
    chain,
    underlying_price,
    direction
):

    candidates = []

    for contract_symbol, snapshot in chain.items():

        try:

            # ------------------------------------------------
            # OPTION TYPE
            # ------------------------------------------------

            option_type = get_option_type(
                contract_symbol
            )

            if (
                direction == "BULLISH"
                and option_type != "CALL"
            ):
                continue

            if (
                direction == "BEARISH"
                and option_type != "PUT"
            ):
                continue

            # ------------------------------------------------
            # QUOTE
            # ------------------------------------------------

            if not snapshot.latest_quote:
                continue

            bid = snapshot.latest_quote.bid_price
            ask = snapshot.latest_quote.ask_price

            if bid is None or ask is None:
                continue

            if bid <= 0 or ask <= 0:
                continue

            # ------------------------------------------------
            # SPREAD
            # ------------------------------------------------

            spread_percent = calculate_spread_percent(
                bid,
                ask
            )

            if spread_percent is None:
                continue

            if spread_percent > MAX_SPREAD_PERCENT:
                continue

            # ------------------------------------------------
            # STRIKE
            # ------------------------------------------------

            strike = get_strike(
                contract_symbol
            )

            if strike is None:
                continue

            # ------------------------------------------------
            # DTE
            # ------------------------------------------------

            dte = get_dte(
                contract_symbol
            )

            if dte is None:
                continue

            if dte < MIN_DTE:
                continue

            if dte > MAX_DTE:
                continue

            # ------------------------------------------------
            # GREEKS
            # ------------------------------------------------

            if not snapshot.greeks:
                continue

            delta = snapshot.greeks.delta

            if delta is None:
                continue

            abs_delta = abs(delta)

            if not (
                MIN_DELTA
                <= abs_delta
                <= MAX_DELTA
            ):
                continue

            # ------------------------------------------------
            # IV
            # ------------------------------------------------

            iv = snapshot.implied_volatility

            # ------------------------------------------------
            # SCORE
            # ------------------------------------------------

            score = score_contract(

                option_type,

                strike,

                underlying_price,

                bid,

                ask,

                iv,

                delta,

                dte
            )

            candidates.append({

                "symbol": contract_symbol,

                "type": option_type,

                "strike": strike,

                "bid": bid,

                "ask": ask,

                "spread": spread_percent,

                "iv": iv,

                "delta": delta,

                "dte": dte,

                "score": score
            })

        except Exception:

            continue

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: (
            x["score"],
            -x["spread"]
        ),
        reverse=True
    )

    return candidates[:TOP_CANDIDATES]


# ============================================================
# 18. TEST / DEMO
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("             ALPHAPILOT SMART OPTIONS SELECTOR")
    print("=" * 70)

    print(
        f"\nUnderlying: {UNDERLYING}"
    )

    # --------------------------------------------------------
    # Current price
    # --------------------------------------------------------

    try:

        current_price = get_current_price(
            UNDERLYING
        )

        print(
            f"Current Price: ${current_price:.2f}"
        )

    except Exception as e:

        print(
            "\nERROR getting stock price:"
        )

        print(e)

        raise SystemExit

    # --------------------------------------------------------
    # Test direction
    # --------------------------------------------------------

    direction = "BULLISH"

    print(
        f"Strategy Direction: {direction}"
    )

    print(
        "\nDownloading option chain..."
    )

    # --------------------------------------------------------
    # Option chain
    # --------------------------------------------------------

    try:

        request = OptionChainRequest(
            underlying_symbol=UNDERLYING
        )

        chain = options_client.get_option_chain(
            request
        )

        print(
            f"Contracts received: {len(chain)}"
        )

    except Exception as e:

        print(
            "\nERROR getting option chain:"
        )

        print(e)

        raise SystemExit

    # --------------------------------------------------------
    # Select
    # --------------------------------------------------------

    print(
        "\nFiltering contracts..."
    )

    candidates = select_contracts(
        chain,
        current_price,
        direction
    )

    # ========================================================
    # RESULTS
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "                TOP OPTION CANDIDATES"
    )

    print(
        "=" * 70
    )

    if not candidates:

        print(
            "\nNo suitable contracts found."
        )

    else:

        for index, option in enumerate(
            candidates,
            start=1
        ):

            print(
                f"\n#{index}"
            )

            print(
                f"Contract : "
                f"{option['symbol']}"
            )

            print(
                f"Type     : "
                f"{option['type']}"
            )

            print(
                f"Strike   : "
                f"${option['strike']:.2f}"
            )

            print(
                f"Bid      : "
                f"${option['bid']:.2f}"
            )

            print(
                f"Ask      : "
                f"${option['ask']:.2f}"
            )

            print(
                f"Spread   : "
                f"{option['spread']:.2f}%"
            )

            print(
                f"DTE      : "
                f"{option['dte']}"
            )

            if option["iv"] is not None:

                print(
                    f"IV       : "
                    f"{option['iv']:.2%}"
                )

            print(
                f"Delta    : "
                f"{option['delta']:.4f}"
            )

            print(
                f"Score    : "
                f"{option['score']:.2f}"
            )

    # ========================================================
    # END
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "          SMART OPTIONS SELECTION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "\nNO ORDER WAS PLACED."
    )

    print(
        "This program only analyzes option contracts."
    )