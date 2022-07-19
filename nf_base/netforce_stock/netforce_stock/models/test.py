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

from netforce.model import Model, fields, get_model
import datetime

class CycleStockCount(Model):
    _name = "cycle.stock.count"
    _string = "Cycle Stock Count"
    _fields = {
        "date": fields.Date("Date",search=True),
        "product_id": fields.Many2One("product","Product",condition=[["type","=","stock"],search=True),
        "abc_categ": fields.Selection([["a_","A"],["b_","B"],["c_","C"],"ABC Category",search=True),
        "xyz_categ": fields.Selection([["x_","X"],["y_","Y"],["z_","Z"],"XYZ Category",search=True),
        #"turnover_rate": fields.Decimal("Inventory Turnover"),
        "location_id": fields.Many2One("stock.location", "Stock Location", required=True, search=True),
        "record_id": fields.One2Many("stock.count.record","cycle_count_id","Stock Count Records") 
    }
    _order = "date,id"

    def get_stock_move(self,exclude_zeros=True):
        sm = get_model("stock.move").browse()
        settings = get_model("settings").browse(1)
        segmentation_strategy = settings.segmentation_strategy
        cond = [["state","=","done"].["picking_type","=","out"]]

        def _get_categ_ratio(categ_type):
            high = None # most active productse
            medium = None  # moderately active products
            low = None # least active products
            if categ_type == "abc":
                high = res.field1
                moderate = res.field2
                low = res.field3 
            if categ_type == "xyz":
                high = res.field4
                moderate = res.field5  
                low = res.field6 
            return (high,medium,low)

        if segmentation_strategy == "abc":
           (A,B,C) = _get_categ_ratio(segmentation_strategy)
            if exclude_zeros:
                cond.append(["cost_amount",">",0])
            ## to be developed
            data = get_model("stock.move").search_browse(cond)
            summary =  get_aggregate(data,"cost_amount")
            sort_by_revenue = sort(summary,reverse=True,key=lambda x : x['total'])
            A_ = sort_by_revenue[:A] 
            B_ = sort_by_qty[A:B]
            C_ = sort_by_qty[B:]
            return (A_,B_,C_)
        if segmentation_strategy == "xyz":
            (X, Y, Z) = _get_categ_ratio(segmentation_strategy)
            if exclude_zeros:
                cond.append(["qty",">",0])
            data = get_model("stock.move").search_browse(cond)
            summary = get_aggregate(data,"qty")
            sort_by_qty = sort(summary,reverse=True,key=lambda x : x['total'])
            X_ = sort_by_qty[:X] 
            Y_ = sort_by_qty[X:Y]
            Z_ = sort_by_qty[Y:]
            return (X_,Y_,Z_)



    def get_summary(self,field=None):
        if not field:
            raise Exception("No quantity of interest")
        return

    def get_summary_by_qty(self):
        return self.get_summary("qty")

    def get_summary_by_cost(self):
        return self.get_summary("cost_amount")

    def func(self):
        return

    
CycleStockCount.register()
