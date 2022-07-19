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


class StockCountLine(Model):
    _name = "stock.count.line"
    _fields = {
        "count_id": fields.Many2One("stock.count", "Stock Count", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", condition=[["type", "=", "stock"]], required=True),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "bin_location": fields.Char("Bin Location", readonly=True),
        "prev_qty": fields.Decimal("Previous Qty", required=True, readonly=True),
        "new_qty": fields.Decimal("New Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True, readonly=True),
        "prev_cost_price": fields.Decimal("Previous Cost Price", scale=6, readonly=True),
        "prev_cost_amount": fields.Decimal("Previous Cost Amount"),
        "unit_price": fields.Decimal("New Cost Price", scale=6), # TODO: rename to new_cost_price
        "new_cost_amount": fields.Decimal("New Cost Amount",function="get_new_cost_amount"),
    }
    _order="product_id.code"

    def get_prev_cost_price(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.prev_cost_amount or 0)/obj.prev_qty if obj.prev_qty else 0
        return vals

    def get_new_cost_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.new_qty or 0)*(obj.unit_price or 0)
        return vals

StockCountLine.register()
