import requests
import pandas as pd
from fastapi import FastAPI, Query

app = FastAPI()

BASE_URL = "https://contract.mexc.com"

@app.get("/")
def home():
    return {"status": "ok"}

@app.get("/analyze")
def analyze(symbol: str = Query("BTC_USDT")):
    try:
        url = f"{BASE_URL}/api/v1/contract/kline/{symbol}"
        params = {
            "interval": "Min5",
            "limit": 150
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data["success"] != True:
            return {"status": "error", "message": "MEXC veri alınamadı"}

        klines = data["data"]

        df = pd.DataFrame(klines)
        df["close"] = df["close"].astype(float)

        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        def rsi(series, period=14):
            delta = series.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

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
            "symbol": symbol,
            "price": price,
            "ema20": ema20,
            "ema50": ema50,
            "rsi": round(rsi_val, 2),
            "score": score,
            "signal": signal
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
