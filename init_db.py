import sqlite3
from datetime import datetime
import pandas as pd

DB_PATH = "data/portfolio.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT PRIMARY KEY,
            buy_price REAL,
            buy_date TEXT,
            current_price REAL,
            days_held INTEGER,
            status TEXT,
            quantity INTEGER,
            investment REAL,
            pnl REAL,
            return_pct REAL
        )
        ''')
        conn.commit()

# INSERT or UPSERT
def insert_or_update_stock(symbol, buy_price, quantity, current_price, days_held=0, status="Holding",buy_date=None):
    buy_date = datetime.now().strftime('%Y-%m-%d') if buy_date is None else buy_date
    buy_price = float(buy_price)
    quantity = int(quantity)
    current_price = float(current_price)
    days_held = int(days_held)
    investment = round(float(buy_price * quantity), 2)
    pnl = round(float((current_price - buy_price) * quantity), 2)
    return_pct = round(float(((current_price / buy_price) - 1) * 100), 2) if buy_price else 0.0

    print(f"Inserting/Updating stock: {symbol}, Buy Price: {buy_price}, Quantity: {quantity}, Current Price: {current_price}, Days Held: {days_held}, Status: {status}")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO portfolio (symbol, buy_price, buy_date, current_price, days_held, status, quantity, investment, pnl, return_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            buy_price=excluded.buy_price,
            buy_date=excluded.buy_date,
            current_price=excluded.current_price,
            quantity=excluded.quantity,
            investment=excluded.investment,
            pnl=excluded.pnl,
            return_pct=excluded.return_pct,
            status=excluded.status,
            days_held=excluded.days_held
        ''', (symbol, buy_price, buy_date, current_price, days_held, status, quantity, investment, pnl, return_pct))
        conn.commit()

# DELETE
def delete_stock(symbol):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM portfolio WHERE symbol = ?', (symbol,))
        conn.commit()

# Mark stock as sold
def mark_stock_sold(symbol):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE portfolio
            SET status = 'Sold'
            WHERE symbol = ?
        ''', (symbol,))
        conn.commit()

# RESET (TRUNCATE)
def reset_portfolio():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio")
        conn.commit()

# FETCH all
def fetch_portfolio():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM portfolio')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df= pd.DataFrame([dict(zip(columns, row)) for row in rows])
        return df

if __name__ == "__main__":
    initialize_db()
