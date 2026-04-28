from fastapi import FastAPI, Query
import requests
import pandas as pd

app = FastAPI()

BINANCE_BASE = "https://fapi.binance.com"

@app.get("/")
def home():
    return {"status": "ok", "message": "Binance Signal API calisiyor"}

@app.get("/status")
def status():
    return {"status": "ok", "exchange": "BINANCE"}

def get_klines(symbol="BTCUSDT", interval="5m", limit=100):
    url = f"{BINANCE_BASE}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","taker_base","taker_quote","ignore"
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
def analyze(symbol: str = Query("BTCUSDT"), interval: str = Query("5m")):
    try:
        df = get_klines(symbol.upper(), interval)

        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()
        df["rsi"] = rsi(df["close"])

        last = df.iloc[-1]
        price = float(last["close"])
        ema20 = float(last["ema20"])
        ema50 = float(last["ema50"])
        rsi_val = float(last["rsi"])

        score = 0
        score += 1 if price > ema20 else -1
        score += 1 if ema20 > ema50 else -1

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
            "exchange": "BINANCE",
            "symbol": symbol.upper(),
            "interval": interval,
            "price": price,
            "rsi": round(rsi_val, 2),
            "ema20": round(ema20, 4),
            "ema50": round(ema50, 4),
            "score": score,
            "signal": signal
        }

    except Exception as e:
        return {"exchange": "BINANCE", "status": "error", "message": str(e)}

@app.get("/top")
def top():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    return {"exchange": "BINANCE", "results": [analyze(s, "5m") for s in symbols]}
