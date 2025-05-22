# signal_generator.py

import yfinance as yf
import pandas as pd

def calculate_moving_averages(ticker, period="250d"):
    data = yf.download(ticker, period=period, interval="1d", auto_adjust=True)
    if data.empty:
        return None
    
    data["MA_20"] = data["Close"].rolling(window=20).mean()
    data["MA_50"] = data["Close"].rolling(window=50).mean()
    data["MA_200"] = data["Close"].rolling(window=200).mean()
    data["Ticker"] = ticker
    return data

def generate_signal(data):
    if data is None or len(data) == 0:
        return None
    
    latest = data.iloc[-1]
    price = latest["Close"].iloc[-1]
    ma20 = latest["MA_20"].iloc[-1]
    ma50 = latest["MA_50"].iloc[-1]
    ma200 = latest["MA_200"].iloc[-1]

    # Ensure none are NaN before comparing
    if pd.isna(ma20) or pd.isna(ma50) or pd.isna(ma200):
        return "Hold", price

    if ma200 > ma50 > ma20:
        return "Buy", price
    elif ma20 > ma50 > ma200:
        return "Sell", price
    else:
        return "Hold", price

def analyze_stocks(v40_list):
    results = []

    for symbol in v40_list:
        df = calculate_moving_averages(symbol)
        if df is not None:
            signal, price = generate_signal(df)
            results.append({
                "Symbol": symbol,
                "Signal": signal,
                "Current Price": round(price, 2),
                "MA_20": round(df.iloc[-1]["MA_20"].iloc[-1], 2),
                "MA_50": round(df.iloc[-1]["MA_50"].iloc[-1], 2),
                "MA_200": round(df.iloc[-1]["MA_200"].iloc[-1], 2),
            })
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    # Load tickers
    v40 = pd.read_csv("data/v40_companies.csv")
    v40_list = v40["Symbol"].tolist()
    signals = analyze_stocks(v40_list)
    print(signals)