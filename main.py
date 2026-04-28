import os
from fastapi import FastAPI, Query
import requests
import pandas as pd

app = FastAPI()

# 🔥 SABİT BINANCE (mobil sorun çözümü)
EXCHANGE = "BINANCE"
BASE_URL = "https://fapi.binance.com"


@app.get("/")
def home():
    return {"status": "ok", "exchange": EXCHANGE}


@app.get("/status")
def status():
    return {"status": "ok", "exchange": EXCHANGE}


def get_klines(symbol="BTCUSDT", limit=150):
    url = f"{BASE_URL}/fapi/v1/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": "5m",
        "limit": limit
    }

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "taker_base", "taker_quote", "ignore"
    ])

    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


@app.get("/analyze")
def analyze(symbol: str = Query("BTCUSDT")):
    try:
        df = get_klines(symbol)

        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()
        df["rsi"] = rsi(df["close"])

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price = float(last["close"])
        ema20 = float(last["ema20"])
        ema50 = float(last["ema50"])
        ema200 = float(last["ema200"])
        rsi_val = float(last["rsi"])

        volume = float(last["volume"])
        avg_volume = float(df["volume"].rolling(20).mean().iloc[-1])

        score = 0

        # Trend
        if price > ema200:
            score += 1
        else:
            score -= 1

        # EMA
        if ema20 > ema50:
            score += 1
        else:
            score -= 1

        # RSI
        if rsi_val > 55:
            score += 1
        elif rsi_val < 45:
            score -= 1

        # Hacim
        if volume > avg_volume:
            score += 1

        # Momentum
        if price > prev["close"]:
            score += 1
        else:
            score -= 1

        if score >= 3:
            signal = "LONG"
        elif score <= -3:
            signal = "SHORT"
        else:
            signal = "BEKLE"

        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "price": round(price, 6),
            "ema20": round(ema20, 6),
            "ema50": round(ema50, 6),
            "ema200": round(ema200, 6),
            "rsi": round(rsi_val, 2),
            "volume": volume,
            "score": score,
            "signal": signal
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/top")
def top():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]

    results = []
    for s in symbols:
        res = analyze(s)
        if res["status"] == "ok":
            results.append(res)

    return {
        "status": "ok",
        "results": sorted(results, key=lambda x: x["score"], reverse=True)
    }
