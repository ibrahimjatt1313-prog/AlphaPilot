import os

from dotenv import load_dotenv
from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest


# ==========================================
# 1. LOAD CREDENTIALS
# ==========================================

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    print("ERROR: Alpaca API keys not found.")
    exit()


# ==========================================
# 2. CONNECT TO OPTIONS DATA
# ==========================================

options_client = OptionHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)


# ==========================================
# 3. REQUEST OPTION CHAIN
# ==========================================

symbol = "SPY"

print("=" * 65)
print("ALPHAPILOT OPTIONS SCANNER")
print("=" * 65)

print(f"\nUnderlying: {symbol}")
print("Requesting option chain...\n")


try:

    request = OptionChainRequest(
        underlying_symbol=symbol
    )

    chain = options_client.get_option_chain(request)

    print("Options chain received successfully!")
    print("Number of contracts:", len(chain))

    count = 0

    for contract_symbol, snapshot in chain.items():

        print("\nContract:", contract_symbol)

        if snapshot.latest_quote:
            print(
                "Bid:",
                snapshot.latest_quote.bid_price,
                "| Ask:",
                snapshot.latest_quote.ask_price
            )

        if snapshot.latest_trade:
            print(
                "Last:",
                snapshot.latest_trade.price
            )

        if snapshot.implied_volatility:
            print(
                "IV:",
                snapshot.implied_volatility
            )

        if snapshot.greeks:
            print(
                "Delta:",
                snapshot.greeks.delta,
                "| Gamma:",
                snapshot.greeks.gamma
            )

        count += 1

        if count >= 10:
            break


except Exception as e:

    print("\nERROR while retrieving options chain:")
    print(e)


print("\n" + "=" * 65)
print("OPTIONS SCAN COMPLETE")
print("=" * 65)