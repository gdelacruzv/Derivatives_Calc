# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 15:56:56 2025

@author: gilbe
"""
# helper_functions.py

# helper_functions.py

# helper_functions.py

import pandas as pd
from datetime import timedelta, datetime
from fredapi import Fred
import yfinance as yf


# Initialize Fred with your personal API key
fred = Fred(api_key='983188cadf286e4e553982bf2b9b4a1c')

def compute_reset_date(dt, reset_frequency="1D"):
    """
    Given a date (dt) and a reset frequency, return the corresponding reset date.
    
    For example:
      - "1D": Daily reset (reset date = dt)
      - "1M": Monthly reset (reset date = first day of the month)
      - "3M": Quarterly reset (reset date = first day of the quarter)
      - "6M": Semi-annual reset (reset date = first day of the half-year period)
    """
    if reset_frequency == "1D":
        return dt
    elif reset_frequency == "1M":
        return dt.replace(day=1)
    elif reset_frequency == "3M":
        # Determine the quarter start month
        month = dt.month
        if month in [1, 2, 3]:
            reset_month = 1
        elif month in [4, 5, 6]:
            reset_month = 4
        elif month in [7, 8, 9]:
            reset_month = 7
        else:
            reset_month = 10
        return dt.replace(month=reset_month, day=1)
    elif reset_frequency == "6M":
        # Semi-annual: Jan and Jul are the resets
        reset_month = 1 if dt.month <= 6 else 7
        return dt.replace(month=reset_month, day=1)
    else:
        # Default fallback: return the date itself
        return dt

def fetch_interest_rates(start_date, end_date, index="SOFR", look_back_days=0, reset_frequency="1D"):
    """
    Fetch daily interest rates from FRED for either SOFR or Effective Fed Funds (EFFR)
    and return a DataFrame with the following columns:
      - Reset Date: The reset date computed from the reset frequency.
      - Rate Date: (Reset Date - look_back_days) which is the date from which the rate is applied.
      - Rate: The interest rate in decimal form. If no rate is available on the computed Rate Date,
              the most recent posted rate is used or clamped to the earliest data point.
    """

    if index.upper() == "SOFR":
        series_id = "SOFR"
    else:
        series_id = "EFFR"

    # Adjust the start date by subtracting look_back_days to ensure coverage
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    start_date_adjusted = start_date - pd.Timedelta(days=180)

    # 1) Pull data from FRED
    data_series = fred.get_series(
        series_id,
        observation_start=start_date_adjusted,
        observation_end=end_date
    )
    # data_series is a Pandas Series indexed by date, with the rate in PERCENT form

    # 2) Reindex to daily frequency and forward-fill missing days
    all_days = pd.date_range(start=start_date_adjusted, end=end_date, freq='D')
    data_series = data_series.reindex(all_days, method='ffill')

    # 3) Convert from percent to decimal
    data_series = data_series / 100.0

    # 4) Build DataFrame for reset dates from original start_date..end_date
    reset_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    df = pd.DataFrame({"Temp Reset Date": reset_dates})
    
    # 4a) Compute the actual Reset Date using your reset_frequency logic
    df["Reset Date"] = df["Temp Reset Date"].apply(lambda dt: compute_reset_date(dt, reset_frequency))
    
    # 5) Compute Rate Date as (Reset Date - look_back_days)
    df["Rate Date"] = df["Reset Date"] - pd.Timedelta(days=look_back_days)

    # 6) Clamp any Rate Date that is earlier than the earliest date in data_series
    earliest_date_in_series = data_series.index.min()
    
    def clamp_date(rd):
        # If the Rate Date is before the earliest data date, clamp it
        if rd < earliest_date_in_series:
            return earliest_date_in_series
        return rd
    
    df["Clamped Rate Date"] = df["Rate Date"].apply(clamp_date)

    # 7) For each Clamped Rate Date, use asof to get the most recent valid observation
    df["Rate"] = df["Clamped Rate Date"].apply(lambda rd: data_series.asof(rd))

    # Rearrange columns
    df = df[["Reset Date", "Rate Date", "Clamped Rate Date", "Rate"]]
    return df


def fetch_yfinance_prices(ticker, start_date, end_date):
    """
    Fetch historical price data for a given ticker (single-name equity or commodity index)
    using the yfinance API.
    
    Args:
      ticker (str): The ticker symbol (e.g. "AAPL" for equities or "GLD" for a commodity index).
      start_date (str or datetime): Start date for historical data (YYYY-MM-DD).
      end_date (str or datetime): End date for historical data (YYYY-MM-DD).
      interval (str): Data interval (default is "1d"). Other options: "1wk", "1mo", etc.
      
    Returns:
      pd.DataFrame: DataFrame containing historical price data with columns such as
                    Open, High, Low, Close, Adj Close, and Volume.
    """
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        return df
    except Exception as e:
        print(f"Error fetching data for ticker {ticker}: {e}")
        return None


def day_count_fraction(start_d, end_d, day_count='Act', year_basis=360):
    """
    Compute the fraction of the year between start_d and end_d 
    given a day_count and year_basis.
    Examples: '30/360', 'Act/360', 'Act/365'.
    """
    delta_days = (end_d - start_d).days
    
    if day_count == '30':
        # Simplified 30/360 approach
        return delta_days / 360.0
    elif day_count == 'Act':
        # Actual/Actual or Actual/360 or Actual/365
        return delta_days / float(year_basis)
    
    # Default fallback
    return delta_days / float(year_basis)

# -------------------------------
# Code to test the function
# -----""
# if __name__ == "__main__":
#     ""
#     # Example test parameters
#     test_start = "2023-10-24"
#     test_end = "2023-11-24"
#     # You can try with different reset frequencies: "1D", "1M", "3M", "6M"
#     test_reset_frequency = "1D"
    
#     # Call the function (using SOFR as an example)
#     # Here, look_back_days is set to 2, so Rate Date = Reset Date - 2 days.
#     rates_df = fetch_interest_rates(test_start, test_end, index="EFFR", look_back_days=2, reset_frequency=test_reset_frequency)
    
#     # Display the DataFrame in the console
#     print("Fetched Interest Rates DataFrame:")
#     print(rates_df)

#     #   # Test yfinance for a single-name equity (e.g., AAPL)
#     # ticker_equity = "AAPL"
#     # equity_data = fetch_yfinance_prices(ticker_equity, test_start, test_end)
#     # print(f"\nPrice data for {ticker_equity}:")
#     # print(equity_data)
    
#     # # Test yfinance for a commodity index (e.g., GLD for gold)
#     # ticker_commodity = "GLD"
#     # commodity_data = fetch_yfinance_prices(ticker_commodity, test_start, test_end)
#     # print(f"\nPrice data for {ticker_commodity}:")
#     # print(commodity_data)