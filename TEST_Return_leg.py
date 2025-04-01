# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 18:50:33 2025

@author: gilbe
"""

# test_return_leg.py

from return_leg import calculate_total_return
from helper_functions import fetch_yfinance_prices
import pandas as pd

# ---------------------------
# Bond TRS Test
# ---------------------------
# For a Bond TRS, the total return is computed as:
#   (Final Price - Initial Price) * (Notional / 100)
product_type = "Bond"
notional = 1_000_000.0  # Example notional in currency units
initial_price_bond = 98.50   # For example, bond price (dirty price)
final_price_bond   = 100.00  # Final price
bond_total_return = calculate_total_return(product_type, notional, None, initial_price_bond, final_price_bond)
print("Bond TRS Total Return:", bond_total_return)

# ---------------------------
# Equity TRS Test
# ---------------------------
# For an Equity TRS, the total return is:
#   (Units * Final Price) - (Units * Initial Price)
product_type = "Equity"
units = 5000  # Number of shares
ticker_equity = "AAPL"  # Example equity ticker
# Define date range for pricing
equity_start_date = "2023-10-01"
equity_end_date   = "2023-10-31"
equity_data = fetch_yfinance_prices(ticker_equity, equity_start_date, equity_end_date)

if equity_data is not None and not equity_data.empty:
    # Use the closing price on the first and last available days as initial and final prices
    initial_price_equity = equity_data.iloc[0]['Close']
    final_price_equity   = equity_data.iloc[-1]['Close']
    equity_total_return = calculate_total_return(product_type, None, units, initial_price_equity, final_price_equity)
    print(f"Equity TRS Total Return for {ticker_equity}: {equity_total_return}")
else:
    print(f"No equity data available for {ticker_equity} between {equity_start_date} and {equity_end_date}")

# ---------------------------
# Commodity TRS Test
# ---------------------------
# For a Commodity TRS, the total return is similarly:
#   (Units * Final Price) - (Units * Initial Price)
product_type = "Commodity"
units = 1000  # Example number of commodity units
ticker_commodity = "GLD"  # Example ticker for a commodity index (e.g. gold ETF)
commodity_start_date = "2023-10-01"
commodity_end_date   = "2023-10-31"
commodity_data = fetch_yfinance_prices(ticker_commodity, commodity_start_date, commodity_end_date)

if commodity_data is not None and not commodity_data.empty:
    initial_price_commodity = commodity_data.iloc[0]['Close']
    final_price_commodity   = commodity_data.iloc[-1]['Close']
    commodity_total_return = calculate_total_return(product_type, None, units, initial_price_commodity, final_price_commodity)
    print(f"Commodity TRS Total Return for {ticker_commodity}: {commodity_total_return}")
else:
    print(f"No commodity data available for {ticker_commodity} between {commodity_start_date} and {commodity_end_date}")