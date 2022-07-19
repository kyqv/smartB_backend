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
from netforce.access import get_active_company, get_active_user
import time


class BorrowLine(Model):
    _name = "product.borrow.line"
    _name_field = "number"
    _fields = {
        "request_id": fields.Many2One("product.borrow", "Borrow Request", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", required=True),
        "qty": fields.Decimal("Requested Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "issued_qty": fields.Decimal("Issued Qty", function="get_qty_issued"),
        "returned_qty": fields.Decimal("Returned Qty", function="get_qty_returned"),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
    }

    def get_qty_issued(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.request_id
            qty = 0
            for move in order.stock_moves:
                if move.product_id.id != obj.product_id.id or move.state != "done":
                    continue
                if move.picking_id.type == "out":
                    qty += move.qty  # XXX: uom
            vals[obj.id] = qty
        return vals

    def get_qty_returned(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.request_id
            qty = 0
            for move in order.stock_moves:
                if move.product_id.id != obj.product_id.id or move.state != "done":
                    continue
                if move.picking_id.type == "in":
                    qty += move.qty  # XXX: uom
            vals[obj.id] = qty
        return vals

BorrowLine.register()
