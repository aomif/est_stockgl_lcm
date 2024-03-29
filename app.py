import streamlit as st
st.set_page_config(layout="wide")
from PIL import Image
image = Image.open('irpclogo.png')

import datetime as dt
import random
import numpy as np
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings("ignore")
from io import BytesIO
import matplotlib.pyplot as plt


import pandas as pd
from sklearn.model_selection import train_test_split 
from sklearn.ensemble import GradientBoostingClassifier 
from sklearn import metrics 
#from flask import Flask, request, render_template 
import os 
import pickle

import sklearn

import requests
url = 'https://raw.githubusercontent.com/aomif/est_stockgl_lcm/main/Info.xlsx'
#url = 'https://github.com/aomif/est_stockgl_lcm/90ce2f11f686e540d38edff775fb0470926b15c7/Info.xlsx'
myfile = requests.get(url)

#import info table
sell_percent = pd.read_excel(myfile.content, sheet_name = "Sell Percent")
yield_percent = pd.read_excel('Info.xlsx', sheet_name = "Yield Percent")
historical_inv_quan = pd.read_excel('Info.xlsx', sheet_name = "Inventory Quantity")
historical_inv_amount = pd.read_excel('Info.xlsx', sheet_name = "Inventory Amount")
historical_lcm = pd.read_excel('Info.xlsx', sheet_name = "LCM")

# @st.cache
def first_calculation(date,converted_input_all,sell_percent,yield_percent,predicted_transfer_inv_quan,predicted_transfer_inv_amount,historical_inv_quan,historical_inv_amount):
    #select only one period
    date = date
    previous_date = date - relativedelta(months=1)
    next_date = date + relativedelta(months=1)
    delta_day = (next_date - date).days

    #input one period
    input = converted_input_all.loc[converted_input_all['Period'] == date.strftime("%Y-%m-%d")]

    transfer_quan = predicted_transfer_inv_quan.loc[predicted_transfer_inv_quan['Period'] == date.strftime("%Y-%m-%d")]
    transfer_amount = predicted_transfer_inv_amount.loc[predicted_transfer_inv_amount['Period'] == date.strftime("%Y-%m-%d")]

    inv_quan = historical_inv_quan.loc[historical_inv_quan['Period'] == previous_date.strftime("%Y-%m-%d")]
    inv_amount = historical_inv_amount.loc[historical_inv_amount['Period'] == previous_date.strftime("%Y-%m-%d")]

    previous_lcm = historical_lcm.loc[historical_lcm['Period'] == previous_date.strftime("%Y-%m-%d")]

    #input
    fx = input.iloc[0]['Exchange Rate (TH/USD)']
    dubai = input.iloc[0]['Dubai ($/bbl)']
    premium = input.iloc[0]['Premium ($/bbl)']
    market_price = dubai + premium

    #check sell target
    sell_target = input.iloc[0]['Sell Target (kbd)']

    #adjust sell percent
    adjust = 0.8
    cogs_kbd = 0

    while round(cogs_kbd,0) != round(sell_target,0):
      #crude 1st loop
      crude_old_quan = inv_quan.iloc[0]['Crude']
      crude_added_quan = input.iloc[0]['Crude Purchase (bbl)']
      total_before_crude_quan = crude_old_quan + crude_added_quan

      crude_old_amount = inv_amount.iloc[0]['Crude']
      crude_added_amount = input.iloc[0]['Crude Purchase (Baht)']
      total_before_crude_amount = crude_old_amount + crude_added_amount

      #transfer: cal crude run 60% old and 40% added
      crude_to_refinery_quan = input.iloc[0]['Crude Run (bbl)']
      crude_to_refinery_amount = 0.6 * crude_to_refinery_quan * (crude_old_amount/crude_old_quan) + 0.4 * crude_to_refinery_quan * (crude_added_amount/crude_added_quan)

      #transfer ratio
      transfer_ratio = crude_to_refinery_amount/crude_to_refinery_quan/2716.346197

      #check after crude
      if crude_old_quan - crude_to_refinery_quan < 0:
          after_old_crude_quan = 0
          after_new_crude_quan = total_before_crude_quan - crude_old_quan - (crude_to_refinery_quan - crude_old_quan)
      else:
          after_old_crude_quan = crude_old_quan - crude_to_refinery_quan
          after_new_crude_quan = crude_added_quan

      if crude_old_amount - crude_to_refinery_amount < 0:
          after_old_crude_amount = 0
          after_new_crude_amount = total_before_crude_amount - crude_old_amount - (crude_to_refinery_amount - crude_old_amount)
      else:
          after_old_crude_amount = crude_old_amount - crude_to_refinery_amount
          after_new_crude_amount = crude_added_amount

      total_after_crude_quan = after_old_crude_quan + after_new_crude_quan
      total_after_crude_amount = (after_old_crude_amount + after_new_crude_amount) * 0.995 #add loss

      #-------------------------------------------------

      #refinery 1st loop : only input
      refinery_old_quan = inv_quan.iloc[0]['Refinery']
      refinery_added_quan = crude_to_refinery_quan
      total_before_refinery_quan = refinery_old_quan + refinery_added_quan

      refinery_old_amount = inv_amount.iloc[0]['Refinery']
      refinery_added_amount = crude_to_refinery_amount
      total_before_refinery_amount = refinery_old_amount + refinery_added_amount

      #transfer
      refinery_to_lube_quan = transfer_quan.iloc[0]['Refinery -> Lube']
      refinery_to_lube_amount = transfer_amount.iloc[0]['Refinery -> Lube'] * transfer_ratio
      refinery_to_olefin_quan = transfer_quan.iloc[0]['Refinery -> Olefin']
      refinery_to_olefin_amount = transfer_amount.iloc[0]['Refinery -> Olefin'] * transfer_ratio
      refinery_to_polyolefin_quan = transfer_quan.iloc[0]['Refinery -> Polyolefin']
      refinery_to_polyolefin_amount = transfer_amount.iloc[0]['Refinery -> Polyolefin'] * transfer_ratio
      refinery_to_btx_quan = transfer_quan.iloc[0]['Refinery -> BTX']
      refinery_to_btx_amount = transfer_amount.iloc[0]['Refinery -> BTX'] * transfer_ratio

      total_refinery_transfer_quan = refinery_to_lube_quan + refinery_to_olefin_quan + refinery_to_polyolefin_quan + refinery_to_btx_quan
      total_refinery_transfer_amount = refinery_to_lube_amount + refinery_to_olefin_amount + refinery_to_polyolefin_amount + refinery_to_btx_amount

      #-------------------------------------------------

      #lube 1st loop
      lube_old_quan = inv_quan.iloc[0]['Lube']
      lube_added_quan = refinery_to_lube_quan
      total_before_lube_quan = lube_old_quan + lube_added_quan

      lube_old_amount = inv_amount.iloc[0]['Lube']
      lube_added_amount = refinery_to_lube_amount
      total_before_lube_amount = lube_old_amount + lube_added_amount

      #transfer
      lube_to_polystyrenic_quan = transfer_quan.iloc[0]['Lube -> Polystyrenic']
      lube_to_polystyrenic_amount = transfer_amount.iloc[0]['Lube -> Polystyrenic'] * transfer_ratio

      total_lube_transfer_quan = lube_to_polystyrenic_quan
      total_lube_transfer_amount = lube_to_polystyrenic_amount

      #sell
      lube_sell_percent = sell_percent.iloc[0]['Lube'] * adjust
      lube_sell_quan = lube_sell_percent * (total_before_lube_quan - total_lube_transfer_quan)
      lube_sell_amount = lube_sell_percent * (total_before_lube_amount - total_lube_transfer_amount)

      #check after lube
      if lube_old_quan - total_lube_transfer_quan - lube_sell_quan < 0:
          after_old_lube_quan = 0
          after_new_lube_quan = total_before_lube_quan - lube_old_quan - (total_lube_transfer_quan + lube_sell_quan - lube_old_quan)
      else:
          after_old_lube_quan = lube_old_quan - total_lube_transfer_quan - lube_sell_quan
          after_new_lube_quan = lube_added_quan

      if lube_old_amount - total_lube_transfer_amount - lube_sell_amount < 0:
          after_old_lube_amount = 0
          after_new_lube_amount = total_before_lube_amount - lube_old_amount - (total_lube_transfer_amount + lube_sell_amount - lube_old_amount)
      else:
          after_old_lube_amount = lube_old_amount - total_lube_transfer_amount- lube_sell_amount
          after_new_lube_amount = lube_added_amount

      total_after_lube_quan = after_old_lube_quan + after_new_lube_quan
      total_after_lube_amount = (after_old_lube_amount + after_new_lube_amount)

      #-------------------------------------------------

      #olefin 1st loop
      olefin_old_quan = inv_quan.iloc[0]['Olefin']
      olefin_added_quan = refinery_to_olefin_quan
      total_before_olefin_quan = olefin_old_quan + olefin_added_quan

      olefin_old_amount = inv_amount.iloc[0]['Olefin']
      olefin_added_amount = refinery_to_olefin_amount
      total_before_olefin_amount = olefin_old_amount + olefin_added_amount

      #transfer
      olefin_to_polyolefin_quan = transfer_quan.iloc[0]['Olefin -> Polyolefin']
      olefin_to_polyolefin_amount = transfer_amount.iloc[0]['Olefin -> Polyolefin'] * transfer_ratio
      olefin_to_btx_quan = transfer_quan.iloc[0]['Olefin -> BTX']
      olefin_to_btx_amount = transfer_amount.iloc[0]['Olefin -> BTX'] * transfer_ratio
      olefin_to_polystyrenic_quan = transfer_quan.iloc[0]['Olefin -> Polystyrenic']
      olefin_to_polystyrenic_amount = transfer_amount.iloc[0]['Olefin -> Polystyrenic'] * transfer_ratio

      total_olefin_transfer_quan = olefin_to_polyolefin_quan + olefin_to_btx_quan + olefin_to_polystyrenic_quan
      total_olefin_transfer_amount = olefin_to_polyolefin_amount + olefin_to_btx_amount + olefin_to_polystyrenic_amount

      #sell
      olefin_sell_percent = sell_percent.iloc[0]['Olefin'] * adjust
      olefin_sell_quan = olefin_sell_percent * (total_before_olefin_quan - total_olefin_transfer_quan)
      olefin_sell_amount = olefin_sell_percent * (total_before_olefin_amount - total_olefin_transfer_amount)

      #check after olefin
      if olefin_old_quan - total_olefin_transfer_quan - olefin_sell_quan < 0:
          after_old_olefin_quan = 0
          after_new_olefin_quan = total_before_olefin_quan - olefin_old_quan - (total_olefin_transfer_quan + olefin_sell_quan - olefin_old_quan)
      else:
          after_old_olefin_quan = olefin_old_quan - total_olefin_transfer_quan - olefin_sell_quan
          after_new_olefin_quan = olefin_added_quan

      if olefin_old_amount - total_olefin_transfer_amount - olefin_sell_amount < 0:
          after_old_olefin_amount = 0
          after_new_olefin_amount = total_before_olefin_amount - olefin_old_amount - (total_olefin_transfer_amount + olefin_sell_amount - olefin_old_amount)
      else:
          after_old_olefin_amount = olefin_old_amount - total_olefin_transfer_amount - olefin_sell_amount
          after_new_olefin_amount = olefin_added_amount

      total_after_olefin_quan = after_old_olefin_quan + after_new_olefin_quan
      total_after_olefin_amount = (after_old_olefin_amount + after_new_olefin_amount)

      #-------------------------------------------------

      #polyolefin 1st loop
      polyolefin_old_quan = inv_quan.iloc[0]['Polyolefin']
      polyolefin_added_quan = refinery_to_polyolefin_quan + olefin_to_polyolefin_quan
      total_before_polyolefin_quan = polyolefin_old_quan + polyolefin_added_quan

      polyolefin_old_amount = inv_amount.iloc[0]['Polyolefin']
      polyolefin_added_amount = refinery_to_polyolefin_amount + olefin_to_polyolefin_amount
      total_before_polyolefin_amount = polyolefin_old_amount + polyolefin_added_amount

      #sell
      polyolefin_sell_percent = sell_percent.iloc[0]['Polyolefin'] * adjust
      polyolefin_sell_quan = polyolefin_sell_percent * total_before_polyolefin_quan
      polyolefin_sell_amount = polyolefin_sell_percent * total_before_polyolefin_amount

      #check after polyolefin
      if polyolefin_old_quan - polyolefin_sell_quan < 0:
          after_old_polyolefin_quan = 0
          after_new_polyolefin_quan = total_before_polyolefin_quan - polyolefin_old_quan - (polyolefin_sell_quan - polyolefin_old_quan)
      else:
          after_old_polyolefin_quan = polyolefin_old_quan - polyolefin_sell_quan
          after_new_polyolefin_quan = polyolefin_added_quan

      if polyolefin_old_amount - polyolefin_sell_amount < 0:
          after_old_polyolefin_amount = 0
          after_new_polyolefin_amount = total_before_polyolefin_amount - polyolefin_old_amount - (polyolefin_sell_amount - polyolefin_old_amount)
      else:
          after_old_polyolefin_amount = polyolefin_old_amount - polyolefin_sell_amount
          after_new_polyolefin_amount = polyolefin_added_amount

      total_after_polyolefin_quan = after_old_polyolefin_quan + after_new_polyolefin_quan
      total_after_polyolefin_amount = (after_old_polyolefin_amount + after_new_polyolefin_amount)

      #-------------------------------------------------

      #btx 1st loop
      btx_old_quan = inv_quan.iloc[0]['BTX']
      btx_added_quan = refinery_to_btx_quan + olefin_to_btx_quan
      total_before_btx_quan = btx_old_quan + btx_added_quan

      btx_old_amount = inv_amount.iloc[0]['BTX']
      btx_added_amount = refinery_to_btx_amount + olefin_to_btx_amount
      total_before_btx_amount = btx_old_amount + btx_added_amount

      #transfer
      btx_to_polystyrenic_quan = transfer_quan.iloc[0]['BTX -> Polystyrenic']
      btx_to_polystyrenic_amount = transfer_amount.iloc[0]['BTX -> Polystyrenic'] * transfer_ratio

      total_btx_transfer_quan = btx_to_polystyrenic_quan
      total_btx_transfer_amount = btx_to_polystyrenic_amount

      #sell
      btx_sell_percent = sell_percent.iloc[0]['BTX'] * adjust
      btx_sell_quan = btx_sell_percent * (total_before_btx_quan - total_btx_transfer_quan)
      btx_sell_amount = btx_sell_percent * (total_before_btx_amount - total_btx_transfer_amount)

      #check after btx
      if btx_old_quan - total_btx_transfer_quan - btx_sell_quan < 0:
          after_old_btx_quan = 0
          after_new_btx_quan = total_before_btx_quan - btx_old_quan - (total_btx_transfer_quan + btx_sell_quan - btx_old_quan)
      else:
          after_old_btx_quan = btx_old_quan - total_btx_transfer_quan - btx_sell_quan
          after_new_btx_quan = btx_added_quan

      if btx_old_amount - total_btx_transfer_amount - btx_sell_amount < 0:
          after_old_btx_amount = 0
          after_new_btx_amount = total_before_btx_amount - btx_old_amount - (total_btx_transfer_amount + btx_sell_amount - btx_old_amount)
      else:
          after_old_btx_amount = btx_old_amount - total_btx_transfer_amount - btx_sell_amount
          after_new_btx_amount = btx_added_amount

      total_after_btx_quan = after_old_btx_quan + after_new_btx_quan
      total_after_btx_amount = (after_old_btx_amount + after_new_btx_amount)

      #-------------------------------------------------

      #polystyrenic 1st loop
      polystyrenic_old_quan = inv_quan.iloc[0]['Polystyrenic']
      polystyrenic_added_quan = lube_to_polystyrenic_quan + olefin_to_polystyrenic_quan + btx_to_polystyrenic_quan
      total_before_polystyrenic_quan = polystyrenic_old_quan + polystyrenic_added_quan

      polystyrenic_old_amount = inv_amount.iloc[0]['Polystyrenic']
      polystyrenic_added_amount = lube_to_polystyrenic_amount + olefin_to_polystyrenic_amount + btx_to_polystyrenic_amount
      total_before_polystyrenic_amount = polystyrenic_old_amount + polystyrenic_added_amount

      #transfer
      polystyrenic_to_refinery_quan = transfer_quan.iloc[0]['Polystyrenic -> Refinery']
      polystyrenic_to_refinery_amount = transfer_amount.iloc[0]['Polystyrenic -> Refinery'] * transfer_ratio

      total_polystyrenic_transfer_quan = polystyrenic_to_refinery_quan
      total_polystyrenic_transfer_amount = polystyrenic_to_refinery_amount

      #sell
      polystyrenic_sell_percent = sell_percent.iloc[0]['Polystyrenic'] * adjust
      polystyrenic_sell_quan = polystyrenic_sell_percent * (total_before_polystyrenic_quan - total_polystyrenic_transfer_quan)
      polystyrenic_sell_amount = polystyrenic_sell_percent * (total_before_polystyrenic_amount - total_polystyrenic_transfer_amount)

      #check after polystyrenic
      if polystyrenic_old_quan - total_polystyrenic_transfer_quan - polystyrenic_sell_quan < 0:
          after_old_polystyrenic_quan = 0
          after_new_polystyrenic_quan = total_before_polystyrenic_quan - polystyrenic_old_quan - (total_polystyrenic_transfer_quan + polystyrenic_sell_quan - polystyrenic_old_quan)
      else:
          after_old_polystyrenic_quan = polystyrenic_old_quan - total_polystyrenic_transfer_quan - polystyrenic_sell_quan
          after_new_polystyrenic_quan = polystyrenic_added_quan

      if polystyrenic_old_amount - total_polystyrenic_transfer_amount - polystyrenic_sell_amount < 0:
          after_old_polystyrenic_amount = 0
          after_new_polystyrenic_amount = total_before_polystyrenic_amount - polystyrenic_old_amount - (total_polystyrenic_transfer_amount + polystyrenic_sell_amount - polystyrenic_old_amount)
      else:
          after_old_polystyrenic_amount = polystyrenic_old_amount - total_polystyrenic_transfer_amount - polystyrenic_sell_amount
          after_new_polystyrenic_amount = polystyrenic_added_amount

      total_after_polystyrenic_quan = after_old_polystyrenic_quan + after_new_polystyrenic_quan
      total_after_polystyrenic_amount = (after_old_polystyrenic_amount + after_new_polystyrenic_amount)

      #-------------------------------------------------

      #sell
      refinery_sell_percent = sell_percent.iloc[0]['Refinery'] * adjust
      refinery_sell_quan = refinery_sell_percent * (total_before_refinery_quan - total_refinery_transfer_quan)
      refinery_sell_amount = refinery_sell_percent * (total_before_refinery_amount - total_refinery_transfer_amount)

      #check after refinery
      if refinery_old_quan - total_refinery_transfer_quan - refinery_sell_quan < 0:
          after_old_refinery_quan = 0
          after_new_refinery_quan = total_before_refinery_quan - refinery_old_quan - (total_refinery_transfer_quan + refinery_sell_quan - refinery_old_quan)
      else:
          after_old_refinery_quan = refinery_old_quan - total_refinery_transfer_quan - refinery_sell_quan
          after_new_refinery_quan = refinery_added_quan

      if refinery_old_amount - total_refinery_transfer_amount - refinery_sell_amount < 0:
          after_old_refinery_amount = 0
          after_new_refinery_amount = total_before_refinery_amount - refinery_old_amount - (total_refinery_transfer_amount + refinery_sell_amount - refinery_old_amount)
      else:
          after_old_refinery_amount = refinery_old_amount - total_refinery_transfer_amount - refinery_sell_amount
          after_new_refinery_amount = refinery_added_amount

      after_new_refinery_quan = after_new_refinery_quan + polystyrenic_to_refinery_quan
      after_new_refinery_amount = after_new_refinery_amount + polystyrenic_to_refinery_amount

      total_after_refinery_quan = after_old_refinery_quan + after_new_refinery_quan
      total_after_refinery_amount = (after_old_refinery_amount + after_new_refinery_amount)

      #-------------------------------------------------

      global result_all
      global inv_all
      global lcm_all

      #create dataframe to store results
      col = ["Crude Purchase ($/bbl)","Crude Purchase (Mbbl)","Crude Run ($/bbl)","Crude Run (Mbbl)",
            "Market Price ($/bbl)","Inventory Close (Mbbl)","Product Sell (Mbbl)","Crude COGS ($/bbl)",
            "Stock Gain/(Loss) (Market - COGS) ($/bbl)","Inventory Gain/(Loss) (M USD)","Exchange Rate (TH/USD)"]
      result_all = pd.DataFrame(columns = col)

      inv_col = ["Crude Close ($/bbl)","Crude Close (Mbbl)","Refinery Close ($/bbl)","Refinery Close (Mbbl)",
                "Lube  Close ($/bbl)","Lube Close (Mbbl)","Olefin Close ($/bbl)","Olefin Close (Mbbl)",
                "Polyolefin Close ($/bbl)","Polyolefin Close (Mbbl)","BTX Close ($/bbl)","BTX Close (Mbbl)",
                "Polystyrenic Close ($/bbl)","Polystyrenic Close (Mbbl)",]
      inv_all = pd.DataFrame(columns = inv_col)

      lcm_col = ["Crude Close ($/bbl)","FG Close ($/bbl)","LCM in Crude (MBaht)","LCM in FG (MBaht)","Overall LCM (MBaht)","LCM Rev (MBaht)"]
      lcm_all = pd.DataFrame(columns = lcm_col)

      #detail crude in result table
      crude_buy_quan = crude_added_quan
      crude_buy_rate = crude_added_amount / crude_added_quan / fx
      crude_run_quan = crude_to_refinery_quan
      crude_run_rate = crude_to_refinery_amount / crude_to_refinery_quan / fx

      #inventory
      inv_close = total_after_crude_quan + total_after_refinery_quan + total_after_lube_quan + total_after_olefin_quan + total_after_polyolefin_quan + total_after_btx_quan + total_after_polystyrenic_quan

      #cost of goods sold
      cogs_quan = refinery_sell_quan + lube_sell_quan + olefin_sell_quan + polyolefin_sell_quan + btx_sell_quan + polystyrenic_sell_quan
      cogs_amount = refinery_sell_amount + lube_sell_amount + olefin_sell_amount + polyolefin_sell_amount + btx_sell_amount + polystyrenic_sell_amount
      cogs_rate = cogs_amount / cogs_quan / fx

      #stock g/l
      stock_gl_amount = (market_price - cogs_rate) * cogs_quan / 1000000
      stock_gl = stock_gl_amount * 1000000 / crude_to_refinery_quan

      result = pd.DataFrame([[crude_buy_rate,crude_buy_quan/1000000,crude_run_rate,crude_run_quan/1000000,market_price,inv_close/1000000,cogs_quan/1000000,cogs_rate,stock_gl,stock_gl_amount,fx]],
                          index = [date.strftime("%b-%y")], columns = col)
      result_all = pd.concat([result_all,result])

      #-------------------------------------------------

      #inventory data
      inv = pd.DataFrame([[total_after_crude_amount/total_after_crude_quan/fx , total_after_crude_quan/1000000,
                          total_after_refinery_amount/total_after_refinery_quan/fx , total_after_refinery_quan/1000000,
                          total_after_lube_amount/total_after_lube_quan/fx , total_after_lube_quan/1000000,
                          total_after_olefin_amount/total_after_olefin_quan/fx , total_after_olefin_quan/1000000,
                          total_after_polyolefin_amount/total_after_polyolefin_quan/fx , total_after_polyolefin_quan/1000000,
                          total_after_btx_amount/total_after_btx_quan/fx , total_after_btx_quan/1000000,
                          total_after_polystyrenic_amount/total_after_polystyrenic_quan/fx , total_after_polystyrenic_quan/1000000]],
                              index = [date.strftime("%b-%y")], columns = inv_col)
      inv_all = pd.concat([inv_all,inv])

      #-------------------------------------------------

      #refinery
      lcm_refinery = (market_price - (total_after_refinery_amount/total_after_refinery_quan/fx)) * total_after_refinery_quan * fx / 1000000
      if lcm_refinery > 0:
          lcm_refinery = 0

      #lube
      lcm_lube = (market_price - (total_after_lube_amount/total_after_lube_quan/fx)) * total_after_lube_quan * fx / 1000000
      if lcm_lube > 0:
          lcm_lube = 0

      #olefin
      lcm_olefin = (market_price - (total_after_olefin_amount/total_after_olefin_quan/fx)) * total_after_olefin_quan * fx / 1000000
      if lcm_olefin > 0:
          lcm_olefin = 0

      #polyolefin
      lcm_polyolefin = (market_price - (total_after_polyolefin_amount/total_after_polyolefin_quan/fx)) * total_after_polyolefin_quan * fx / 1000000
      if lcm_polyolefin > 0:
          lcm_polyolefin = 0

      #btx
      lcm_btx = (market_price - (total_after_btx_amount/total_after_btx_quan/fx)) * total_after_btx_quan * fx / 1000000
      if lcm_btx > 0:
          lcm_btx = 0

      #polystyrenic
      lcm_polystyrenic = (market_price - (total_after_polystyrenic_amount/total_after_polystyrenic_quan/fx)) * total_after_polystyrenic_quan * fx / 1000000
      if lcm_polystyrenic > 0:
          lcm_polystyrenic = 0

      #total FG
      lcm_fg = lcm_refinery + lcm_lube + lcm_olefin + lcm_polyolefin + lcm_btx + lcm_polystyrenic

      market_GIM = input.iloc[0]['Market GIM ($/bbl)']
      market_GIM_amount = market_GIM * fx * (inv_close - total_after_crude_quan)/1000000
      market_GIM_amount_in_fg = market_GIM_amount * 0.36

      lcm_fg = lcm_fg + (market_GIM_amount_in_fg * 0.5)
      if lcm_fg > 0:
          lcm_fg = 0

      #crude
      lcm_crude = (market_price - (total_after_crude_amount/total_after_crude_quan/fx)) * total_after_crude_quan * fx / 1000000

      #production yield
      refinery_yield = yield_percent.iloc[0]['Refinery']
      lube_yield = yield_percent.iloc[0]['Lube']
      olefin_yield = yield_percent.iloc[0]['Olefin']
      polyolefin_yield = yield_percent.iloc[0]['Polyolefin']
      btx_yield = yield_percent.iloc[0]['BTX']
      polystyrenic_yield = yield_percent.iloc[0]['Polystyrenic']

      lcm_fg_list = [lcm_refinery,lcm_lube,lcm_olefin,lcm_polyolefin,lcm_btx,lcm_polystyrenic]
      yield_list = [refinery_yield,lube_yield,olefin_yield,polyolefin_yield,btx_yield,polystyrenic_yield]
      total_lcm_yield = 0

      for i in range(len(lcm_fg_list)):
          if lcm_fg_list[i] < 0:
              total_lcm_yield = total_lcm_yield + yield_list[i]

      lcm_crude = total_lcm_yield * lcm_crude
      if lcm_crude > 0:
          lcm_crude = 0

      total_lcm = lcm_crude + lcm_fg

      #reversed lcm
      rev_lcm = total_lcm - (previous_lcm.iloc[0]['LCM']/ 1000000)

      #inv cost
      crude_cost = total_after_crude_amount/total_after_crude_quan/fx
      fg_cost = (total_after_refinery_amount + total_after_lube_amount + total_after_olefin_amount + total_after_polyolefin_amount + 
                total_after_btx_amount + total_after_polystyrenic_amount) / (total_after_refinery_quan + total_after_lube_quan  + 
                total_after_olefin_quan  + total_after_polyolefin_quan  +  total_after_btx_quan  + total_after_polystyrenic_quan ) / fx

      lcm = pd.DataFrame([[crude_cost,fg_cost,lcm_crude,lcm_fg,total_lcm,rev_lcm]], index = [date.strftime("%b-%y")], columns = lcm_col)
      lcm_all = pd.concat([lcm_all,lcm])

      #-------------------------------------------------

      cogs_kbd = cogs_quan / 1000 / delta_day
      if round(cogs_kbd,0) != round(sell_target,0):
          if round(cogs_kbd,0) > round(sell_target,0):
              adjust = random.uniform (0.3,adjust)
          else:
              adjust = random.uniform(adjust,1.5)

    #collect data for being old value in next loop
    previous_his_col = ["Crude","Refinery","Lube","Olefin","Polyolefin","BTX","Polystyrenic"]
    previous_historical_quan = pd.DataFrame([[total_after_crude_quan,total_after_refinery_quan,total_after_lube_quan,total_after_olefin_quan,
                                            total_after_polyolefin_quan,total_after_btx_quan,total_after_polystyrenic_quan]],
                                          columns = previous_his_col)
    previous_historical_amount = pd.DataFrame([[total_after_crude_amount,total_after_refinery_amount,total_after_lube_amount,total_after_olefin_amount,
                                            total_after_polyolefin_amount,total_after_btx_amount,total_after_polystyrenic_amount]],
                                          columns = previous_his_col)

    return result_all, inv_all, lcm_all, previous_historical_quan, previous_historical_amount

    
# @st.cache
def loop_calculation(date,converted_input_all,sell_percent,yield_percent,predicted_transfer_inv_quan,predicted_transfer_inv_amount,
                     previous_historical_quan,previous_historical_amount,result_all,inv_all,lcm_all):
    #select only one period
    date = date
    previous_date = date - relativedelta(months=1)
    next_date = date + relativedelta(months=1)
    delta_day = (next_date - date).days

    #inventory from previous loop
    crude_old_quan = previous_historical_quan.iloc[0]['Crude']
    crude_old_amount = previous_historical_amount.iloc[0]['Crude']
    refinery_old_quan = previous_historical_quan.iloc[0]['Refinery']
    refinery_old_amount = previous_historical_amount.iloc[0]['Refinery']
    lube_old_quan = previous_historical_quan.iloc[0]['Lube']
    lube_old_amount = previous_historical_amount.iloc[0]['Lube']
    olefin_old_quan = previous_historical_quan.iloc[0]['Olefin']
    olefin_old_amount = previous_historical_amount.iloc[0]['Olefin']
    polyolefin_old_quan = previous_historical_quan.iloc[0]['Polyolefin']
    polyolefin_old_amount = previous_historical_amount.iloc[0]['Polyolefin']
    btx_old_quan = previous_historical_quan.iloc[0]['BTX']
    btx_old_amount = previous_historical_amount.iloc[0]['BTX']
    polystyrenic_old_quan = previous_historical_quan.iloc[0]['Polystyrenic']
    polystyrenic_old_amount = previous_historical_amount.iloc[0]['Polystyrenic']

    #input one period
    input = converted_input_all.loc[converted_input_all['Period'] == date.strftime("%Y-%m-%d")]

    transfer_quan = predicted_transfer_inv_quan.loc[predicted_transfer_inv_quan['Period'] == date.strftime("%Y-%m-%d")]
    transfer_amount = predicted_transfer_inv_amount.loc[predicted_transfer_inv_amount['Period'] == date.strftime("%Y-%m-%d")]

    previous_lcm = lcm_all.loc[previous_date.strftime("%b-%y"), 'Overall LCM (MBaht)']

    #input
    fx = input.iloc[0]['Exchange Rate (TH/USD)']
    dubai = input.iloc[0]['Dubai ($/bbl)']
    premium = input.iloc[0]['Premium ($/bbl)']
    market_price = dubai + premium

    #check sell target
    sell_target = input.iloc[0]['Sell Target (kbd)']

    #adjust sell percent
    adjust = 1
    cogs_kbd = 0

    #-------------------------------------------------

    while round(cogs_kbd,0) != round(sell_target,0):
        #crude following loop
        crude_added_quan = input.iloc[0]['Crude Purchase (bbl)']
        total_before_crude_quan = crude_old_quan + crude_added_quan

        crude_added_amount = input.iloc[0]['Crude Purchase (Baht)']
        total_before_crude_amount = crude_old_amount + crude_added_amount

        #transfer: cal crude run 60% old and 40% added
        crude_to_refinery_quan = input.iloc[0]['Crude Run (bbl)']
        crude_to_refinery_amount = 0.6 * crude_to_refinery_quan * (crude_old_amount/crude_old_quan) + 0.4 * crude_to_refinery_quan * (crude_added_amount/crude_added_quan)

        #transfer ratio
        transfer_ratio = crude_to_refinery_amount/crude_to_refinery_quan/2716.346197

        #check after crude
        if crude_old_quan - crude_to_refinery_quan < 0:
            after_old_crude_quan = 0
            after_new_crude_quan = total_before_crude_quan - crude_old_quan - (crude_to_refinery_quan - crude_old_quan)
        else:
            after_old_crude_quan = crude_old_quan - crude_to_refinery_quan
            after_new_crude_quan = crude_added_quan

        if crude_old_amount - crude_to_refinery_amount < 0:
            after_old_crude_amount = 0
            after_new_crude_amount = total_before_crude_amount - crude_old_amount - (crude_to_refinery_amount - crude_old_amount)
        else:
            after_old_crude_amount = crude_old_amount - crude_to_refinery_amount
            after_new_crude_amount = crude_added_amount

        total_after_crude_quan = after_old_crude_quan + after_new_crude_quan
        total_after_crude_amount = (after_old_crude_amount + after_new_crude_amount)

        #-------------------------------------------------

        #refinery following loop : only input
        refinery_added_quan = crude_to_refinery_quan
        total_before_refinery_quan = refinery_old_quan + refinery_added_quan

        refinery_added_amount = crude_to_refinery_amount
        total_before_refinery_amount = refinery_old_amount + refinery_added_amount

        #transfer
        refinery_to_lube_quan = transfer_quan.iloc[0]['Refinery -> Lube']
        refinery_to_lube_amount = transfer_amount.iloc[0]['Refinery -> Lube'] * transfer_ratio
        refinery_to_olefin_quan = transfer_quan.iloc[0]['Refinery -> Olefin']
        refinery_to_olefin_amount = transfer_amount.iloc[0]['Refinery -> Olefin'] * transfer_ratio
        refinery_to_polyolefin_quan = transfer_quan.iloc[0]['Refinery -> Polyolefin']
        refinery_to_polyolefin_amount = transfer_amount.iloc[0]['Refinery -> Polyolefin'] * transfer_ratio
        refinery_to_btx_quan = transfer_quan.iloc[0]['Refinery -> BTX']
        refinery_to_btx_amount = transfer_amount.iloc[0]['Refinery -> BTX'] * transfer_ratio

        total_refinery_transfer_quan = refinery_to_lube_quan + refinery_to_olefin_quan + refinery_to_polyolefin_quan + refinery_to_btx_quan
        total_refinery_transfer_amount = refinery_to_lube_amount + refinery_to_olefin_amount + refinery_to_polyolefin_amount + refinery_to_btx_amount

        #-------------------------------------------------

        #lube following loop
        lube_added_quan = refinery_to_lube_quan
        total_before_lube_quan = lube_old_quan + lube_added_quan

        lube_added_amount = refinery_to_lube_amount
        total_before_lube_amount = lube_old_amount + lube_added_amount

        #transfer
        lube_to_polystyrenic_quan = transfer_quan.iloc[0]['Lube -> Polystyrenic']
        lube_to_polystyrenic_amount = transfer_amount.iloc[0]['Lube -> Polystyrenic'] * transfer_ratio

        total_lube_transfer_quan = lube_to_polystyrenic_quan
        total_lube_transfer_amount = lube_to_polystyrenic_amount

        #sell
        lube_sell_percent = sell_percent.iloc[0]['Lube'] * adjust
        lube_sell_quan = lube_sell_percent * (total_before_lube_quan - total_lube_transfer_quan)
        lube_sell_amount = lube_sell_percent * (total_before_lube_amount - total_lube_transfer_amount)

        #check after lube
        if lube_old_quan - total_lube_transfer_quan - lube_sell_quan < 0:
            after_old_lube_quan = 0
            after_new_lube_quan = total_before_lube_quan - lube_old_quan - (total_lube_transfer_quan + lube_sell_quan - lube_old_quan)
        else:
            after_old_lube_quan = lube_old_quan - total_lube_transfer_quan - lube_sell_quan
            after_new_lube_quan = lube_added_quan

        if lube_old_amount - total_lube_transfer_amount - lube_sell_amount < 0:
            after_old_lube_amount = 0
            after_new_lube_amount = total_before_lube_amount - lube_old_amount - (total_lube_transfer_amount + lube_sell_amount - lube_old_amount)
        else:
            after_old_lube_amount = lube_old_amount - total_lube_transfer_amount- lube_sell_amount
            after_new_lube_amount = lube_added_amount

        total_after_lube_quan = after_old_lube_quan + after_new_lube_quan
        total_after_lube_amount = (after_old_lube_amount + after_new_lube_amount)

        #-------------------------------------------------

        #olefin following loop
        olefin_added_quan = refinery_to_olefin_quan
        total_before_olefin_quan = olefin_old_quan + olefin_added_quan

        olefin_added_amount = refinery_to_olefin_amount
        total_before_olefin_amount = olefin_old_amount + olefin_added_amount

        #transfer
        olefin_to_polyolefin_quan = transfer_quan.iloc[0]['Olefin -> Polyolefin']
        olefin_to_polyolefin_amount = transfer_amount.iloc[0]['Olefin -> Polyolefin'] * transfer_ratio
        olefin_to_btx_quan = transfer_quan.iloc[0]['Olefin -> BTX']
        olefin_to_btx_amount = transfer_amount.iloc[0]['Olefin -> BTX'] * transfer_ratio
        olefin_to_polystyrenic_quan = transfer_quan.iloc[0]['Olefin -> Polystyrenic']
        olefin_to_polystyrenic_amount = transfer_amount.iloc[0]['Olefin -> Polystyrenic'] * transfer_ratio

        total_olefin_transfer_quan = olefin_to_polyolefin_quan + olefin_to_btx_quan + olefin_to_polystyrenic_quan
        total_olefin_transfer_amount = olefin_to_polyolefin_amount + olefin_to_btx_amount + olefin_to_polystyrenic_amount

        #sell
        olefin_sell_percent = sell_percent.iloc[0]['Olefin'] * adjust
        olefin_sell_quan = olefin_sell_percent * (total_before_olefin_quan - total_olefin_transfer_quan)
        olefin_sell_amount = olefin_sell_percent * (total_before_olefin_amount - total_olefin_transfer_amount)

        #check after olefin
        if olefin_old_quan - total_olefin_transfer_quan - olefin_sell_quan < 0:
            after_old_olefin_quan = 0
            after_new_olefin_quan = total_before_olefin_quan - olefin_old_quan - (total_olefin_transfer_quan + olefin_sell_quan - olefin_old_quan)
        else:
            after_old_olefin_quan = olefin_old_quan - total_olefin_transfer_quan - olefin_sell_quan
            after_new_olefin_quan = olefin_added_quan

        if olefin_old_amount - total_olefin_transfer_amount - olefin_sell_amount < 0:
            after_old_olefin_amount = 0
            after_new_olefin_amount = total_before_olefin_amount - olefin_old_amount - (total_olefin_transfer_amount + olefin_sell_amount - olefin_old_amount)
        else:
            after_old_olefin_amount = olefin_old_amount - total_olefin_transfer_amount - olefin_sell_amount
            after_new_olefin_amount = olefin_added_amount

        total_after_olefin_quan = after_old_olefin_quan + after_new_olefin_quan
        total_after_olefin_amount = (after_old_olefin_amount + after_new_olefin_amount)

        #-------------------------------------------------

        #polyolefin following loop
        polyolefin_added_quan = refinery_to_polyolefin_quan + olefin_to_polyolefin_quan
        total_before_polyolefin_quan = polyolefin_old_quan + polyolefin_added_quan

        polyolefin_added_amount = refinery_to_polyolefin_amount + olefin_to_polyolefin_amount
        total_before_polyolefin_amount = polyolefin_old_amount + polyolefin_added_amount

        #sell
        polyolefin_sell_percent = sell_percent.iloc[0]['Polyolefin'] * adjust
        polyolefin_sell_quan = polyolefin_sell_percent * total_before_polyolefin_quan
        polyolefin_sell_amount = polyolefin_sell_percent * total_before_polyolefin_amount

        #check after polyolefin
        if polyolefin_old_quan - polyolefin_sell_quan < 0:
            after_old_polyolefin_quan = 0
            after_new_polyolefin_quan = total_before_polyolefin_quan - polyolefin_old_quan - (polyolefin_sell_quan - polyolefin_old_quan)
        else:
            after_old_polyolefin_quan = polyolefin_old_quan - polyolefin_sell_quan
            after_new_polyolefin_quan = polyolefin_added_quan

        if polyolefin_old_amount - polyolefin_sell_amount < 0:
            after_old_polyolefin_amount = 0
            after_new_polyolefin_amount = total_before_polyolefin_amount - polyolefin_old_amount - (polyolefin_sell_amount - polyolefin_old_amount)
        else:
            after_old_polyolefin_amount = polyolefin_old_amount - polyolefin_sell_amount
            after_new_polyolefin_amount = polyolefin_added_amount

        total_after_polyolefin_quan = after_old_polyolefin_quan + after_new_polyolefin_quan
        total_after_polyolefin_amount = (after_old_polyolefin_amount + after_new_polyolefin_amount)

        #-------------------------------------------------

        #btx following loop
        btx_added_quan = refinery_to_btx_quan + olefin_to_btx_quan
        total_before_btx_quan = btx_old_quan + btx_added_quan

        btx_added_amount = refinery_to_btx_amount + olefin_to_btx_amount
        total_before_btx_amount = btx_old_amount + btx_added_amount

        #transfer
        btx_to_polystyrenic_quan = transfer_quan.iloc[0]['BTX -> Polystyrenic']
        btx_to_polystyrenic_amount = transfer_amount.iloc[0]['BTX -> Polystyrenic'] * transfer_ratio

        total_btx_transfer_quan = btx_to_polystyrenic_quan
        total_btx_transfer_amount = btx_to_polystyrenic_amount

        #sell
        btx_sell_percent = sell_percent.iloc[0]['BTX'] * adjust
        btx_sell_quan = btx_sell_percent * (total_before_btx_quan - total_btx_transfer_quan)
        btx_sell_amount = btx_sell_percent * (total_before_btx_amount - total_btx_transfer_amount)

        #check after btx
        if btx_old_quan - total_btx_transfer_quan - btx_sell_quan < 0:
            after_old_btx_quan = 0
            after_new_btx_quan = total_before_btx_quan - btx_old_quan - (total_btx_transfer_quan + btx_sell_quan - btx_old_quan)
        else:
            after_old_btx_quan = btx_old_quan - total_btx_transfer_quan - btx_sell_quan
            after_new_btx_quan = btx_added_quan

        if btx_old_amount - total_btx_transfer_amount - btx_sell_amount < 0:
            after_old_btx_amount = 0
            after_new_btx_amount = total_before_btx_amount - btx_old_amount - (total_btx_transfer_amount + btx_sell_amount - btx_old_amount)
        else:
            after_old_btx_amount = btx_old_amount - total_btx_transfer_amount - btx_sell_amount
            after_new_btx_amount = btx_added_amount

        total_after_btx_quan = after_old_btx_quan + after_new_btx_quan
        total_after_btx_amount = (after_old_btx_amount + after_new_btx_amount)

        #-------------------------------------------------

        #polystyrenic following loop
        polystyrenic_added_quan = lube_to_polystyrenic_quan + olefin_to_polystyrenic_quan + btx_to_polystyrenic_quan
        total_before_polystyrenic_quan = polystyrenic_old_quan + polystyrenic_added_quan

        polystyrenic_added_amount = lube_to_polystyrenic_amount + olefin_to_polystyrenic_amount + btx_to_polystyrenic_amount
        total_before_polystyrenic_amount = polystyrenic_old_amount + polystyrenic_added_amount

        #transfer
        polystyrenic_to_refinery_quan = transfer_quan.iloc[0]['Polystyrenic -> Refinery']
        polystyrenic_to_refinery_amount = transfer_amount.iloc[0]['Polystyrenic -> Refinery'] * transfer_ratio

        total_polystyrenic_transfer_quan = polystyrenic_to_refinery_quan
        total_polystyrenic_transfer_amount = polystyrenic_to_refinery_amount

        #sell
        polystyrenic_sell_percent = sell_percent.iloc[0]['Polystyrenic'] * adjust
        polystyrenic_sell_quan = polystyrenic_sell_percent * (total_before_polystyrenic_quan - total_polystyrenic_transfer_quan)
        polystyrenic_sell_amount = polystyrenic_sell_percent * (total_before_polystyrenic_amount - total_polystyrenic_transfer_amount)

        #check after polystyrenic
        if polystyrenic_old_quan - total_polystyrenic_transfer_quan - polystyrenic_sell_quan < 0:
            after_old_polystyrenic_quan = 0
            after_new_polystyrenic_quan = total_before_polystyrenic_quan - polystyrenic_old_quan - (total_polystyrenic_transfer_quan + polystyrenic_sell_quan - polystyrenic_old_quan)
        else:
            after_old_polystyrenic_quan = polystyrenic_old_quan - total_polystyrenic_transfer_quan - polystyrenic_sell_quan
            after_new_polystyrenic_quan = polystyrenic_added_quan

        if polystyrenic_old_amount - total_polystyrenic_transfer_amount - polystyrenic_sell_amount < 0:
            after_old_polystyrenic_amount = 0
            after_new_polystyrenic_amount = total_before_polystyrenic_amount - polystyrenic_old_amount - (total_polystyrenic_transfer_amount + polystyrenic_sell_amount - polystyrenic_old_amount)
        else:
            after_old_polystyrenic_amount = polystyrenic_old_amount - total_polystyrenic_transfer_amount - polystyrenic_sell_amount
            after_new_polystyrenic_amount = polystyrenic_added_amount

        total_after_polystyrenic_quan = after_old_polystyrenic_quan + after_new_polystyrenic_quan
        total_after_polystyrenic_amount = (after_old_polystyrenic_amount + after_new_polystyrenic_amount)

        #-------------------------------------------------

        #sell
        refinery_sell_percent = sell_percent.iloc[0]['Refinery'] * adjust
        refinery_sell_quan = refinery_sell_percent * (total_before_refinery_quan - total_refinery_transfer_quan)
        refinery_sell_amount = refinery_sell_percent * (total_before_refinery_amount - total_refinery_transfer_amount)

        #check after refinery
        if refinery_old_quan - total_refinery_transfer_quan - refinery_sell_quan < 0:
            after_old_refinery_quan = 0
            after_new_refinery_quan = total_before_refinery_quan - refinery_old_quan - (total_refinery_transfer_quan + refinery_sell_quan - refinery_old_quan)
        else:
            after_old_refinery_quan = refinery_old_quan - total_refinery_transfer_quan - refinery_sell_quan
            after_new_refinery_quan = refinery_added_quan

        if refinery_old_amount - total_refinery_transfer_amount - refinery_sell_amount < 0:
            after_old_refinery_amount = 0
            after_new_refinery_amount = total_before_refinery_amount - refinery_old_amount - (total_refinery_transfer_amount + refinery_sell_amount - refinery_old_amount)
        else:
            after_old_refinery_amount = refinery_old_amount - total_refinery_transfer_amount - refinery_sell_amount
            after_new_refinery_amount = refinery_added_amount

        after_new_refinery_quan = after_new_refinery_quan + polystyrenic_to_refinery_quan
        after_new_refinery_amount = after_new_refinery_amount + polystyrenic_to_refinery_amount

        total_after_refinery_quan = after_old_refinery_quan + after_new_refinery_quan
        total_after_refinery_amount = (after_old_refinery_amount + after_new_refinery_amount)

        #-------------------------------------------------

        global result
        global inv
        global lcm

        #detail crude in result table
        crude_buy_quan = crude_added_quan
        crude_buy_rate = crude_added_amount / crude_added_quan / fx
        crude_run_quan = crude_to_refinery_quan
        crude_run_rate = crude_to_refinery_amount / crude_to_refinery_quan / fx

        #inventory
        inv_close = total_after_crude_quan + total_after_refinery_quan + total_after_lube_quan + total_after_olefin_quan + total_after_polyolefin_quan + total_after_btx_quan + total_after_polystyrenic_quan

        #cost of goods sold
        cogs_quan = refinery_sell_quan + lube_sell_quan + olefin_sell_quan + polyolefin_sell_quan + btx_sell_quan + polystyrenic_sell_quan
        cogs_amount = refinery_sell_amount + lube_sell_amount + olefin_sell_amount + polyolefin_sell_amount + btx_sell_amount + polystyrenic_sell_amount
        cogs_rate = cogs_amount / cogs_quan / fx

        #stock g/l
        stock_gl_amount = (market_price - cogs_rate) * cogs_quan / 1000000
        stock_gl = stock_gl_amount * 1000000 / crude_to_refinery_quan

        col = ["Crude Purchase ($/bbl)","Crude Purchase (Mbbl)","Crude Run ($/bbl)","Crude Run (Mbbl)",
              "Market Price ($/bbl)","Inventory Close (Mbbl)","Product Sell (Mbbl)","Crude COGS ($/bbl)",
              "Stock Gain/(Loss) (Market - COGS) ($/bbl)","Inventory Gain/(Loss) (M USD)","Exchange Rate (TH/USD)"]
        result = pd.DataFrame([[crude_buy_rate,crude_buy_quan/1000000,crude_run_rate,crude_run_quan/1000000,market_price,inv_close/1000000,cogs_quan/1000000,cogs_rate,stock_gl,stock_gl_amount,fx]],
                            index = [date.strftime("%b-%y")], columns = col)

        #-------------------------------------------------

        #inventory data
        inv_col = ["Crude Close ($/bbl)","Crude Close (Mbbl)","Refinery Close ($/bbl)","Refinery Close (Mbbl)",
                  "Lube  Close ($/bbl)","Lube Close (Mbbl)","Olefin Close ($/bbl)","Olefin Close (Mbbl)",
                  "Polyolefin Close ($/bbl)","Polyolefin Close (Mbbl)","BTX Close ($/bbl)","BTX Close (Mbbl)",
                  "Polystyrenic Close ($/bbl)","Polystyrenic Close (Mbbl)",]
        inv = pd.DataFrame([[total_after_crude_amount/total_after_crude_quan/fx , total_after_crude_quan/1000000,
                            total_after_refinery_amount/total_after_refinery_quan/fx , total_after_refinery_quan/1000000,
                            total_after_lube_amount/total_after_lube_quan/fx , total_after_lube_quan/1000000,
                            total_after_olefin_amount/total_after_olefin_quan/fx , total_after_olefin_quan/1000000,
                            total_after_polyolefin_amount/total_after_polyolefin_quan/fx , total_after_polyolefin_quan/1000000,
                            total_after_btx_amount/total_after_btx_quan/fx , total_after_btx_quan/1000000,
                            total_after_polystyrenic_amount/total_after_polystyrenic_quan/fx , total_after_polystyrenic_quan/1000000]],
                                index = [date.strftime("%b-%y")], columns = inv_col)

        #-------------------------------------------------

        #refinery
        lcm_refinery = (market_price - (total_after_refinery_amount/total_after_refinery_quan/fx)) * total_after_refinery_quan * fx / 1000000
        if lcm_refinery > 0:
            lcm_refinery = 0

        #lube
        lcm_lube = (market_price - (total_after_lube_amount/total_after_lube_quan/fx)) * total_after_lube_quan * fx / 1000000
        if lcm_lube > 0:
            lcm_lube = 0

        #olefin
        lcm_olefin = (market_price - (total_after_olefin_amount/total_after_olefin_quan/fx)) * total_after_olefin_quan * fx / 1000000
        if lcm_olefin > 0:
            lcm_olefin = 0

        #polyolefin
        lcm_polyolefin = (market_price - (total_after_polyolefin_amount/total_after_polyolefin_quan/fx)) * total_after_polyolefin_quan * fx / 1000000
        if lcm_polyolefin > 0:
            lcm_polyolefin = 0

        #btx
        lcm_btx = (market_price - (total_after_btx_amount/total_after_btx_quan/fx)) * total_after_btx_quan * fx / 1000000
        if lcm_btx > 0:
            lcm_btx = 0

        #polystyrenic
        lcm_polystyrenic = (market_price - (total_after_polystyrenic_amount/total_after_polystyrenic_quan/fx)) * total_after_polystyrenic_quan * fx / 1000000
        if lcm_polystyrenic > 0:
            lcm_polystyrenic = 0

        #total FG
        lcm_fg = lcm_refinery + lcm_lube + lcm_olefin + lcm_polyolefin + lcm_btx + lcm_polystyrenic

        market_GIM = input.iloc[0]['Market GIM ($/bbl)']
        market_GIM_amount = market_GIM * fx * (inv_close - total_after_crude_quan)/1000000
        market_GIM_amount_in_fg = market_GIM_amount * 0.36

        lcm_fg = lcm_fg + (market_GIM_amount_in_fg * 0.5)
        if lcm_fg > 0:
            lcm_fg = 0

        #crude
        lcm_crude = (market_price - (total_after_crude_amount/total_after_crude_quan/fx)) * total_after_crude_quan * fx / 1000000

        #production yield
        refinery_yield = yield_percent.iloc[0]['Refinery']
        lube_yield = yield_percent.iloc[0]['Lube']
        olefin_yield = yield_percent.iloc[0]['Olefin']
        polyolefin_yield = yield_percent.iloc[0]['Polyolefin']
        btx_yield = yield_percent.iloc[0]['BTX']
        polystyrenic_yield = yield_percent.iloc[0]['Polystyrenic']

        lcm_fg_list = [lcm_refinery,lcm_lube,lcm_olefin,lcm_polyolefin,lcm_btx,lcm_polystyrenic]
        yield_list = [refinery_yield,lube_yield,olefin_yield,polyolefin_yield,btx_yield,polystyrenic_yield]
        total_lcm_yield = 0

        for i in range(len(lcm_fg_list)):
            if lcm_fg_list[i] < 0:
                total_lcm_yield = total_lcm_yield + yield_list[i]

        lcm_crude = total_lcm_yield * lcm_crude
        if lcm_crude > 0:
            lcm_crude = 0

        total_lcm = lcm_crude + lcm_fg
        rev_lcm = total_lcm - previous_lcm

        #inv cost
        crude_cost = total_after_crude_amount/total_after_crude_quan/fx
        fg_cost = (total_after_refinery_amount + total_after_lube_amount + total_after_olefin_amount + total_after_polyolefin_amount + 
                  total_after_btx_amount + total_after_polystyrenic_amount) / (total_after_refinery_quan + total_after_lube_quan  + 
                  total_after_olefin_quan  + total_after_polyolefin_quan  +  total_after_btx_quan  + total_after_polystyrenic_quan ) / fx

        lcm_col = ["Crude Close ($/bbl)","FG Close ($/bbl)","LCM in Crude (MBaht)","LCM in FG (MBaht)","Overall LCM (MBaht)","LCM Rev (MBaht)"]
        lcm = pd.DataFrame([[crude_cost,fg_cost,lcm_crude,lcm_fg,total_lcm,rev_lcm]], index = [date.strftime("%b-%y")], columns = lcm_col)

        #-------------------------------------------------

        cogs_kbd = cogs_quan / 1000 / delta_day
        if round(cogs_kbd,0) != round(sell_target,0):
            if round(cogs_kbd,0) > round(sell_target,0):
                adjust = random.uniform (0.3,adjust)
            else:
                adjust = random.uniform(adjust,1.5)

    #collect data for being old value in next loop
    previous_his_col = ["Crude","Refinery","Lube","Olefin","Polyolefin","BTX","Polystyrenic"]
    previous_historical_quan = pd.DataFrame([[total_after_crude_quan,total_after_refinery_quan,total_after_lube_quan,total_after_olefin_quan,
                                              total_after_polyolefin_quan,total_after_btx_quan,total_after_polystyrenic_quan]],
                                            columns = previous_his_col)
    previous_historical_amount = pd.DataFrame([[total_after_crude_amount,total_after_refinery_amount,total_after_lube_amount,total_after_olefin_amount,
                                              total_after_polyolefin_amount,total_after_btx_amount,total_after_polystyrenic_amount]],
                                            columns = previous_his_col)
    
    result_all = pd.concat([result_all,result])
    inv_all = pd.concat([inv_all,inv])
    lcm_all = pd.concat([lcm_all,lcm])

    return result_all, inv_all, lcm_all, previous_historical_quan, previous_historical_amount


def to_excel(result_all,inv_all,lcm_all):
    output = BytesIO()
    writer = pd.ExcelWriter(output)
    result_all.to_excel(writer, index = True, sheet_name = 'Result')
    inv_all.to_excel(writer, index = True, sheet_name = 'Inventory')
    lcm_all.to_excel(writer, index = True, sheet_name = 'LCM')
    writer.save()
    final_data = output.getvalue()
    return final_data

def train_model(model_path,scaler_path,input_model):
    model = pickle.load(open(f"{model_path}",'rb'))
    scaler = pickle.load(open(f"{scaler_path}",'rb'))
    scaled_input_model = scaler.transform(input_model)
    y = model.predict(scaled_input_model)
    return y

def eda_amount(new_row_amount,date,plant):
    historical_data = new_row_amount.copy(0)
    historical_data['Dubai TH1'] = historical_data['Dubai'] * historical_data['FX']
    historical_data['Dubai TH2'] = historical_data['Dubai TH1'].shift(1)
    historical_data['Dubai TH3'] = historical_data['Dubai TH1'].shift(2)

    historical_data[plant+'1'] = historical_data[plant]
    historical_data[plant+'2'] = historical_data[plant].shift(1)
    historical_data[plant+'3'] = historical_data[plant].shift(2)

    historical_data = historical_data.replace(0,historical_data.mean())
    historical_data = historical_data.fillna(historical_data.mean())

    data = historical_data.filter(['Period',plant+'1',plant+'2',plant+'3','Dubai TH1','Dubai TH2','Dubai TH3'], axis=1)
    data = data.loc[data['Period']==date]
    data = data.reset_index()
    data = data.drop(columns = ['index','Period'])
    return data

def eda_quantity(input_model,date):
    next_date = date + relativedelta(months=1)
    delta_day = (next_date - date).days

    x_input = input_model.copy()
    x_input['Dubai TH'] = x_input['Dubai ($/bbl)'] * x_input['Exchange Rate (TH/USD)']
    x_input['Sales target'] = x_input['Sell Target (kbd)'] * 1000 * delta_day
    x_input = x_input.replace(0,x_input.mean())
    x_input = x_input.fillna(x_input.mean())

    data = x_input.filter(['Period','Dubai TH','Sales target'], axis=1)
    data = data.loc[data['Period']==date]
    data = data.reset_index()
    data = data.drop(columns = ['index','Period'])
    return data


st.markdown(
    """
<style>
.streamlit-expanderHeader {
    font-size: x-large;
}
</style>
""",
    unsafe_allow_html=True,
)



logocol , headercol = st.columns([1,2.5])
with logocol:
    st.image(image)
with headercol:
    st.title('📈 Estimated Stock Gain/(Loss) and LCM calculation')

with st.expander("Input information",True):

    left_column, right_column = st.columns([1,2.5])
#example of input table
    with left_column:
        st.markdown('<font color="skyblue"> 🟢 Download the input variables template </font>',True)
        st.caption('The number of period can be any number from 1.')
        with open("Input.xlsx",'rb') as my_file:
            with st.spinner("Template file is downloading."):
                st.download_button(label = 'Download Template', data = my_file, file_name = 'example template.xlsx', 
                                    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    #import input table all
    with right_column:
        with st.spinner("Input file is uploading."):
            st.markdown('<font color="skyblue"> 🟢 Upload the input variables </font>',True)
            st.caption('Latest actual period is '+historical_inv_quan.iloc[-1]['Period'].strftime("%b-%y")+'.'+' Please do not state starting period after '+ (historical_inv_quan.iloc[-1]['Period']+relativedelta(months=1)).strftime("%b-%y")+'.')
            uploaded_file = st.file_uploader("Choose a file")
            if uploaded_file is not None:
                input_model = pd.read_excel(uploaded_file)
                st.markdown('<font color="skyblue"> 🟢 Input Preview</font>',True)
                st.dataframe(input_model)
            
                #convert input all into desired unit
                converted_input_all = pd.DataFrame()
            
                converted_input_all["Period"] = input_model["Period"]
                converted_input_all["Crude Purchase (bbl)"] = input_model["Crude Purchase (Mbbl)"] * 1000000
                converted_input_all["Crude Purchase (Baht)"] = input_model["Crude Purchase ($/bbl)"] * converted_input_all["Crude Purchase (bbl)"] * input_model["Exchange Rate (TH/USD)"]
                converted_input_all["Crude Run (bbl)"] = input_model["Crude Run (Mbbl)"] * 1000000
                converted_input_all["Dubai ($/bbl)"] = input_model["Dubai ($/bbl)"]
                converted_input_all["Premium ($/bbl)"] = input_model["Premium ($/bbl)"]
                converted_input_all["Exchange Rate (TH/USD)"] = input_model["Exchange Rate (TH/USD)"]
                converted_input_all["Sell Target (kbd)"] = input_model["Sell Target (kbd)"]
                converted_input_all["Market GIM ($/bbl)"] = input_model["Market GIM ($/bbl)"]
                    

#import info table
sell_percent = pd.read_excel("Info.xlsx", sheet_name = "Sell Percent")
yield_percent = pd.read_excel("Info.xlsx", sheet_name = "Yield Percent")
historical_inv_quan = pd.read_excel("Info.xlsx", sheet_name = "Inventory Quantity")
historical_inv_amount = pd.read_excel("Info.xlsx", sheet_name = "Inventory Amount")
transfer_ratio_amount = pd.read_excel("Info.xlsx", sheet_name = "Transfer Amount")
transfer_ratio_quan = pd.read_excel("Info.xlsx", sheet_name = "Transfer Quantity")
historical_lcm = pd.read_excel("Info.xlsx", sheet_name = "LCM")

if uploaded_file is not None:
    with st.expander("Modeling",True):
        inputcol, buttoncol = st.columns([1,2.5])
        with inputcol:
            selected_period = st.number_input('How many periods do you want to calculate?',min_value=1, max_value=len(input_model['Period']),value=len(input_model['Period']), step=1)
            if selected_period <= 1:
                st.write('You have selected ',selected_period,'period.')
            else:
                st.write('You have selected ',selected_period,'periods.')
           
        with buttoncol :
            st.markdown('##')
            run_model = st.button('Run model')
        if run_model:
            with st.spinner("Model is running."):
                #transfer
                transfer_list = ['Period','Refinery -> Lube','Refinery -> Olefin','Refinery -> Polyolefin',
                 'Refinery -> BTX','Lube -> Polystyrenic','Olefin -> Polyolefin',
                 'Olefin -> BTX','Olefin -> Polystyrenic','BTX -> Polystyrenic',
                 'Polystyrenic -> Refinery']
                
                #transfer quantity
                predicted_transfer_inv_quan = pd.DataFrame(columns = transfer_list)
                predicted_transfer_inv_quan["Period"] = converted_input_all["Period"]

                for i in range(len(predicted_transfer_inv_quan['Period'])):
                    for j in range(len(transfer_list)):
                        if j != 0:
                            predicted_transfer_inv_quan.iloc[i,j] = transfer_ratio_quan.iloc[0,j-1]

                #transfer amount
                predicted_transfer_inv_amount = pd.DataFrame(columns = transfer_list)
                predicted_transfer_inv_amount["Period"] = converted_input_all["Period"]

                for i in range(len(predicted_transfer_inv_amount['Period'])):
                    for j in range(len(transfer_list)):
                        if j != 0:
                            predicted_transfer_inv_amount.iloc[i,j] = transfer_ratio_amount.iloc[0,j-1]

                if selected_period == 1:
                    selected_date = converted_input_all.iloc[0]["Period"]
                    date = selected_date
                    result_all,inv_all,lcm_all,previous_historical_quan,previous_historical_amount = first_calculation(date,converted_input_all,sell_percent,yield_percent,predicted_transfer_inv_quan,predicted_transfer_inv_amount,historical_inv_quan,historical_inv_amount)
                else:
                    for i in range(selected_period):
                        selected_date = converted_input_all.iloc[i]["Period"]
                        date = selected_date
    
                        if i == 0:
                            result_all,inv_all,lcm_all,previous_historical_quan,previous_historical_amount = first_calculation(date,converted_input_all,sell_percent,
                                                                                                            yield_percent,predicted_transfer_inv_quan,predicted_transfer_inv_amount,
                                                                                                            historical_inv_quan,historical_inv_amount)
                        else:
                            result_all,inv_all,lcm_all,previous_historical_quan,previous_historical_amount = loop_calculation(date,converted_input_all,sell_percent,
                                                                                                            yield_percent,predicted_transfer_inv_quan,predicted_transfer_inv_amount,
                                                                                                            previous_historical_quan,previous_historical_amount,result_all,inv_all,lcm_all)
    
                st.markdown('##')

                tab1, tab2, tab3 , tab4 = st.tabs(["Result", "Stock G/L", "Inventory","LCM"])

                with tab1:
                  #create pd to store selected date info
                  input_selected = input_model.copy()
                  if selected_period < len(input_selected):
                      input_selected = input_selected.drop(labels = range(selected_period,len(input_selected)))
                    
                  fig, ax = plt.subplots(figsize=(15, 5))
                  ax.axes.get_yaxis().set_visible(False)
                  ax1 = ax.twinx() 
                  
                  ax_1 = result_all['Crude COGS ($/bbl)'].plot(kind='line', marker='o', color = 'firebrick')
                  arr_crudecogs = result_all[['Crude COGS ($/bbl)']].to_numpy()

                  ax_2 = result_all['Market Price ($/bbl)'].plot(kind='line', marker='x', color = 'mediumblue')
                  arr_marketprice = result_all[['Market Price ($/bbl)']].to_numpy()
                     
                  ax_3 = input_selected['Dubai ($/bbl)'].plot(kind='line', marker='*', color = 'darkgrey')
                  arr_dubai = input_selected[['Dubai ($/bbl)']].to_numpy()
                  
                  ax_4 = result_all['Stock Gain/(Loss) (Market - COGS) ($/bbl)'].plot(kind='bar', color = 'gold',secondary_y=True,stacked = True)
                  arr_stockgain = result_all[['Stock Gain/(Loss) (Market - COGS) ($/bbl)']].to_numpy()

                  lcm_graph = pd.DataFrame()
                  lcm_graph['LCM Rev (MBaht)'] = lcm_all['LCM Rev (MBaht)']
                  lcm_graph['LCM Rev ($/bbl)'] = lcm_graph['LCM Rev (MBaht)'] / result_all['Crude Run ($/bbl)'] / result_all['Exchange Rate (TH/USD)']
                  ax_5 = lcm_graph['LCM Rev ($/bbl)'].plot(kind='bar', color = 'seagreen',secondary_y=True,stacked = True)
                  arr_lcm = lcm_graph['LCM Rev ($/bbl)'].to_numpy()

                  for i in range(arr_stockgain.shape[0]):
                      v_1 = arr_crudecogs[i]
                      v_2 = arr_marketprice[i]
                      v_3 = arr_dubai[i]
                      v_4 = arr_stockgain[i]
                      v_5 = arr_lcm[i]
                      style_1 = dict(size=8, color='firebrick')
                      style_2 = dict(size=8, color='mediumblue')
                      style_3 = dict(size=8, color='black')
                      style_4 = dict(size=8, color='brown')
                      style_5 = dict(size=8, color='green')
                      ax_1.text(i, v_1+1, "%.2f" %v_1, ha="center",**style_1)
                      ax_2.text(i, v_2+1, "%.2f" %v_2, ha="center",**style_2)
                      ax_3.text(i, v_3+1, "%.2f" %v_3, ha="center",**style_3)
                      ax_4.text(i, v_4, "%.2f" %v_4, ha="center",**style_4)
                      ax_5.text(i, v_5, "%.2f" %v_5, ha="center",**style_5)
      
                  
      
                  ax_3.set_ylim(bottom = 20)
                  ax_5.set_ylim(top = 30)

                  input_selected['Period'] = input_selected['Period'].dt.strftime('%b-%y')
                  ax_3.set_xticklabels(input_selected['Period'])
                  ax_3.legend(loc='center left', bbox_to_anchor=(1.04, 0.7),fancybox = True, shadow = True)
                  ax_5.legend(loc='center left', bbox_to_anchor=(1.04, 0.4),fancybox = True, shadow = True)
      
                  st.pyplot(fig)
      
                with tab2:
                  st.dataframe(result_all)

                with tab3:
                  st.dataframe(inv_all)

                with tab4:
                  st.dataframe(lcm_all)

                left_column1, right_column1 = st.columns([1.5,4])

                with left_column1:
                  st.caption('The result from Estimated model')
                  export_data = to_excel(result_all,inv_all,lcm_all)
                  st.download_button(label = ' Download result', data = export_data, file_name = 'Result.xlsx')
                  
                with right_column1:
                  st.caption('The result from machinery model')
                  output = BytesIO()
                  writer = pd.ExcelWriter(output)
                  predicted_transfer_inv_quan.to_excel(writer, index = True, sheet_name = 'quantity')
                  predicted_transfer_inv_amount.to_excel(writer, index = True, sheet_name = 'amount')
                  writer.save()
                  final_data = output.getvalue()
                  st.download_button(label = 'Download transfer', data = final_data, file_name = 'Result transfer from model.xlsx')

                st.balloons()
