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


class BarcodeIssueRMLine(Model):
    _name = "barcode.issue.rm.line"
    _transient = True
    _fields = {
        "wizard_id": fields.Many2One("barcode.issue.rm", "Wizard", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", required=True),
        "qty": fields.Decimal("Qty Issued", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "qty_stock": fields.Decimal("Qty In Stock", function="get_qty_stock"),
    }

    def get_qty_stock(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            wiz = obj.wizard_id
            loc_id = wiz.location_from_id.id
            if loc_id:
                res = get_model("stock.location").compute_balance(
                    [loc_id], obj.product_id.id, lot_id=obj.lot_id.id)  # XXX: speed
                qty = res["bal_qty"]
            else:
                qty = None
            vals[obj.id] = qty
        return vals

BarcodeIssueRMLine.register()
