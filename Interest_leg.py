import pandas as pd
from helper_functions import fetch_interest_rates, day_count_fraction
from datetime import timedelta

def calculate_interest_leg(product_type,
                           notional,
                           initial_price,
                           start_date,
                           end_date,
                           spread,
                           float_index,      # "SOFR" or "EFFR"
                           reset_frequency,
                           day_count_choice,
                           year_basis,
                           look_back_days=0):
    """
    Calculate the accrued interest (funding leg) for a TRS using the ISDA geometric 
    compounding method (i.e. "Compounding" as defined in the ISDA Definitions), and return:
      1) Total compounded interest (float)
      2) A DataFrame with detailed daily accrual info.

    The returned DataFrame contains the following columns:
      - Accrual Date:          The Reset Date (start of the accrual period).
      - Rate Date:             The Rate Date used for the rate lookup.
      - Accrual Days:          Number of calendar days in the period.
      - Rate:                  The reference rate (index) in decimal form.
      - NCCR:                  The effective rate (index + spread) in decimal form.
      - Daily Factor:          1 + NCCR * Day Count Fraction.
      - Cumulative Factor:     Product of daily factors up to this period.
      - Daily Interest:        Funding_leg_notional * (Current CF - Previous CF).
      - Running Accrued Interest: Funding_leg_notional * (Current CF - 1).

    Args:
      product_type      : "Bond", "Equity", or "Commodity".
      notional          : Notional amount.
      initial_price     : For Bond TRS, the initial dirty price.
      start_date        : Accrual start date (Effective Date).
      end_date          : Accrual end date (Maturity Date).
      spread            : Spread added to the reference rate (decimal, e.g. 0.002 for 0.2%).
      float_index       : "SOFR" or "EFFR".
      reset_frequency   : Reset frequency (e.g. "1D", "1M", "3M", "6M").
      day_count_choice  : Day count convention ("Act" or "30").
      year_basis        : 360 or 365.
      look_back_days    : Number of look-back days.

    Returns:
      (total_interest, df_accrual):
        total_interest (float) - Total compounded interest.
        df_accrual (pd.DataFrame) - Detailed daily accrual table.
    """
    # 1) Determine the funding leg notional.
    if product_type == 'Bond':
        funding_leg_notional = notional * (initial_price / 100.0)
    else:
        funding_leg_notional = notional

    # 2) Fetch daily rates from FRED.
    # The returned DataFrame has columns: ["Reset Date", "Rate Date", "Rate"]
    rates_df = fetch_interest_rates(
        start_date, end_date, 
        index=float_index, 
        look_back_days=look_back_days, 
        reset_frequency=reset_frequency
    )
    
    # For compounding, we want to use the Reset Date as the accrual boundary.
    rates_df['Reset Date'] = pd.to_datetime(rates_df['Reset Date']).dt.date
    rates_df['Rate Date'] = pd.to_datetime(rates_df['Rate Date']).dt.date

    # It’s important that our accrual dates are in order.
    rates_df = rates_df.sort_values('Reset Date').reset_index(drop=True)
    
    # 3) Build the daily accrual breakdown table using geometric compounding.
    table_rows = []
    compound_factor = 1.0  # Starting compound factor
    previous_cf = 1.0      # Store previous compound factor
    
    # Use Reset Date as the accrual date
    accrual_dates = rates_df['Reset Date'].tolist()   # These should be consecutive
    rates_list = rates_df['Rate'].tolist()              # Use the rate from each row
    # We also keep the Rate Date for record-keeping
    rate_dates = rates_df['Rate Date'].tolist()
    
    for i in range(len(accrual_dates) - 1):
        d1 = accrual_dates[i]
        d2 = accrual_dates[i+1]
        r_date = rate_dates[i]  # the rate was looked up on this Rate Date
        
        # Reference rate for the period
        daily_rate = rates_list[i]
        # Effective rate = rate + spread
        effective_rate = daily_rate + spread

        # Number of calendar days in the accrual period
        accrual_days = (d2 - d1).days
        
        # Compute day count fraction using your day_count_fraction function
        dc_fraction = day_count_fraction(d1, d2, day_count=day_count_choice, year_basis=year_basis)
        
        # Compute the daily factor as: 1 + effective_rate * dc_fraction
        daily_factor = 1 + effective_rate * dc_fraction
        
        # Update compound factor (geometric product)
        compound_factor *= daily_factor
        
        # Daily interest is the incremental increase times the funding notional
        daily_interest = funding_leg_notional * (compound_factor - previous_cf)
        
        # Running accrued interest: funding_leg_notional * (compound_factor - 1)
        running_accrued = funding_leg_notional * (compound_factor - 1)
        
        # Record this period’s details
        row_data = {
            "Accrual Date": d1,
            "Rate Date": r_date,
            "Accrual Days": accrual_days,
            "Rate": daily_rate,
            "NCCR": effective_rate,
            "Daily Factor": daily_factor,
            "Cumulative Factor": compound_factor,
            "Daily Interest": daily_interest,
            "Running Accrued Interest": running_accrued
        }
        table_rows.append(row_data)
        
        # Update previous compound factor for the next period.
        previous_cf = compound_factor

    # Create the accrual breakdown DataFrame.
    df_accrual = pd.DataFrame(table_rows)
    
    # Total compounded interest is:
    total_interest = funding_leg_notional * (compound_factor - 1)
    
    return total_interest, df_accrual


# # Example Parameters
# product_type      = "Bond"
# notional          = 50_000_000
# initial_price     = 94.500510
# start_date        = "2023-10-24"
# end_date          = "2023-11-24"
# spread            = 0.002      # 0.2%
# float_index       = "EFFR"
# reset_frequency   = "1D"
# day_count_choice  = "Act"
# year_basis        = 360
# look_back_days    = 2
# # 1) Calculate the interest leg
# total_interest, df_accrual = calculate_interest_leg(
#     product_type      = product_type,
#     notional          = notional,
#     initial_price     = initial_price,
#     start_date        = start_date,
#     end_date          = end_date,
#     spread            = spread,
#     float_index       = float_index,
#     reset_frequency   = reset_frequency,
#     day_count_choice  = day_count_choice,
#     year_basis        = year_basis,
#     look_back_days    = look_back_days
# )

# # 2) Print the total accrued interest
# print("TOTAL ACCRUED INTEREST:", total_interest)

# # 3) Print (or display) the first few rows of the accrual table
# print("\nACCRUAL TABLE (first 10 rows):")
# print(df_accrual.head(10))
