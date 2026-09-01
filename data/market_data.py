import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

data_client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)

symbols = ["SPY", "QQQ", "NVDA", "AAPL", "TSLA"]

request = StockBarsRequest(
    symbol_or_symbols=symbols,
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=10)
)

bars = data_client.get_stock_bars(request)

print("=" * 55)
print("ALPHAPILOT MARKET DATA SCANNER")
print("=" * 55)

for symbol in symbols:
    try:
        data = bars[symbol]

        if data:
            latest = data[-1]

            print(f"\n📊 {symbol}")
            print(f"Open   : {latest.open}")
            print(f"High   : {latest.high}")
            print(f"Low    : {latest.low}")
            print(f"Close  : {latest.close}")
            print(f"Volume : {latest.volume}")

    except Exception as e:
        print(f"\n{symbol}: Data unavailable")
        print("Error:", e)

print("\n" + "=" * 55)
print("MARKET DATA TEST COMPLETE")
print("=" * 55)