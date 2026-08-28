import os
import json
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest
)
from alpaca.data.timeframe import TimeFrame


# ============================================================
# ALPHAPILOT AI - TECHNICAL DECISION ENGINE
# ============================================================

load_dotenv()


# ============================================================
# SETTINGS
# ============================================================

SYMBOL = "SPY"

MIN_CONFIDENCE = 70

LOOKBACK_DAYS = 10

FEED = "iex"


# ============================================================
# API KEYS
# ============================================================

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


if not API_KEY or not SECRET_KEY:

    print("ERROR: Alpaca API keys not found.")
    raise SystemExit


# ============================================================
# ALPACA CLIENT
# ============================================================

stock_client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY
)


# ============================================================
# LIVE QUOTE
# ============================================================

def get_live_quote():

    try:

        request = StockLatestQuoteRequest(
            symbol_or_symbols=SYMBOL,
            feed=FEED
        )

        quotes = stock_client.get_stock_latest_quote(
            request
        )

        quote = quotes[SYMBOL]

        bid = quote.bid_price
        ask = quote.ask_price

        bid = float(bid) if bid is not None else None
        ask = float(ask) if ask is not None else None

        if bid is not None and ask is not None:

            mid = (bid + ask) / 2

        elif bid is not None:

            mid = bid

        elif ask is not None:

            mid = ask

        else:

            mid = None

        return {
            "bid": bid,
            "ask": ask,
            "mid": mid
        }

    except Exception as e:

        print("\nLIVE QUOTE ERROR:")
        print(e)

        return {
            "bid": None,
            "ask": None,
            "mid": None
        }


# ============================================================
# HISTORICAL BARS
# ============================================================

def get_historical_bars():

    try:

        end_time = datetime.now(timezone.utc)

        start_time = (
            end_time
            - timedelta(days=LOOKBACK_DAYS)
        )

        request = StockBarsRequest(

            symbol_or_symbols=SYMBOL,

            timeframe=TimeFrame.Minute,

            start=start_time,

            end=end_time,

            feed=FEED,

            limit=1000
        )

        bars = stock_client.get_stock_bars(
            request
        )

        return list(bars[SYMBOL])

    except Exception as e:

        print("\nHISTORICAL DATA ERROR:")
        print(e)

        return []


# ============================================================
# SMA
# ============================================================

def calculate_sma(values, period):

    if len(values) < period:

        return None

    return sum(
        values[-period:]
    ) / period


# ============================================================
# EMA SERIES
# ============================================================

def calculate_ema_series(values, period):

    if len(values) < period:

        return []

    multiplier = 2 / (period + 1)

    first_ema = (
        sum(values[:period])
        / period
    )

    ema_values = [first_ema]

    previous_ema = first_ema

    for price in values[period:]:

        current_ema = (
            (price - previous_ema)
            * multiplier
        ) + previous_ema

        ema_values.append(
            current_ema
        )

        previous_ema = current_ema

    return ema_values


# ============================================================
# MACD
# ============================================================

def calculate_macd(values):

    if len(values) < 35:

        return None, None, None


    ema12 = calculate_ema_series(
        values,
        12
    )

    ema26 = calculate_ema_series(
        values,
        26
    )


    if not ema12 or not ema26:

        return None, None, None


    # --------------------------------------------------------
    # Align EMA12 with EMA26.
    #
    # EMA26 starts later than EMA12.
    # --------------------------------------------------------

    offset = len(ema12) - len(ema26)

    ema12_aligned = ema12[offset:]


    macd_series = []

    for fast, slow in zip(
        ema12_aligned,
        ema26
    ):

        macd_series.append(
            fast - slow
        )


    if len(macd_series) < 9:

        return None, None, None


    signal_series = calculate_ema_series(
        macd_series,
        9
    )


    if not signal_series:

        return None, None, None


    macd_current = macd_series[-1]

    signal_current = signal_series[-1]

    histogram = (
        macd_current
        - signal_current
    )


    return (
        macd_current,
        signal_current,
        histogram
    )


# ============================================================
# RSI
# ============================================================

def calculate_rsi(values, period=14):

    if len(values) <= period:

        return None


    gains = []
    losses = []


    for i in range(1, len(values)):

        change = (
            values[i]
            - values[i - 1]
        )

        if change > 0:

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(abs(change))


    average_gain = (
        sum(gains[:period])
        / period
    )

    average_loss = (
        sum(losses[:period])
        / period
    )


    # Wilder-style smoothing

    for i in range(
        period,
        len(gains)
    ):

        average_gain = (
            (
                average_gain
                * (period - 1)
            )
            + gains[i]
        ) / period


        average_loss = (
            (
                average_loss
                * (period - 1)
            )
            + losses[i]
        ) / period


    if average_loss == 0:

        return 100.0


    rs = (
        average_gain
        / average_loss
    )


    return 100 - (
        100 / (1 + rs)
    )


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def analyze_market(
    bars,
    live_price
):

    if len(bars) < 50:

        return {
            "ready": False,
            "reason": (
                "Not enough historical bars "
                "for technical analysis."
            )
        }


    # --------------------------------------------------------
    # Extract closing prices and volume
    # --------------------------------------------------------

    closes = [
        float(bar.close)
        for bar in bars
    ]

    volumes = [
        float(bar.volume)
        for bar in bars
    ]


    price = live_price

    if price is None:

        price = closes[-1]


    # --------------------------------------------------------
    # Indicators
    # --------------------------------------------------------

    sma20 = calculate_sma(
        closes,
        20
    )

    sma50 = calculate_sma(
        closes,
        50
    )

    rsi14 = calculate_rsi(
        closes,
        14
    )

    macd, macd_signal, macd_histogram = (
        calculate_macd(closes)
    )


    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    recent_volumes = volumes[-20:]

    average_volume = (
        sum(recent_volumes)
        / len(recent_volumes)
    )

    current_volume = volumes[-1]


    # ========================================================
    # SCORING
    # ========================================================

    score = 0

    reasons = []


    # --------------------------------------------------------
    # 1. PRICE VS SMA20
    # --------------------------------------------------------

    if sma20 is not None:

        if price > sma20:

            score += 20

            reasons.append(
                "Price above SMA20"
            )

        else:

            reasons.append(
                "Price below SMA20"
            )


    # --------------------------------------------------------
    # 2. SMA20 VS SMA50
    # --------------------------------------------------------

    if (
        sma20 is not None
        and sma50 is not None
    ):

        if sma20 > sma50:

            score += 20

            reasons.append(
                "SMA20 above SMA50"
            )

        else:

            reasons.append(
                "SMA20 below SMA50"
            )


    # --------------------------------------------------------
    # 3. RSI
    # --------------------------------------------------------

    if rsi14 is not None:

        if 50 <= rsi14 < 70:

            score += 20

            reasons.append(
                "RSI bullish range"
            )

        elif rsi14 >= 70:

            reasons.append(
                "RSI overbought"
            )

        else:

            reasons.append(
                "RSI below bullish range"
            )


    # --------------------------------------------------------
    # 4. MACD
    # --------------------------------------------------------

    if (
        macd is not None
        and macd_signal is not None
    ):

        if (
            macd > macd_signal
            and macd_histogram > 0
        ):

            score += 20

            reasons.append(
                "MACD bullish"
            )

        else:

            reasons.append(
                "MACD bearish or weakening"
            )


    # --------------------------------------------------------
    # 5. VOLUME
    # --------------------------------------------------------

    if average_volume > 0:

        if current_volume >= average_volume:

            score += 20

            reasons.append(
                "Volume confirms momentum"
            )

        else:

            reasons.append(
                "Volume below average"
            )


    # ========================================================
    # CONFIDENCE
    # ========================================================

    confidence = score


    # ========================================================
    # FINAL DECISION
    # ========================================================

    if confidence >= MIN_CONFIDENCE:

        decision = "BUY"

    else:

        decision = "NO TRADE"


    # ========================================================
    # RESULT
    # ========================================================

    return {

        "ready": True,

        "price": round(
            price,
            2
        ),

        "sma20": round(
            sma20,
            2
        ) if sma20 is not None else None,

        "sma50": round(
            sma50,
            2
        ) if sma50 is not None else None,

        "rsi14": round(
            rsi14,
            2
        ) if rsi14 is not None else None,

        "macd": round(
            macd,
            4
        ) if macd is not None else None,

        "macd_signal": round(
            macd_signal,
            4
        ) if macd_signal is not None else None,

        "macd_histogram": round(
            macd_histogram,
            4
        ) if macd_histogram is not None else None,

        "current_volume": current_volume,

        "average_volume": round(
            average_volume,
            2
        ),

        "confidence": confidence,

        "decision": decision,

        "reasons": reasons
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "        ALPHAPILOT AI TECHNICAL DECISION ENGINE"
    )

    print("=" * 70)

    print()

    print(
        "Mode           : DECISION ONLY"
    )

    print(
        "Symbol         :",
        SYMBOL
    )

    print(
        "Feed           :",
        FEED.upper()
    )

    print(
        "Min Confidence :",
        str(MIN_CONFIDENCE) + "%"
    )


    # ========================================================
    # LIVE QUOTE
    # ========================================================

    quote = get_live_quote()


    # ========================================================
    # HISTORICAL DATA
    # ========================================================

    bars = get_historical_bars()


    print("\n" + "=" * 70)

    print(
        "             MARKET DATA"
    )

    print("=" * 70)


    if quote["bid"] is not None:

        print(
            "Bid            : $%.2f"
            % quote["bid"]
        )

    else:

        print(
            "Bid            : N/A"
        )


    if quote["ask"] is not None:

        print(
            "Ask            : $%.2f"
            % quote["ask"]
        )

    else:

        print(
            "Ask            : N/A"
        )


    if quote["mid"] is not None:

        print(
            "Live Mid       : $%.2f"
            % quote["mid"]
        )

    else:

        print(
            "Live Mid       : N/A"
        )


    print(
        "Historical Bars:",
        len(bars)
    )


    # ========================================================
    # ANALYZE
    # ========================================================

    analysis = analyze_market(
        bars,
        quote["mid"]
    )


    # ========================================================
    # NOT READY
    # ========================================================

    if not analysis["ready"]:

        print("\n" + "=" * 70)

        print(
            "             AI TRADE DECISION"
        )

        print("=" * 70)

        print(
            "Symbol     :",
            SYMBOL
        )

        print(
            "Decision   : NO TRADE"
        )

        print(
            "Confidence : 0%"
        )

        print(
            "Reason     :",
            analysis["reason"]
        )


    # ========================================================
    # READY
    # ========================================================

    else:

        print("\n" + "=" * 70)

        print(
            "             TECHNICAL ANALYSIS"
        )

        print("=" * 70)


        print(
            "Price            : $%.2f"
            % analysis["price"]
        )

        print(
            "SMA 20           : $%.2f"
            % analysis["sma20"]
        )

        print(
            "SMA 50           : $%.2f"
            % analysis["sma50"]
        )

        print(
            "RSI 14           : %.2f"
            % analysis["rsi14"]
        )

        print(
            "MACD             : %.4f"
            % analysis["macd"]
        )

        print(
            "MACD Signal      : %.4f"
            % analysis["macd_signal"]
        )

        print(
            "MACD Histogram   : %.4f"
            % analysis["macd_histogram"]
        )

        print(
            "Current Volume   : %.0f"
            % analysis["current_volume"]
        )

        print(
            "Average Volume   : %.0f"
            % analysis["average_volume"]
        )


        print("\n" + "=" * 70)

        print(
            "             AI TRADE DECISION"
        )

        print("=" * 70)


        print(
            "Symbol     :",
            SYMBOL
        )

        print(
            "Decision   :",
            analysis["decision"]
        )

        print(
            "Confidence :",
            str(analysis["confidence"]) + "%"
        )


        print(
            "Reasons:"
        )


        for reason in analysis["reasons"]:

            print(
                " -",
                reason
            )


    # ========================================================
    # TIMESTAMP
    # ========================================================

    print("\n" + "=" * 70)

    print(
        "Timestamp  :",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 70)

    print(
        "\nDecision engine test complete."
    )