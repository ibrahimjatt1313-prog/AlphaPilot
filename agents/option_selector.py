import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.trading.enums import ContractType


# ============================================================
# ALPHAPILOT AI - OPTION SELECTOR
# ============================================================

load_dotenv()


# ============================================================
# SETTINGS
# ============================================================

UNDERLYING_SYMBOL = "SPY"

CONTRACT_TYPE = ContractType.CALL

MIN_DAYS_TO_EXPIRY = 7
MAX_DAYS_TO_EXPIRY = 30

MAX_STRIKE_DISTANCE = 15.00

MIN_OPEN_INTEREST = 100

MAX_RESULTS = 10


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
# GET SPY PRICE
# ============================================================

def get_spy_price():

    try:

        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest

        data_client = StockHistoricalDataClient(
            API_KEY,
            SECRET_KEY
        )

        request = StockLatestQuoteRequest(
            symbol_or_symbols=UNDERLYING_SYMBOL,
            feed="iex"
        )

        quotes = data_client.get_stock_latest_quote(
            request
        )

        quote = quotes[UNDERLYING_SYMBOL]

        bid = quote.bid_price
        ask = quote.ask_price

        if bid is not None and ask is not None:

            return (
                float(bid) + float(ask)
            ) / 2

        if bid is not None:
            return float(bid)

        if ask is not None:
            return float(ask)

        return None

    except Exception as e:

        print("\nSPY PRICE ERROR:")
        print(e)

        return None


# ============================================================
# GET OPTION CONTRACTS
# ============================================================

def get_option_contracts():

    try:

        today = datetime.now(
            timezone.utc
        ).date()

        min_expiration = (
            today
            + timedelta(
                days=MIN_DAYS_TO_EXPIRY
            )
        )

        max_expiration = (
            today
            + timedelta(
                days=MAX_DAYS_TO_EXPIRY
            )
        )

        request = GetOptionContractsRequest(

            underlying_symbols=[
                UNDERLYING_SYMBOL
            ],

            type=CONTRACT_TYPE,

            expiration_date_gte=min_expiration,

            expiration_date_lte=max_expiration,

            limit=1000
        )

        response = trading_client.get_option_contracts(
            request
        )

        return list(
            response.option_contracts
        )

    except Exception as e:

        print("\nOPTION CONTRACT ERROR:")
        print(e)

        return []


# ============================================================
# SELECT CONTRACTS
# ============================================================

def select_contracts(
    contracts,
    spy_price
):

    if spy_price is None:
        return []

    selected = []

    for contract in contracts:

        try:

            strike = float(
                contract.strike_price
            )

        except Exception:

            continue


        # ----------------------------------------------------
        # Strike distance
        # ----------------------------------------------------

        distance = abs(
            strike - spy_price
        )

        if distance > MAX_STRIKE_DISTANCE:
            continue


        # ----------------------------------------------------
        # Open interest
        # ----------------------------------------------------

        open_interest = (
            contract.open_interest
        )

        if open_interest is None:

            open_interest = 0

        else:

            open_interest = float(
                open_interest
            )

        if open_interest < MIN_OPEN_INTEREST:
            continue


        # ----------------------------------------------------
        # Selection score
        # ----------------------------------------------------

        score = 0


        if distance <= 2:
            score += 40

        elif distance <= 5:
            score += 30

        elif distance <= 10:
            score += 20

        else:
            score += 10


        if open_interest >= 1000:
            score += 40

        elif open_interest >= 500:
            score += 30

        elif open_interest >= 250:
            score += 20

        else:
            score += 10


        selected.append({

            "symbol": contract.symbol,

            "strike": strike,

            "expiration": str(
                contract.expiration_date
            ),

            "open_interest": open_interest,

            "score": score,

            "distance": round(
                distance,
                2
            )

        })


    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    selected.sort(
        key=lambda x: (
            -x["score"],
            x["distance"]
        )
    )


    return selected[
        :MAX_RESULTS
    ]


# ============================================================
# GET BEST OPTION
# ============================================================

def get_best_option():

    """
    Automatically finds the best available
    CALL option according to the selector rules.

    Returns:
        dict or None
    """

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
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("        ALPHAPILOT AI OPTION SELECTOR")
    print("=" * 70)

    print()

    print(
        "Mode              : PAPER TRADING"
    )

    print(
        "Underlying         :",
        UNDERLYING_SYMBOL
    )

    print(
        "Contract Type      : CALL"
    )

    print(
        "Expiration Window  :",
        MIN_DAYS_TO_EXPIRY,
        "-",
        MAX_DAYS_TO_EXPIRY,
        "days"
    )

    print(
        "Max Strike Distance:",
        "$%.2f"
        % MAX_STRIKE_DISTANCE
    )

    print(
        "Min Open Interest  :",
        MIN_OPEN_INTEREST
    )


    # ========================================================
    # GET SPY PRICE
    # ========================================================

    print(
        "\nGetting current SPY price..."
    )

    spy_price = get_spy_price()


    if spy_price is None:

        print(
            "\nERROR: Unable to get SPY price."
        )

        raise SystemExit


    print(
        "SPY Price          : $%.2f"
        % spy_price
    )


    # ========================================================
    # GET CONTRACTS
    # ========================================================

    print(
        "\nSearching option contracts..."
    )

    contracts = get_option_contracts()


    print(
        "Contracts Found    :",
        len(contracts)
    )


    if not contracts:

        print(
            "\nNo option contracts found."
        )

        raise SystemExit


    # ========================================================
    # SELECT
    # ========================================================

    selected = select_contracts(
        contracts,
        spy_price
    )


    print("\n" + "=" * 70)
    print("             SELECTED OPTIONS")
    print("=" * 70)


    if not selected:

        print(
            "No suitable option contracts found."
        )

    else:

        for index, option in enumerate(
            selected,
            start=1
        ):

            print()
            print(
                "#%d" % index
            )

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
                int(
                    option["open_interest"]
                )
            )

            print(
                "Selection Score:",
                option["score"]
            )


    print("\n" + "=" * 70)
    print("ORDER ACTION")
    print("=" * 70)

    print(
        "NO ORDER WAS PLACED."
    )

    print(
        "This module only selects candidate options."
    )

    print("\n" + "=" * 70)
    print(
        "Option selector test complete."
    )
    print("=" * 70)