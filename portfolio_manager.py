# portfolio_manager.py

import pandas as pd
import yfinance as yf
from datetime import datetime

PORTFOLIO_FILE = "data/portfolio.csv"

def load_portfolio():
    try:
        return pd.read_csv(PORTFOLIO_FILE, parse_dates=["Buy Date"])
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "Symbol", "Buy Price", "Buy Date", "Current Price",
            "Days Held", "Status", "Quantity"
        ])

def save_portfolio(df):
    df.to_csv(PORTFOLIO_FILE, index=False)

def buy_stock(symbol, price, quantity):
    portfolio = load_portfolio()
    today = pd.Timestamp.today().normalize()

    # Check if the stock is already held
    existing = (portfolio["Symbol"] == symbol) & (portfolio["Status"] == "Holding")
    if not existing.any():
        new_entry = pd.DataFrame([{
            "Symbol": symbol,
            "Buy Price": price,
            "Buy Date": today,
            "Current Price": price,
            "Days Held": 0,
            "Status": "Holding",
            "Quantity": quantity
        }])
        portfolio = pd.concat([portfolio, new_entry], ignore_index=True)
        save_portfolio(portfolio)

def sell_stock(symbol):
    portfolio = load_portfolio()
    portfolio.loc[(portfolio["Symbol"] == symbol) & (portfolio["Status"] == "Holding"), "Status"] = "Sold"
    save_portfolio(portfolio)

def update_portfolio():
    portfolio = load_portfolio()
    today = pd.Timestamp.today().normalize()

    if portfolio.empty:
        return portfolio

    portfolio["Days Held"] = (today - pd.to_datetime(portfolio["Buy Date"])).dt.days

    # Update current prices
    for i in portfolio.index:
        symbol = portfolio.at[i, "Symbol"]
        try:
            data = yf.download(symbol, period="2d", interval="1d", auto_adjust=True)
            if not data.empty:
                portfolio.at[i, "Current Price"] = round(data["Close"].iloc[-1], 2)
        except Exception:
            pass

    # Ensure Quantity column exists
    if "Quantity" not in portfolio.columns:
        portfolio["Quantity"] = 1

    # Compute Investment, P&L, Return %
    portfolio["Investment"] = portfolio["Buy Price"] * portfolio["Quantity"]
    portfolio["P&L"] = (portfolio["Current Price"] - portfolio["Buy Price"]) * portfolio["Quantity"]
    portfolio["Return %"] = ((portfolio["Current Price"] - portfolio["Buy Price"]) / portfolio["Buy Price"]) * 100

    save_portfolio(portfolio)
    return portfolio

def reset_portfolio():
    df = pd.DataFrame(columns=[
        "Symbol", "Buy Price", "Buy Date", "Current Price",
        "Days Held", "Status", "Quantity", "Investment", "P&L", "Return %"
    ])
    save_portfolio(df)
