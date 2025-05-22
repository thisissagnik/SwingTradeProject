import streamlit as st
import pandas as pd
from signal_generator import analyze_stocks
from portfolio_manager import update_portfolio, buy_stock, sell_stock, reset_portfolio

st.set_page_config(layout="wide")
st.title("📈 V40 Moving Average Strategy Dashboard")

# ------------------ Utility Functions ------------------

def signal_color(signal):
    if signal == "Buy":
        return "background-color: #b6f0b6; color: green;"  # light green background + green text
    elif signal == "Sell":
        return "background-color: #f0b6b6; color: red;"    # light red background + red text
    else:
        return "background-color: #f0f0f0; color: grey;"    # light grey background + grey text

def pnl_color(val):
    try:
        val = float(val.replace("₹", "").replace(",", ""))
        color = "green" if val >= 0 else "red"
        return f"color: {color}"
    except:
        return ""

def portfolio_row_style(row):
    if row["Status"] == "Sold":
        return ['background-color: lightgray; color: grey'] * len(row)
    elif row["Status"] == "Holding":
        return ['background-color: #e6ffe6; color:green'] * len(row)
    else:
        return [''] * len(row)

# ------------------ Component Functions ------------------

def show_signals():
    st.subheader("Stock Signals")
    signals = analyze_stocks(v40_list)
    styled_signals = signals.style.applymap(signal_color, subset=["Signal"])
    st.dataframe(styled_signals, use_container_width=True)
    return signals

def buy_stocks(signals):
    st.subheader("Buy Stocks")
    buy_signals = signals[signals["Signal"] == "Buy"]

    if buy_signals.empty:
        st.info("No Buy signals currently.")
    else:
        for _, row in buy_signals.iterrows():
            symbol = row["Symbol"]
            price = row["Current Price"]
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                st.markdown(f"**{symbol}**")
            with col2:
                st.markdown(f"₹{price:.2f}")
            with col3:
                qty = st.text_input(f"Quantity", key=f"qty_{symbol}")
            with col4:
                if st.button(f"Buy", key=f"buy_{symbol}"):
                    qty_str = st.session_state.get(f"qty_{symbol}", "1")
                    try:
                        qty = int(qty_str)
                        if qty < 1:
                            st.warning("Quantity must be at least 1.")
                        else:
                            buy_stock(symbol, price, qty)
                            st.success(f"Bought {qty} shares of {symbol} at ₹{price:.2f}")
                    except ValueError:
                        st.error("Please enter a valid integer quantity.")

def get_portfolio():
    
    # Re-fetch portfolio after selling if triggered
    if st.session_state.get("sell_triggered", False):
        st.session_state.sell_triggered = False

    portfolio = update_portfolio()

    if portfolio.empty:
        return portfolio

    portfolio["Investment"] = portfolio["Buy Price"] * portfolio["Quantity"]
    portfolio["P&L"] = (portfolio["Current Price"] - portfolio["Buy Price"]) * portfolio["Quantity"]
    portfolio["Return %"] = ((portfolio["Current Price"] / portfolio["Buy Price"]) - 1) * 100

    portfolio["Investment"] = portfolio["Investment"].apply(lambda x: f"₹{x:,.2f}")
    portfolio["P&L"] = portfolio["P&L"].apply(lambda x: f"₹{x:,.2f}")
    portfolio["Return %"] = portfolio["Return %"].apply(lambda x: f"{x:.2f}%")

    display_cols = [
        "Symbol", "Buy Price", "Current Price", "Quantity",
        "Investment", "P&L", "Return %", "Status", "Days Held"
    ]

    portfolio = portfolio[display_cols]
    return portfolio

def display_portfolio(portfolio):
    st.subheader("Portfolio")
    if portfolio.empty:
        st.info("Portfolio is empty.")
    else:
        styled = portfolio.style\
            .apply(lambda x: portfolio_row_style(x), axis=1)\
            .applymap(pnl_color, subset=["P&L"])

        st.dataframe(styled, use_container_width=True)

def sell_stocks(portfolio):
    st.subheader("Sell Stocks")
    holdings = portfolio[portfolio["Status"] == "Holding"]
    if holdings.empty:
        st.info("No holdings available to sell.")
    else:
        for _, row in holdings.iterrows():
            symbol = row["Symbol"]
            current_price = row["Current Price"]
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                st.markdown(f"**{symbol}**")
            with col2:
                st.markdown(f"₹{current_price:.2f}")
            with col3:
                if st.button(f"Sell", key=f"sell_{symbol}"):
                    sell_stock(symbol)
                    st.session_state.sell_triggered = True
                    st.success(f"Sold all holdings of {symbol}")

def reset_portfolio_ui():
    if st.button("🔄 Reset Portfolio"):
        reset_portfolio()
        st.success("Portfolio reset.")

# ------------------ Main App Flow ------------------

# Load stock symbols
v40 = pd.read_csv("data/v40_companies.csv")
v40_list = v40["Symbol"].dropna().unique().tolist()

# UI Sections
signals_df = show_signals()
buy_stocks(signals_df)
portfolio_df = get_portfolio() # Get portfolio data
sell_stocks(portfolio_df)
portfolio_df = get_portfolio()  # Refresh portfolio after selling
reset_portfolio_ui()
portfolio_df = get_portfolio()  # Refresh portfolio after reset
# Display portfolio
display_portfolio(portfolio_df)
