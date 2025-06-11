# portfolio_manager.py

import pandas as pd
import yfinance as yf
from datetime import datetime
from init_db import insert_or_update_stock, mark_stock_sold, fetch_portfolio as db_fetch_portfolio, reset_portfolio as db_reset_portfolio

def buy_stock(symbol, price, quantity):
    # Initial buy sets current price = buy price
    insert_or_update_stock(symbol, price, quantity, price)

def sell_stock(symbol):
    mark_stock_sold(symbol)

def update_portfolio():
    portfolio = db_fetch_portfolio()
    if portfolio.empty or len(portfolio) == 0:
        return portfolio  # Do NOT update if table is empty

    today = pd.Timestamp.today().normalize()
    portfolio["days_held"] = (today - pd.to_datetime(portfolio["buy_date"])).dt.days

    for i in portfolio.index:
        symbol = portfolio.at[i, "symbol"]
        try:
            print(f"Updating stock: {symbol}")
            data = yf.download(symbol, period="2d", interval="1d", auto_adjust=True)
            if not data.empty:
                current_price = round(data.iloc[-1]["Close"].iloc[-1], 2)
                buy_price = portfolio.at[i, "buy_price"]
                quantity = portfolio.at[i, "quantity"]
                days_held = portfolio.at[i, "days_held"]
                status = portfolio.at[i, "status"]
                # Update stock with latest price and other details
                if status != "Sold":
                    insert_or_update_stock(symbol, buy_price, quantity, current_price, days_held, status)
        except Exception as e:
            print(f"Error updating {symbol}: {e}")

    return db_fetch_portfolio()

def reset_portfolio():
    db_reset_portfolio()
