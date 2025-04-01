# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 16:44:11 2025

@author: gilbe
"""
# TEST_Interest_leg.py

from Interest_leg import calculate_interest_leg

# Example Parameters
product_type      = "Bond"
notional          = 50_000_000
initial_price     = 94.500510
start_date        = "2023-10-24"
end_date          = "2024-05-24"
spread            = 0.002      # 0.2%
float_index       = "EFFR"
reset_frequency   = "1D"
day_count_choice  = "Act"
year_basis        = 360
look_back_days    = 2
# 1) Calculate the interest leg
total_interest, df_accrual = calculate_interest_leg(
    product_type      = product_type,
    notional          = notional,
    initial_price     = initial_price,
    start_date        = start_date,
    end_date          = end_date,
    spread            = spread,
    float_index       = float_index,
    reset_frequency   = reset_frequency,
    day_count_choice  = day_count_choice,
    year_basis        = year_basis,
    look_back_days    = look_back_days
)

# 2) Print the total accrued interest
print("TOTAL ACCRUED INTEREST:", total_interest)

# 3) Print (or display) the first few rows of the accrual table
print("\nACCRUAL TABLE (first 10 rows):")
print(df_accrual.head(10))

# 4) Save the accrual table to a CSV file if you want
df_accrual.to_csv("accrual_detail4.csv", index=False)
print("\nAccrual details have been saved to 'accrual_detail4.csv'.")
