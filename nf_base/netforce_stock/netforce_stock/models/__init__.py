# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from . import stock_picking
from . import stock_move
from . import stock_location
from . import stock_count
from . import stock_count_line
from . import stock_count_add
from . import report_stock
from . import stock_orderpoint
from . import stock_balance
from . import stock_barcode
from . import pick_validate
from . import pick_validate_line
from . import report_stock_card
from . import report_stock_summary
from . import stock_journal
from . import ship_method
from . import ship_rate
from . import ship_term
from . import store_type
from . import report_stock_aging
from . import report_stock_forecast
from . import product_claim
from . import product_borrow
from . import product_borrow_line
from . import stock_container
from . import stock_packaging
from . import stock_lot
from . import barcode_station
from . import barcode_transfer
from . import barcode_transfer_line
from . import barcode_validate
from . import barcode_validate_line
from . import barcode_receive
from . import barcode_receive_line
from . import barcode_issue
from . import barcode_issue_line
from . import report_ship_cost
from . import report_stock_move
from . import stock_transform
from . import stock_transform_line
from . import stock_consign
from . import stock_consign_period
from . import landed_cost
from . import landed_cost_alloc
from . import report_stock_plan
from . import stock_order
from . import stock_order_line
from . import delivery_slot
from . import delivery_slot_capacity
from . import messenger # XXX: deprecated
from . import qc_result
from . import product_waste
from . import stock_forecast
from . import stock_pallet
from . import stock_container_type
from . import stock_grade
from . import stock_grade_line
from . import report_forecast_details
from . import report_forecast_summary
from . import stock_lot_item
from . import ship_port
from . import stock_transfer
from . import gen_lots
from . import report_stock_invoice
from . import stock_balance_update
from . import report_stock_expire
from . import stock_cut 
from . import stock_cut_order
from . import stock_cut_stock
from . import stock_cut_pattern
from . import port_loading #Chin
from . import port_destination #Chin
from . import cycle_stock_count #Max
from . import select_location #Max
