import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame


# ==========================================
# 1. LOAD ALPACA CREDENTIALS
# ==========================================

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    print("ERROR: Alpaca API keys not found.")
    exit()


# ==========================================
# 2. CONNECT TO ALPACA MARKET DATA
# ==========================================

data_client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)


# ==========================================
# 3. TECHNICAL INDICATORS
# ==========================================

def calculate_indicators(df):

    # 20-day moving average
    df["SMA20"] = df["close"].rolling(window=20).mean()

    # 50-day moving average
    df["SMA50"] = df["close"].rolling(window=50).mean()

    # Momentum
    df["Momentum"] = df["close"].pct_change(periods=5) * 100

    # Volatility
    df["Volatility"] = df["close"].pct_change().rolling(10).std() * 100

    return df


# ==========================================
# 4. GENERATE TRADING SIGNAL
# ==========================================

def generate_signal(df):

    latest = df.iloc[-1]

    close = latest["close"]
    sma20 = latest["SMA20"]
    sma50 = latest["SMA50"]
    momentum = latest["Momentum"]
    volatility = latest["Volatility"]

    # Make sure indicators exist
    if pd.isna(sma20) or pd.isna(sma50) or pd.isna(momentum):
        return "NO TRADE"

    # --------------------------------------
    # BULLISH CONDITIONS
    # --------------------------------------

    bullish = (
        close > sma20
        and sma20 > sma50
        and momentum > 1
        and volatility < 5
    )

    # --------------------------------------
    # BEARISH CONDITIONS
    # --------------------------------------

    bearish = (
        close < sma20
        and sma20 < sma50
        and momentum < -1
        and volatility < 5
    )

    if bullish:
        return "BULLISH"

    elif bearish:
        return "BEARISH"

    else:
        return "NO TRADE"


# ==========================================
# 5. SCAN SYMBOL
# ==========================================

def analyze_symbol(symbol):

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=120)
    )

    bars = data_client.get_stock_bars(request)

    data = bars[symbol]

    if not data:
        return None

    rows = []

    for bar in data:
        rows.append({
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        })

    df = pd.DataFrame(rows)

    df = calculate_indicators(df)

    signal = generate_signal(df)

    latest = df.iloc[-1]

    return {
        "symbol": symbol,
        "price": latest["close"],
        "sma20": latest["SMA20"],
        "sma50": latest["SMA50"],
        "momentum": latest["Momentum"],
        "volatility": latest["Volatility"],
        "signal": signal
    }


# ==========================================
# 6. MAIN SCANNER
# ==========================================

symbols = [
    "SPY",
    "QQQ",
    "NVDA",
    "AAPL",
    "TSLA"
]

print("=" * 65)
print("          ALPHAPILOT AI SIGNAL ENGINE")
print("=" * 65)

for symbol in symbols:

    try:

        result = analyze_symbol(symbol)

        if result:

            print(f"\n📊 {result['symbol']}")

            print(f"Price      : {result['price']:.2f}")
            print(f"SMA 20     : {result['sma20']:.2f}")
            print(f"SMA 50     : {result['sma50']:.2f}")
            print(f"Momentum   : {result['momentum']:.2f}%")
            print(f"Volatility : {result['volatility']:.2f}%")
            print(f"Signal     : {result['signal']}")

    except Exception as e:

        print(f"\n{symbol}: ERROR")
        print(e)


print("\n" + "=" * 65)
print("          SIGNAL SCAN COMPLETE")
print("=" * 65)