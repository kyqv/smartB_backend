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
from netforce.utils import get_data_path
from netforce.database import get_connection
from netforce import access
from datetime import *
import time


class SaleForecastLine(Model):
    _name = "sale.forecast.line"
    _string = "Sales Forecast Line"
    _name_field = "number"
    _fields = {
        "forecast_id": fields.Many2One("sale.forecast", "Sales Forecast", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", required=True, search=True),
        "plan_qty": fields.Decimal("Planned Sale Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM"), # XXX: deprecated
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "actual_qty": fields.Decimal("Actual Sale Qty", function="get_actual_qty"),
        "plan_out_qty": fields.Decimal("Planned Issue Qty", function="get_plan_out_qty"),
        "plan_remain_qty": fields.Decimal("Planned Remain Qty", function="get_plan_remain_qty"),
        "sequence": fields.Integer("Sequence"),
        "customer_id": fields.Many2One("contact","Customer",search=True),
        "location_id": fields.Many2One("stock.location", "Warehouse"),
        "min_shelf_life": fields.Selection([["50","50%"],["75","75%"]],"Min Shelf Life"),
        "prev_line_id": fields.Many2One("sale.forecast.line","Previous Forecast",function="get_prev_line"),
        "prev_plan_qty": fields.Decimal("Previous Planned Qty",function="get_prev",function_multi=True),
        "prev_diff_percent": fields.Decimal("Previous Diff (%)",function="get_prev",function_multi=True),
    }
    _order = "sequence,id"

    def onchange_product(self,context={}):
        data=context.get("data")
        prod_id=data["product_id"]
        prod=get_model("product").browse(prod_id)
        data["uom_id"]=prod.uom_id.id
        return data

    def get_actual_qty(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            cond = [["order_id.state", "in", ["confirmed", "done"]], ["order_id.due_date", ">=", obj.forecast_id.date_from],
                   ["order_id.due_date", "<=", obj.forecast_id.date_to], ["product_id", "=", obj.product_id.id]]
            if obj.customer_id:
                cond.append(["order_id.contact_id", "=", obj.customer_id.id])
            total = 0
            for line in get_model("sale.order.line").search_browse(cond):
                total += get_model("uom").convert(line.qty, line.uom_id.id, obj.product_id.uom_id.id)
            vals[obj.id] = total
        return vals

    def get_plan_out_qty(self, ids, context={}):
        settings = get_model("settings").browse(1)
        vals = {}
        for obj in self.browse(ids):
            cond = [["state", "in", ["pending", "approved", "done"]], ["date", ">=", obj.date_from + " 00:00:00"], ["date", "<=",
                                                                                                                   obj.date_to + " 23:59:59"], ["product_id", "=", obj.product_id.id], ["location_from_id", "=", obj.location_id.id]]
            if obj.customer_id:
                cond.append(["contact_id", "=", obj.customer_id.id])
            total = 0
            for move in get_model("stock.move").search_browse(cond):
                total += get_model("uom").convert(move.qty, move.uom_id.id, obj.uom_id.id)
            vals[obj.id] = total
        return vals

    def get_plan_remain_qty(self, ids, context={}):
        db = get_connection()
        vals = {}
        for obj in self.browse(ids):
            bal_qty = 0
            res = db.query("SELECT SUM(qty) AS qty,uom_id FROM stock_move WHERE product_id=%s AND location_to_id=%s AND date<=%s AND state IN ('pending','approved','done') GROUP BY uom_id",
                           obj.product_id.id, obj.location_id.id, obj.date_to + " 23:59:59")
            for r in res:
                bal_qty += get_model("uom").convert(r.qty, r.uom_id, obj.uom_id.id)
            res = db.query("SELECT SUM(qty) AS qty,uom_id FROM stock_move WHERE product_id=%s AND location_from_id=%s AND date<=%s AND state IN ('pending','approved','done') GROUP BY uom_id",
                           obj.product_id.id, obj.location_id.id, obj.date_to + " 23:59:59")
            for r in res:
                bal_qty -= get_model("uom").convert(r.qty, r.uom_id, obj.uom_id.id)
            vals[obj.id] = bal_qty
        return vals

    def onchange_customer(self, context={}):
        data=context["data"]
        cust_id=data["customer_id"]
        if not cust_id:
            return
        cust=get_model("contact").browse(cust_id)
        data["min_shelf_life"]=cust.min_shelf_life
        return data

    def get_prev_line(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            res=get_model("sale.forecast.line").search([["product_id","=",obj.product_id.id],["min_shelf_life","=",obj.min_shelf_life],["forecast_id.date_to","<",obj.forecast_id.date_to]],order="forecast_id.date_to desc",limit=1)
            vals[obj.id]=res[0] if res else None
        return vals

    def get_prev(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prev=obj.prev_line_id
            if prev and prev.plan_qty:
                vals[obj.id]={
                    "prev_plan_qty": prev.plan_qty,
                    "prev_diff_percent": (obj.plan_qty-prev.plan_qty)*100/prev.plan_qty,
                }
            else:
                vals[obj.id]={
                    "prev_plan_qty": None,
                    "prev_diff_percent": None,
                }
        return vals

SaleForecastLine.register()
