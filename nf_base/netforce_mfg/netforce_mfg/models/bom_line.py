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

from netforce.model import Model, fields
from decimal import *


class BomLine(Model):
    _name = "bom.line"
    _fields = {
        "bom_id": fields.Many2One("bom", "BoM", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "RM Product", required=True),
        "qty": fields.Decimal("Qty", required=True, scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "RM Warehouse"),
        "container": fields.Selection([["sale", "From Sales Order"]], "RM Container"),
        "lot": fields.Selection([["production", "From Production Order"]], "RM Lot"),
        "issue_method": fields.Selection([["manual", "Manual"], ["backflush", "Backflush"], ["purchase","Purchase"]], "Issue Method"),
        "qty2": fields.Decimal("Qty2", scale=6),
        "notes": fields.Text("Notes"),
        "weight": fields.Decimal("Unit Weight",function="_get_related",function_context={"path":"product_id.weight"}),
        "cost_amount": fields.Decimal("RM Cost Amount",function="get_cost"),
        "forecast_cost_amount": fields.Decimal("RM Cost Forecast",function="get_cost_forecast"),
        "labor_amount": fields.Decimal("Labor Amount"),
        "sequence": fields.Integer("Sequence"),
    }

    def get_cost(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod=obj.product_id
            purch_qty=Decimal(obj.qty)/(prod.purchase_to_stock_uom_factor or 1)*(prod.purchase_to_invoice_uom_factor or 1)
            vals[obj.id]=(prod.cost_price or prod.purchase_price or 0)*purch_qty # XXX: use only cost price
        return vals

    def get_cost_forecast(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=None
        return vals

BomLine.register()
