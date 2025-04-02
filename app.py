# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 18:46:09 2025

@author: gilbe
"""

import streamlit as st
from datetime import date, datetime
import pandas as pd
from fredapi import Fred
import requests
import xml.etree.ElementTree as ET
import altair as alt
from dateutil.relativedelta import relativedelta
from ecbdata import ecbdata

# Import your calculation modules
from Interest_leg import calculate_interest_leg
from return_leg import calculate_total_return
from helper_functions import fetch_yfinance_prices

# Initialize Fred (ensure you have your API key set correctly)
fred = Fred(api_key='983188cadf286e4e553982bf2b9b4a1c')

# Add a header title and a link to your LinkedIn profile at the very top.
st.title("Gil De La Cruz Vazquez Derivatives Portofolio")
st.markdown("[LinkedIn](https://www.linkedin.com/in/gil-de-la-cruz-vazquez-62049b125/)")
st.markdown("Sources: US Federal Reserve, European Central Bank & Yahoo Finance")
# Create tabs for TRS Calculator, Economic Dashboard, and FX Forward Valuation
tabs = st.tabs(["FX Derivatives", "Economic Dashboard", "Total Return Swaps Calculator"])

##################################
# TRS Calculator Tab
##################################
with tabs[2]:
    st.title("TRS Settlement Calculator")

    # Select product type
    product_type = st.selectbox("Select Product Type", ["Bond", "Equity", "Commodity"])

    # Common inputs
    col1, col2 = st.columns(2)
    with col1:
        effective_date = st.date_input("Trade Effective Date", value=date.today())
        maturity_date  = st.date_input("Maturity / Final Accrual Date", value=date.today())
        float_index    = st.selectbox("Floating Index", ["SOFR", "FEDFUNDS"])
        # Spread input as a percentage with 5 decimal places, then convert to decimal for calculations.
        spread_percentage = st.number_input("Spread (%)", value=0.20, step=0.00001, format="%.5f")
        spread = spread_percentage / 100.0
    with col2:
        day_count_choice = st.selectbox("Day Count", ["30", "Act"])
        year_basis       = st.selectbox("Year Convention", [360, 365])
        reset_frequency  = st.selectbox("Reset Frequency", ["1D", "1M", "3M", "6M"])
        look_back_days   = st.number_input("Look Back Days", value=2, step=1)
    st.markdown("---")

    def display_and_download_table(df):
        """Utility to display a DataFrame and provide a CSV download button."""
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Accrual Table as CSV",
            data=csv,
            file_name="accrual_table.csv",
            mime="text/csv"
        )

    # Conditional UI based on product type
    if product_type == "Bond":
        notional = st.number_input("Notional ($)", value=1_000_000.0, step=100_000.0, format="%.2f")
        initial_price = st.number_input("Initial Price (Bond) ($)", value=94.500510, step=0.0000001, format="%.7f")
        final_price = st.number_input("Final Price (Bond) ($)", value=100.7395261, step=0.0000001, format="%.7f")
        if st.button("Calculate Bond TRS"):
            asset_return = calculate_total_return(
                product_type="Bond",
                notional=notional,
                units=0,  # Not used for Bond
                initial_price=initial_price,
                final_price=final_price
            )
            interest_accrued, accrual_df = calculate_interest_leg(
                product_type="Bond",
                notional=notional,
                initial_price=initial_price,
                start_date=effective_date,
                end_date=maturity_date,
                spread=spread,
                float_index=float_index,
                reset_frequency=reset_frequency,
                day_count_choice=day_count_choice,
                year_basis=year_basis,
                look_back_days=look_back_days
            )
            net_value = asset_return - interest_accrued
            st.subheader("Results")
            st.write(f"**Asset Leg (Total Return):** {asset_return:,.2f}")
            st.write(f"**Finance Leg (Interest Accrued):** {interest_accrued:,.2f}")
            st.write(f"**Net (Asset - Interest):** {net_value:,.2f}")
            st.markdown("### Accrual Breakdown")
            display_and_download_table(accrual_df)

    elif product_type == "Equity":
        ticker = st.text_input("Equity Ticker (optional)", value="AAPL")
        units = st.number_input("Number of Units (Shares)", value=1000.0, step=100.0)
        initial_date = st.date_input("Initial Valuation Date", value=date.today())
        final_date = st.date_input("Final Valuation Date", value=date.today())
        if st.button("Calculate Equity TRS"):
            df_prices = fetch_yfinance_prices(ticker, initial_date, final_date)
            if df_prices is not None and not df_prices.empty:
                if "Adj Close" in df_prices.columns:
                    start_price = float(df_prices["Adj Close"].iloc[0])
                    final_price = float(df_prices["Adj Close"].iloc[-1])
                elif "Close" in df_prices.columns:
                    start_price = float(df_prices["Close"].iloc[0])
                    final_price = float(df_prices["Close"].iloc[-1])
                else:
                    st.error("Price data does not contain 'Adj Close' or 'Close' columns.")
                    st.stop()
                st.write(f"**Start Price:** {start_price:,.2f}")
                st.write(f"**Final Price:** {final_price:,.2f}")
                equity_notional = units * start_price
                asset_return = calculate_total_return(
                    product_type="Equity",
                    notional=equity_notional,
                    units=units,
                    initial_price=start_price,
                    final_price=final_price
                )
                interest_accrued, accrual_df = calculate_interest_leg(
                    product_type="Bond",  # or "Equity" if you handle it differently
                    notional=equity_notional,
                    initial_price=start_price,
                    start_date=effective_date,
                    end_date=maturity_date,
                    spread=spread,
                    float_index=float_index,
                    reset_frequency=reset_frequency,
                    day_count_choice=day_count_choice,
                    year_basis=year_basis,
                    look_back_days=look_back_days
                )
                net_value = asset_return - interest_accrued
                st.subheader("Results")
                st.write(f"**Asset Leg (Total Return):** {asset_return:,.2f}")
                st.write(f"**Finance Leg (Interest Accrued):** {interest_accrued:,.2f}")
                st.write(f"**Net (Asset - Interest):** {net_value:,.2f}")
                st.markdown("### Accrual Breakdown")
                display_and_download_table(accrual_df)
            else:
                st.error("Failed to fetch price data. Please check the ticker or date range.")

    else:  # Commodity
        commodity_name = st.text_input("Commodity Name", value="WTI Crude")
        units = st.number_input("Number of Units", value=1000.0, step=100.0)
        initial_date = st.date_input("Initial Valuation Date", value=date.today())
        final_date = st.date_input("Final Valuation Date", value=date.today())
        notional = st.number_input("Notional (if needed)", value=100_000.0, step=10_000.0, format="%.2f")
        if st.button("Calculate Commodity TRS"):
            df_prices = fetch_yfinance_prices(commodity_name, initial_date, final_date)
            if df_prices is not None and not df_prices.empty:
                start_price = df_prices["Adj Close"].iloc[0]
                final_price = df_prices["Adj Close"].iloc[-1]
                st.write(f"**Start Price:** {start_price:,.2f}")
                st.write(f"**Final Price:** {final_price:,.2f}")
                asset_return = calculate_total_return(
                    product_type="Commodity",
                    notional=notional,
                    units=units,
                    initial_price=start_price,
                    final_price=final_price
                )
                interest_accrued, accrual_df = calculate_interest_leg(
                    product_type="Bond",  # or "Commodity" if your logic differs
                    notional=notional,
                    initial_price=start_price,
                    start_date=initial_date,
                    end_date=final_date,
                    spread=spread,
                    float_index=float_index,
                    reset_frequency=reset_frequency,
                    day_count_choice=day_count_choice,
                    year_basis=year_basis,
                    look_back_days=look_back_days
                )
                net_value = asset_return - interest_accrued
                st.subheader("Results")
                st.write(f"**Asset Leg (Total Return):** {asset_return:,.2f}")
                st.write(f"**Finance Leg (Interest Accrued):** {interest_accrued:,.2f}")
                st.write(f"**Net (Asset - Interest):** {net_value:,.2f}")
                st.markdown("### Accrual Breakdown")
                display_and_download_table(accrual_df)
            else:
                st.error("Failed to fetch price data. Please check the commodity name and date range.")



##################################
# Economic Dashboard Tab
##################################
with tabs[1]:
    st.title("Economic Dashboard")
    st.markdown("### Benchmark Interest Rates")
    st.write("Below are some key interest rate metrics and trends:")

    try:
        # Define a date range from January 1, 1982 to today
        start_dt = "1982-01-01"
        end_dt = datetime.today().strftime("%Y-%m-%d")

        # Fetch the series from FRED
        sofr_series = fred.get_series("SOFR", observation_start=start_dt, observation_end=end_dt)
        effr_series = fred.get_series("EFFR", observation_start=start_dt, observation_end=end_dt)

        # Show current rates with their as-of dates
        current_sofr = sofr_series.iloc[-1]
        current_effr = effr_series.iloc[-1]
        sofr_date = sofr_series.index[-1].strftime("%Y-%m-%d")
        effr_date = effr_series.index[-1].strftime("%Y-%m-%d")

        st.metric(label=f"Current SOFR (as of {sofr_date})", value=f"{current_sofr:.4f}")
        st.metric(label=f"Current Fed Funds (FFR) (as of {effr_date})", value=f"{current_effr:.4f}")

        # --- Historical Trends ---
        st.markdown("#### Historical Trends")
        # Convert the series to DataFrames and rename EFFR to FFR
        sofr_df = sofr_series.reset_index()
        sofr_df.columns = ["Date", "SOFR"]
        effr_df = effr_series.reset_index()
        effr_df.columns = ["Date", "FFR"]

        # Merge the two DataFrames on Date using an outer join and forward-fill missing values
        merged_df = pd.merge(sofr_df, effr_df, on="Date", how="outer")
        merged_df.sort_values("Date", inplace=True)
        merged_df.ffill(inplace=True)
        merged_df["Date"] = pd.to_datetime(merged_df["Date"])

        # Let the user select which rates to plot
        selected_rates = st.multiselect(
            "Select Rates to Plot",
            options=["SOFR", "FFR"],
            default=["SOFR", "FFR"]
        )

        # Filter merged_df to only include the selected columns
        if not selected_rates:
            st.warning("Please select at least one rate to plot.")
        else:
            # Melt the DataFrame for Altair plotting using only the selected rates
            filtered_df = merged_df.melt(
                id_vars=["Date"],
                value_vars=selected_rates,
                var_name="Rate_Type",
                value_name="Rate"
            )

            import altair as alt
            chart = alt.Chart(filtered_df).mark_line().encode(
                x=alt.X('Date:T', title='Date'),
                y=alt.Y('Rate:Q', title='Rate'),
                color=alt.Color('Rate_Type:N',
                                scale=alt.Scale(domain=["SOFR", "FFR"], range=["red", "blue"])),
                tooltip=['Date:T', 'Rate:Q', 'Rate_Type:N']
            ).properties(
                title='Historical Trends: SOFR and FFR'
            ).interactive()  # Enable panning and zooming

            st.altair_chart(chart, use_container_width=True)
            
            # Add comment about data source
            st.caption("Source: Federal Reserve Bank of U.S.")

    except Exception as e:
        st.error(f"Error fetching benchmark rate data: {e}")
with tabs[1]:
    st.markdown("### U.S. Treasury Yield Curve Snapshot")
    st.write("Below is the latest snapshot of the U.S. Treasury yield curve:")

    try:
        # Fetch the yield curve XML from the Treasury website
        url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview?data=daily_treasury_yield_curve&field_tdr_date_value=2025"
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns_atom = '{http://www.w3.org/2005/Atom}'
        ns_m = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
        ns_d = '{http://schemas.microsoft.com/ado/2007/08/dataservices}'

        yield_data = []
        for entry in root.findall(f'{ns_atom}entry'):
            content = entry.find(f'{ns_atom}content')
            if content is None:
                continue
            props = content.find(f'{ns_m}properties')
            if props is None:
                continue
            date_elem = props.find(f'{ns_d}NEW_DATE')
            if date_elem is None or not date_elem.text:
                continue
            row = {"NEW_DATE": date_elem.text,
                   "BC_1MONTH": None, "BC_2MONTH": None, "BC_3MONTH": None,
                   "BC_4MONTH": None, "BC_6MONTH": None, "BC_1YEAR": None,
                   "BC_2YEAR": None, "BC_3YEAR": None, "BC_5YEAR": None,
                   "BC_7YEAR": None, "BC_10YEAR": None, "BC_20YEAR": None,
                   "BC_30YEAR": None}
            for k in list(row.keys()):
                if k == "NEW_DATE":
                    continue
                elem = props.find(f'{ns_d}{k}')
                if elem is not None and elem.text is not None:
                    row[k] = float(elem.text)
            yield_data.append(row)

        df_yield = pd.DataFrame(yield_data)
        df_yield["NEW_DATE"] = pd.to_datetime(df_yield["NEW_DATE"])
        if df_yield.empty:
            st.warning("No yield curve data found.")
        else:
            latest_date = df_yield["NEW_DATE"].max()
            latest_row = df_yield.loc[df_yield["NEW_DATE"] == latest_date].squeeze()

            maturity_map = {
                "BC_1MONTH":  (1/12,  "1M"),
                "BC_2MONTH":  (2/12,  "2M"),
                "BC_3MONTH":  (3/12,  "3M"),
                "BC_4MONTH":  (4/12,  "4M"),
                "BC_6MONTH":  (6/12,  "6M"),
                "BC_1YEAR":   (1,     "1Y"),
                "BC_2YEAR":   (2,     "2Y"),
                "BC_3YEAR":   (3,     "3Y"),
                "BC_5YEAR":   (5,     "5Y"),
                "BC_7YEAR":   (7,     "7Y"),
                "BC_10YEAR":  (10,    "10Y"),
                "BC_20YEAR":  (20,    "20Y"),
                "BC_30YEAR":  (30,    "30Y")
            }

            curve_rows = []
            for col, (years, label) in maturity_map.items():
                yield_val = latest_row.get(col)
                if pd.notnull(yield_val):
                    curve_rows.append({
                        "MaturityYears": years,
                        "MaturityLabel": label,
                        "Yield": yield_val
                    })
            curve_df = pd.DataFrame(curve_rows)
            st.write(f"Yield Curve Snapshot for {latest_date.date()}")
            # Plot the yield curve
            chart = (
                alt.Chart(curve_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("MaturityYears:Q", title="Maturity (Years)"),
                    y=alt.Y("Yield:Q", title="Yield (%)"),
                    tooltip=["MaturityLabel:N", "Yield:Q"]
                )
                .properties(title="U.S. Treasury Yield Curve")
                .interactive()
            )
            st.altair_chart(chart, use_container_width=True)
            st.caption("Source: U.S. Treasury.")
    except Exception as e:
        st.error(f"Could not fetch or parse yield curve data: {e}")


##################################
# FX Derivatives Tab
##################################
from dateutil.relativedelta import relativedelta

with tabs[0]:
    st.title("FX Derivatives")
    
    # Choose which FX derivative to calculate
    derivative_type = st.radio(
        "Select FX Derivative",
        options=["FX Forward Contract", "FX Currency Swap"],
        key="fx_deriv_type"
    )
    
    if derivative_type == "FX Forward Contract":
        st.markdown("#### FX Forward Contract Valuation")
        # Forward contract inputs
        forward_start_date = st.date_input("Forward Contract Start Date", value=date(2025, 3, 31), key="fwd_start_date")
        tenor_options = {
            "1M": {"years": 0, "months": 1},
            "3M": {"years": 0, "months": 3},
            "6M": {"years": 0, "months": 6},
            "1Y": {"years": 1, "months": 0}
        }
        selected_tenor = st.selectbox("Select Tenor", list(tenor_options.keys()), index=1, key="forward_tenor")
        delta_params = tenor_options[selected_tenor]
        maturity_date = forward_start_date + relativedelta(years=delta_params["years"],
                                                           months=delta_params["months"])
        st.write(f"**Maturity Date:** {maturity_date.strftime('%Y-%m-%d')}")
        days_contract = (maturity_date - forward_start_date).days
        T = days_contract / 360.0
        st.write(f"**Contract Duration:** {days_contract} days, {T:.4f} years")
        basis_spread = st.number_input("Basis Spread (in decimal)", value=0.0, format="%.4f", key="fwd_basis")
        notional_value = st.number_input("Notional Value", value=1_000_000.0, format="%.2f", key="fwd_notional")
        notional_currency = st.selectbox("Notional Currency", options=["USD", "EUR"], key="fwd_currency")
    
        st.markdown("### Fetching Data")
        # Fetch spot rate from Yahoo Finance (assumed to be in USD/EUR terms where 1 USD = X EUR)
        spot_data = fetch_yfinance_prices("EURUSD=X",
                                          (forward_start_date - pd.Timedelta(days=5)).strftime("%Y-%m-%d"),
                                          forward_start_date.strftime("%Y-%m-%d"))
        if spot_data is not None and not spot_data.empty:
             if "Adj Close" in spot_data.columns:
                 fetched_spot = float(spot_data["Adj Close"].iloc[-1])
             elif "Close" in spot_data.columns:
                 fetched_spot = float(spot_data["Close"].iloc[-1])
             else:
                 fetched_spot = None
        else:
             fetched_spot = None
    
        if fetched_spot is None:
             st.error("Failed to fetch spot rate from Yahoo Finance.")
        else:
             spot_rate = st.number_input("Spot Rate (EUR/USD)", value=fetched_spot, format="%.4f", key="fwd_spot")
             st.metric("Spot Rate (EUR/USD)", f"{spot_rate:.4f}")
    
        # Fetch US Treasury par rate for the selected tenor
        treasury_field_map = {"1M": "BC_1MONTH", "3M": "BC_3MONTH", "6M": "BC_6MONTH", "1Y": "BC_1YEAR"}
        treasury_url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/"
                        "xmlview?data=daily_treasury_yield_curve&field_tdr_date_value=2025")
        try:
             response = requests.get(treasury_url)
             response.raise_for_status()
             root = ET.fromstring(response.content)
             ns_atom = '{http://www.w3.org/2005/Atom}'
             ns_m = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
             ns_d = '{http://schemas.microsoft.com/ado/2007/08/dataservices}'
             yield_data = []
             for entry in root.findall(f'{ns_atom}entry'):
                 content = entry.find(f'{ns_atom}content')
                 if content is None:
                     continue
                 props = content.find(f'{ns_m}properties')
                 if props is None:
                     continue
                 date_elem = props.find(f'{ns_d}NEW_DATE')
                 if date_elem is None or not date_elem.text:
                     continue
                 row = {"NEW_DATE": date_elem.text}
                 field = treasury_field_map.get(selected_tenor)
                 elem = props.find(f'{ns_d}{field}')
                 if elem is not None and elem.text is not None:
                     row[field] = float(elem.text)
                 yield_data.append(row)
             treasury_df = pd.DataFrame(yield_data)
             treasury_df["NEW_DATE"] = pd.to_datetime(treasury_df["NEW_DATE"])
             if treasury_df.empty:
                 us_rate = None
             else:
                 latest_us_row = treasury_df.sort_values("NEW_DATE").iloc[-1]
                 us_rate = latest_us_row[treasury_field_map[selected_tenor]]
        except Exception as e:
             st.error(f"Failed to fetch US Treasury par rate: {e}")
             us_rate = None
    
        if us_rate is None:
             st.error("US Treasury par rate not available.")
        else:
             st.metric(f"US Treasury {selected_tenor} Rate", f"{us_rate:.4f}")
    
        from ecbdata import ecbdata
        ecb_series_map = {
             "1M": "FM.M.U2.EUR.RT.MM.EURIBOR1MD_.HSTA",
             "3M": "FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
             "6M": "FM.M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA",
             "1Y": "FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA"
        }
        try:
             df_ecb = ecbdata.get_series(ecb_series_map[selected_tenor],
                                         start=forward_start_date.strftime("%Y-%m"),
                                         detail="dataonly")
             df_ecb["TIME_PERIOD"] = pd.to_datetime(df_ecb["TIME_PERIOD"])
             if df_ecb.empty:
                 euribor_rate = None
             else:
                 df_ecb = df_ecb.sort_values("TIME_PERIOD")
                 euribor_rate = df_ecb.iloc[-1]["OBS_VALUE"]
        except Exception as e:
             st.error(f"Failed to fetch Euribor rate from ECB using ecbdata: {e}")
             euribor_rate = None
    
        if euribor_rate is None:
             st.error("Euribor rate not available.")
        else:
             st.metric(f"Euribor {selected_tenor} Rate", f"{euribor_rate:.4f}")
    
        if spot_rate is not None and us_rate is not None and euribor_rate is not None:
             # Calculate the forward rate using the Premium/Discount method
             interest_diff = (euribor_rate - us_rate) / 100  
             premium = spot_rate * (interest_diff * (days_contract / 360))
             calculated_forward = spot_rate + premium + basis_spread
             st.markdown("### FX Forward Contract Valuation")
             st.write(f"**Forward Start Date:** {forward_start_date.strftime('%Y-%m-%d')}")
             st.write(f"**Maturity Date:** {maturity_date.strftime('%Y-%m-%d')}")
             st.write(f"**Tenor:** {selected_tenor} ({days_contract} days, {T:.4f} years)")
             st.write(f"**Spot Rate (EUR/USD):** {spot_rate:.4f}")
             st.write(f"**US Treasury {selected_tenor} Rate:** {us_rate:.4f}")
             st.write(f"**Euribor {selected_tenor} Rate:** {euribor_rate:.4f}")
             st.write(f"**Interest Rate Differential (EUR - USD):** {interest_diff:.4f}")
             st.write(f"**Premium/Discount:** {premium:.4f}")
             st.write(f"**Basis Spread:** {basis_spread:.4f}")
             st.write(f"**Calculated Forward Rate (EUR/USD):** {calculated_forward:.4f}")
    
             if notional_currency == "USD":
                 spot_eur = notional_value / spot_rate
                 forward_eur = notional_value / calculated_forward
                 st.write(f"**USD Notional:** ${notional_value:,.2f}")
                 st.write(f"**Spot Equivalent in EUR:** €{spot_eur:,.2f}")
                 st.write(f"**Forward Equivalent in EUR:** €{forward_eur:,.2f}")
                 st.write(f"**Difference (Forward vs Spot):** €{(forward_eur - spot_eur):,.2f}")
             else:
                 spot_usd = notional_value * spot_rate
                 forward_usd = notional_value * calculated_forward
                 st.write(f"**EUR Notional:** €{notional_value:,.2f}")
                 st.write(f"**Spot Equivalent in USD:** ${spot_usd:,.2f}")
                 st.write(f"**Forward Equivalent in USD:** ${forward_usd:,.2f}")
                 st.write(f"**Difference (Forward vs Spot):** ${forward_usd - spot_usd:,.2f}")
    
    elif derivative_type == "FX Currency Swap":
        st.markdown("#### FX Currency Swap Valuation")
        # Define position: which side of the swap you are taking
        position = st.radio("Select Position", options=["Long USD / Short EUR", "Long EUR / Short USD"], key="swap_position")
    
        # Swap Execution Date: when the spot transaction occurs
        swap_date = st.date_input("Swap Execution Date", value=date(2025, 3, 31), key="swap_date")
    
        # Tenor options for the forward reversal leg
        tenor_options_swap = {
            "1M": {"years": 0, "months": 1},
            "3M": {"years": 0, "months": 3},
            "6M": {"years": 0, "months": 6},
            "1Y": {"years": 1, "months": 0}
        }
        selected_tenor_swap = st.selectbox("Select Tenor for Swap", list(tenor_options_swap.keys()), index=1, key="swap_tenor")
    
        delta_params_swap = tenor_options_swap[selected_tenor_swap]
        forward_date = swap_date + relativedelta(years=delta_params_swap["years"],
                                                 months=delta_params_swap["months"])
        st.write(f"**Forward Date (Swap Maturity):** {forward_date.strftime('%Y-%m-%d')}")
    
        # Notional and currency inputs for the swap
        notional_value_swap = st.number_input("Notional Value", value=10_000_000.0, format="%.2f", key="swap_notional")
        notional_currency_swap = st.selectbox("Notional Currency", options=["USD", "EUR"], key="swap_currency")
    
        # Inputs for exchange rates (quoted as USD/EUR, i.e. 1 USD equals X EUR)
        spot_rate_swap = st.number_input("Spot Rate (USD/EUR)", value=0.7194, format="%.4f", key="swap_spot")
        forward_rate_swap = st.number_input("Forward Rate (USD/EUR)", value=0.7163, format="%.4f", key="swap_forward")
    
        st.markdown("### Currency Swap Valuation")
        # In a currency swap, the spot and forward legs occur simultaneously.
        # The calculation is as follows:
        # For USD notional:
        #    - At swap_date, euros paid = USD notional × spot_rate_swap
        #    - At forward_date, euros received = USD notional × forward_rate_swap
        #    - The net difference (in euros) = (forward_rate_swap - spot_rate_swap) × USD notional
        #
        # For EUR notional:
        #    - At swap_date, dollars received = EUR notional / spot_rate_swap
        #    - At forward_date, dollars paid = EUR notional / forward_rate_swap
        #    - The net difference (in dollars) = EUR notional × (1/forward_rate_swap - 1/spot_rate_swap)
    
        if notional_currency_swap == "USD":
            spot_eur_swap = notional_value_swap * spot_rate_swap
            forward_eur_swap = notional_value_swap * forward_rate_swap
            net_diff_eur_swap = forward_eur_swap - spot_eur_swap
            # If the user selects the opposite position, reverse the sign.
            if position == "Long EUR / Short USD":
                net_diff_eur_swap = -net_diff_eur_swap
            net_diff_usd_swap = net_diff_eur_swap / forward_rate_swap
            st.write(f"**USD Notional:** ${notional_value_swap:,.2f}")
            st.write(f"**Spot Transaction (EUR paid):** €{spot_eur_swap:,.2f}")
            st.write(f"**Forward Transaction (EUR received):** €{forward_eur_swap:,.2f}")
            st.write(f"**Net Difference (EUR):** €{net_diff_eur_swap:,.2f}")
            st.write(f"**Net Difference (USD equivalent):** ${net_diff_usd_swap:,.2f}")
        else:  # Notional in EUR
            spot_usd_swap = notional_value_swap / spot_rate_swap
            forward_usd_swap = notional_value_swap / forward_rate_swap
            net_diff_usd_swap = forward_usd_swap - spot_usd_swap
            if position == "Long USD / Short EUR":
                net_diff_usd_swap = -net_diff_usd_swap
            st.write(f"**EUR Notional:** €{notional_value_swap:,.2f}")
            st.write(f"**Spot Transaction (USD received):** ${spot_usd_swap:,.2f}")
            st.write(f"**Forward Transaction (USD paid):** ${forward_usd_swap:,.2f}")
            st.write(f"**Net Difference (USD):** ${net_diff_usd_swap:,.2f}")
    
    # New: Plot Historical EUR/USD Exchange Rate for the FX Derivatives tab
    st.markdown("### Historical EUR/USD Exchange Rate")
    # Use a default range of the last 1 year
    hist_start_date = date.today() - relativedelta(years=1)
    hist_end_date = date.today()
    st.write(f"Plotting data from {hist_start_date.strftime('%Y-%m-%d')} to {hist_end_date.strftime('%Y-%m-%d')}")
    hist_data = fetch_yfinance_prices("EURUSD=X",
                                      hist_start_date.strftime("%Y-%m-%d"),
                                      hist_end_date.strftime("%Y-%m-%d"))
    if hist_data is not None and not hist_data.empty:
         if "Close" in hist_data.columns:
             st.line_chart(hist_data["Close"])
         elif "Adj Close" in hist_data.columns:
             st.line_chart(hist_data["Adj Close"])
         else:
             st.error("Historical data does not contain 'Close' or 'Adj Close' column.")
    else:
         st.error("Failed to fetch historical EUR/USD data from Yahoo Finance.")
