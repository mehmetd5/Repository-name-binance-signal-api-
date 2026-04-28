import os
from fastapi import FastAPI, Query
import requests
import pandas as pd

app = FastAPI()

EXCHANGE = os.getenv("EXCHANGE", "MEXC").upper()

if EXCHANGE == "MEXC":
    BASE_URL = "https://contract.mexc.com"
else:
    BASE_URL = "https://fapi.binance.com"


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Signal API calisiyor",
        "exchange": EXCHANGE
    }


@app.get("/status")
def status():
    return {
        "status": "ok",
        "exchange": EXCHANGE
    }


def normalize_symbol(symbol: str):
    symbol = symbol.upper()
    if EXCHANGE == "MEXC":
        if "_" not in symbol:
            symbol = symbol.replace("USDT", "_USDT")
    return symbol


def get_klines(symbol="BTCUSDT", interval="Min5", limit=100):
    symbol = normalize_symbol(symbol)

    if EXCHANGE == "MEXC":
        url = f"{BASE_URL}/api/v1/contract/kline/{symbol}"
        params = {
            "interval": interval
        }

        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        resp = r.json()

        if not resp.get("success"):
            raise Exception(f"MEXC response hatali: {resp}")

        data = resp.get("data", {})

        if not data or "close" not in data:
            raise Exception(f"MEXC kline data hatali: {resp}")

        df = pd.DataFrame({
            "time": data.get("time", []),
            "open": data.get("open", []),
            "high": data.get("high", []),
            "low": data.get("low", []),
            "close": data.get("close", []),
            "volume": data.get("vol", [])
        })

        df = df.tail(limit)
        df["close"] = df["close"].astype(float)

    else:
        url = f"{BASE_URL}/fapi/v1/klines"
        params = {
            "symbol": symbol,
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
        df["rsi"] = rsi(df["close"])

        last = df.iloc[-1]

        price = float(last["close"])
        ema20 = float(last["ema20"])
        ema50 = float(last["ema50"])
        rsi_val = float(last["rsi"])

        score = 0

        if price > ema20:
            score += 1
        else:
            score -= 1

        if ema20 > ema50:
            score += 1
        else:
            score -= 1

        if rsi_val > 55:
            score += 1
        elif rsi_val < 45:
            score -= 1

        if score >= 2:
            signal = "LONG"
        elif score <= -2:
            signal = "SHORT"
        else:
            signal = "BEKLE"

        return {
            "status": "ok",
            "exchange": EXCHANGE,
            "symbol": normalize_symbol(symbol),
            "price": round(price, 6),
            "ema20": round(ema20, 6),
            "ema50": round(ema50, 6),
            "rsi": round(rsi_val, 2),
            "score": score,
            "signal": signal
        }

    except Exception as e:
        return {
            "status": "error",
            "exchange": EXCHANGE,
            "message": str(e)
        }


@app.get("/top")
def top():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    return {
        "exchange": EXCHANGE,
        "results": [analyze(s) for s in symbols]
    }
