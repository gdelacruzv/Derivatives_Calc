# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 18:47:17 2025

@author: gilbe
"""

# return_leg.py

def calculate_total_return(product_type, 
                           notional, 
                           units, 
                           initial_price, 
                           final_price):
    """
    Calculate the Total Return of the underlying asset leg.
    
    Bond TRS:
      (FinalPrice - InitialPrice) * (Notional / 100)
    
    Equity TRS:
      (Units * FinalPrice) - (Units * InitialPrice)
    
    Commodity TRS:
      (Units * FinalPrice) - (Units * InitialPrice)
    """
    if product_type == 'Bond':
        return (final_price - initial_price) * (notional / 100.0)
    
    elif product_type in ['Equity', 'Commodity']:
        return units * (final_price - initial_price)
    
    return 0.0
