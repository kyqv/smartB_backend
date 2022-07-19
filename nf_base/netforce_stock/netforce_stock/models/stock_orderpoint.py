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
from datetime import *
import time


class OrderPoint(Model):
    _name = "stock.orderpoint"
    _string = "Minimum Stock Rule"
    _fields = {
        "location_id": fields.Many2One("stock.location", "Warehouse", search=True, required=True),
        "product_id": fields.Many2One("product", "Product", search=True),
        "product_categ_id": fields.Many2One("product.categ", "Product Category", search=True),
        "min_qty": fields.Decimal("Min Qty"),
        "min_qty_months": fields.Decimal("Min Qty Months"),
        "max_qty": fields.Decimal("Max Qty"),
        "max_qty_months": fields.Decimal("Max Qty Months"),
        "uom_id": fields.Many2One("uom", "UoM"),
        "min_qty2": fields.Decimal("Min Qty2"),
        "max_qty2": fields.Decimal("Max Qty2"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }

    def create(self, vals, **kw):
        id = super().create(vals, **kw)
        prod_id = vals["product_id"]
        #get_model("product").write([prod_id], {"update_balance": True})
        return id

    def write(self, ids, vals, **kw):
        prod_ids = []
        for obj in self.browse(ids):
            prod_ids.append(obj.product_id.id)
        super().write(ids, vals, **kw)
        prod_id = vals.get("product_id")
        if prod_id:
            prod_ids.append(prod_id)
        #get_model("product").write(prod_ids, {"update_balance": True})

    def delete(self, ids, **kw):
        prod_ids = []
        for obj in self.browse(ids):
            prod_ids.append(obj.product_id.id)
        super().delete(ids, **kw)
        #get_model("product").write(prod_ids, {"update_balance": True})

    def onchange_min_qty_months(self,context={}):
        data=context["data"]
        min_qty_months=data.get("min_qty_months") or 0
        print("min_qty_months",min_qty_months)
        prod_id=data["product_id"]
        t=time.strftime("%Y-%m-%d")
        n=0
        qty=0
        last_plan_qty=0
        for line in get_model("sale.forecast.line").search_browse([["product_id","=",prod_id]],order="forecast_id.date_from"):
            print("line",line.id)
            if n>=min_qty_months:
                break
            last_plan_qty=line.plan_qty
            sf=line.forecast_id
            if sf.date_to<t:
                continue
            qty+=line.plan_qty
            n+=1
        if n<min_qty_months:
            qty+=last_plan_qty*(min_qty_months-n)
        print("qty",qty)
        data["min_qty"]=qty
        return data

    def get_min_qty(self,product_id,location=None,context={}):
        res=self.search([["product_id","=",product_id]])
        if not res:
            return {
                "min_qty": 0,
                "max_qty": 0,
            }
        obj_id=res[0]
        obj=self.browse(obj_id)
        return {
            "min_qty": obj.min_qty or 0,
            "max_qty": obj.max_qty or 0,
        }

OrderPoint.register()
