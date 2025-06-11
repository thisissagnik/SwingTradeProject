import dash
from dash import dcc, html, dash_table, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import pandas as pd
from signal_generator import analyze_stocks
from portfolio_manager import update_portfolio, buy_stock, sell_stock, reset_portfolio
from init_db import initialize_db
from time import time

def get_signals(stock_list):
    """
    Fetches stock signals for the given list of stock symbols.
    Args:
        stock_list (list): List of stock symbols to analyze.
    Returns:
        pd.DataFrame: DataFrame containing stock signals and prices.
    """
    print("Fetching stock signals...")
    return analyze_stocks(stock_list)


def get_portfolio_df(signals_data):
    # create a dictionary from the signals(signals is a dataframe) data containing symbols as key and current prices as value
    current_prices = {
        row["Symbol"]: row["Current Price"] for row in signals_data if "Current Price" in row
    }
    
    # Fetch the portfolio from the database
    portfolio = update_portfolio(current_prices)
    if portfolio.empty:
        return portfolio
    # Rename columns from DB (snake_case) to UI (Title Case with spaces)
    portfolio = portfolio.rename(
        columns={
            "symbol": "Symbol",
            "buy_price": "Buy Price",
            "buy_date": "Buy Date",
            "current_price": "Current Price",
            "quantity": "Quantity",
            "status": "Status",
            "days_held": "Days Held",
            "investment": "Investment",
            "pnl": "P&L",
            "return_pct": "Return %",
        }
    )

    display_cols = [
        "Symbol",
        "Buy Price",
        "Buy Date",
        "Current Price",
        "Quantity",
        "Investment",
        "P&L",
        "Return %",
        "Status",
        "Days Held",
    ]
    return portfolio[display_cols]

# Ensure the database is initialized
initialize_db()

# Load stock symbols
v40 = pd.read_csv("data/v40_companies.csv")
v40_list = v40["Symbol"].dropna().unique().tolist()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "V40 Moving Average Strategy Dashboard"

# Fetch initial signals
signals_df = get_signals(v40_list)
signals_data = signals_df.to_dict("records")

app.layout = dbc.Container(
    [
        html.H2("📈 V40 Moving Average Strategy Dashboard"),
        html.Hr(),
        html.H4("Stock Signals"),
        dcc.Store(id="signals-store", data=signals_data),
        dcc.Store(id="portfolio-update-store"),
        dcc.Store(id="portfolio-reset-store"),
        dash_table.DataTable(
            id="signals-table",
            columns=[{"name": i, "id": i} for i in signals_df.columns],
            data= signals_data,
            style_data_conditional=[
                {
                    "if": {"filter_query": '{Signal} = "Buy"', "column_id": "Signal"},
                    "backgroundColor": "#b6f0b6",
                    "color": "green",
                },
                {
                    "if": {"filter_query": '{Signal} = "Sell"', "column_id": "Signal"},
                    "backgroundColor": "#f0b6b6",
                    "color": "red",
                },
                {
                    "if": {"filter_query": '{Signal} = "Hold"', "column_id": "Signal"},
                    "backgroundColor": "#f0f0f0",
                    "color": "grey",
                },
            ],
            style_table={"overflowX": "auto"},
            page_size=20,
        ),
        html.Br(),
        dcc.Loading(
            id="loading-main",
            type="circle",
            fullscreen=True,
            children=[
                html.H4("Buy Stocks"),
                html.Div(id="buy-stocks-div"),
                html.Br(),
                html.H4("Sell Stocks"),
                html.Div(id="sell-stocks-div"),
                html.Br(),
                dbc.Button(
                    "🔄 Reset Portfolio",
                    id="reset-portfolio-btn",
                    color="warning",
                    className="mb-2",
                ),
                html.Div(id="reset-msg"),
                html.H4("Portfolio"),
                html.Div(id="portfolio-div"),
            ],
        ),
    ]
)


# Render Buy Stocks section
@app.callback(
    Output("buy-stocks-div", "children"),
    Input("signals-store", "data"),
    prevent_initial_call=False,
)
def render_buy_stocks(signals_data):
    signals = pd.DataFrame(signals_data)
    buy_signals = signals[signals["Signal"] == "Buy"]
    if buy_signals.empty:
        return dbc.Alert("No Buy signals currently.", color="info")
    rows = []
    for _, row in buy_signals.iterrows():
        symbol = row["Symbol"]
        price = row["Current Price"]
        rows.append(
            dbc.Row(
                [
                    dbc.Col(html.B(symbol), width=2),
                    dbc.Col(f"₹{price:.2f}", width=2),
                    dbc.Col(
                        dcc.Input(
                            id={"type": "qty-input", "index": symbol},
                            type="number",
                            min=1,
                            value=1,
                            style={"width": "80px"},
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Buy",
                            id={"type": "buy-btn", "index": symbol},
                            color="success",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(html.Div(id={"type": "buy-msg", "index": symbol}), width=4),
                ],
                align="center",
                className="mb-2",
            )
        )
    return rows


# Unified Buy/Sell callback to avoid duplicate output errors
@app.callback(
    Output({"type": "buy-msg", "index": dash.ALL}, "children"),
    Output({"type": "sell-msg", "index": dash.ALL}, "children"),
    Output("portfolio-update-store", "data"),
    Input({"type": "buy-btn", "index": dash.ALL}, "n_clicks"),
    Input({"type": "sell-btn", "index": dash.ALL}, "n_clicks"),
    State({"type": "qty-input", "index": dash.ALL}, "value"),
    State("signals-store", "data"),
    State({"type": "sell-btn", "index": dash.ALL}, "id"),
    prevent_initial_call=True,
)
def handle_buy_sell_stock(
    buy_n_clicks, sell_n_clicks, qty_list, signals_data, sell_ids
):
    buy_msgs = ["" for _ in buy_n_clicks]
    sell_msgs = ["" for _ in sell_n_clicks]
    signals = pd.DataFrame(signals_data)

    # Defensive: Only process if a button was actually clicked
    if not ctx.triggered or not ctx.triggered_id:
        return buy_msgs, sell_msgs, time()

    prop_id = ctx.triggered[0]["prop_id"]
    triggered = ctx.triggered_id
    triggered_value = ctx.triggered[0]["value"]

    # Only process if the trigger is a buy button click and n_clicks just incremented
    if (
        isinstance(triggered, dict)
        and triggered.get("type") == "buy-btn"
        and prop_id.endswith(".n_clicks")
        and triggered_value is not None
        and triggered_value > 0
        and buy_n_clicks is not None
        and sum([v for v in buy_n_clicks if v]) > 0
    ):
        symbol = triggered["index"]
        idx = next((i for i, btn_id in enumerate(ctx.inputs_list[0]) if btn_id["id"]["index"] == symbol), None)
        if idx is not None:
            qty = qty_list[idx] if qty_list[idx] else 1
            price = signals[signals["Symbol"] == symbol]["Current Price"].values[0]
            try:
                buy_stock(symbol, price, qty)
                buy_msgs[idx] = f"Bought {qty} shares of {symbol} at ₹{price:.2f}"
            except Exception as e:
                buy_msgs[idx] = str(e)
    # Only process if the trigger is a sell button click and n_clicks just incremented
    elif (
        isinstance(triggered, dict)
        and triggered.get("type") == "sell-btn"
        and prop_id.endswith(".n_clicks")
        and triggered_value is not None
        and triggered_value > 0
        and sell_n_clicks is not None
        and sum([v for v in sell_n_clicks if v]) > 0
    ):
        for i, n_clicks in enumerate(sell_n_clicks):
            if n_clicks:
                symbol = sell_ids[i]["index"]
                try:
                    sell_stock(symbol)
                    sell_msgs[i] = f"Sold all holdings of {symbol}"
                except Exception as e:
                    sell_msgs[i] = str(e)
    return buy_msgs, sell_msgs, time()

# Reset Portfolio
@app.callback(
    Output("reset-msg", "children"),
    Output("portfolio-reset-store", "data"),
    Input("reset-portfolio-btn", "n_clicks"),
    prevent_initial_call=True,
)
def handle_reset_portfolio(n_clicks):
    if n_clicks:
        print("Resetting portfolio...")
        reset_portfolio()
        print("Portfolio reset complete.")
        # Clear the portfolio update store to trigger a refresh
        return dbc.Alert("Portfolio has been reset.", color="success", duration=3000, fade=True), time()
    return "", dash.no_update

# Render Sell Stocks and Portfolio section
@app.callback(
    Output("sell-stocks-div", "children"),
    Output("portfolio-div", "children"),
    Input("portfolio-reset-store", "data"),
    Input("portfolio-update-store", "data"),
    Input("signals-store", "data"),
    prevent_initial_call=False,
)
def render_sell_and_portfolio(_, __, signals_data):
    portfolio = get_portfolio_df(signals_data)
    if portfolio.empty:
        sell_div = dbc.Alert("No holdings available to sell.", color="info")
        port_div = dbc.Alert("Portfolio is empty.", color="info")
        return sell_div, port_div

    holdings = portfolio[portfolio["Status"] == "Holding"]
    sell_rows = []
    for _, row in holdings.iterrows():
        symbol = row["Symbol"]
        current_price = row["Current Price"]
        sell_rows.append(
            dbc.Row(
                [
                    dbc.Col(html.B(symbol), width=2),
                    dbc.Col(f"₹{current_price:.2f}", width=2),
                    dbc.Col(
                        dbc.Button(
                            "Sell",
                            id={"type": "sell-btn", "index": symbol},
                            color="danger",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        html.Div(id={"type": "sell-msg", "index": symbol}), width=6
                    ),
                ],
                align="center",
                className="mb-2",
            )
        )
    sell_div = html.Div(sell_rows)

    port_table = dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in portfolio.columns],
        data=portfolio.to_dict("records"),
        style_data_conditional=[
            {
                "if": {"filter_query": '{Status} = "Sold"'},
                "backgroundColor": "#f2f2f2",
                "color": "grey",
            },
            {
                "if": {"filter_query": '{Status} = "Holding"'},
                "backgroundColor": "#e6ffe6",
                "color": "green",
            },
            {
                "if": {"filter_query": '{P&L} contains "-" && {Status} = "Holding"'},
                "backgroundColor": "#ffe6e6",
                "color": "red",
            }
        ],
        style_table={"overflowX": "auto"},
        page_size=20,
    )
    return sell_div, port_table

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
