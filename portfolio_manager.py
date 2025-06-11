# portfolio_manager.py

import pandas as pd
import yfinance as yf
from datetime import datetime
from init_db import insert_or_update_stock, mark_stock_sold, fetch_portfolio as db_fetch_portfolio, reset_portfolio as db_reset_portfolio
import threading

def buy_stock(symbol, price, quantity):
    # Initial buy sets current price = buy price
    insert_or_update_stock(symbol, price, quantity, price)

def sell_stock(symbol):
    mark_stock_sold(symbol)

def update_portfolio(current_prices: dict = None):
    print(f"update_portfolio called in thread {threading.current_thread().name}")
    portfolio = db_fetch_portfolio()
    if portfolio.empty or len(portfolio) == 0:
        return portfolio  # Do NOT update if table is empty

    today = pd.Timestamp.today().normalize()
    portfolio["days_held"] = (today - pd.to_datetime(portfolio["buy_date"])).dt.days

    for i in portfolio.index:
        symbol = portfolio.at[i, "symbol"]
        try:
            if symbol in current_prices:
                print(f"Updating {symbol} with latest data with current price {current_prices[symbol]}")
                current_price = current_prices[symbol]
                buy_price = portfolio.at[i, "buy_price"]
                quantity = portfolio.at[i, "quantity"]
                days_held = portfolio.at[i, "days_held"]
                status = portfolio.at[i, "status"]
                buy_date = portfolio.at[i, "buy_date"]
                # Update stock with latest price and other details
                if status != "Sold":
                    insert_or_update_stock(symbol, buy_price, quantity, current_price, days_held, status, buy_date)
        except Exception as e:
            print(f"Error updating {symbol}: {e}")

    return db_fetch_portfolio()

def reset_portfolio():
    db_reset_portfolio()
