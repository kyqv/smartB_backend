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


class BarcodeReceiveMFGLine(Model):
    _name = "barcode.receive.mfg.line"
    _transient = True
    _fields = {
        "wizard_id": fields.Many2One("barcode.receive.mfg", "Wizard", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", required=True),
        "qty": fields.Decimal("Actual Receive Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "qty2": fields.Decimal("Actual Receive Secondary Qty"),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number"),
        "qty_planned": fields.Decimal("Planned Receive Qty", function="get_qty_planned"),
        "container_from_id": fields.Many2One("stock.container", "From Container"),
        "container_to_id": fields.Many2One("stock.container", "To Container"),
        "qty_issued": fields.Decimal("Issued Qty", function="get_qty_issued"),
    }

    def get_qty_planned(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.wizard_id.production_id
            qty = 0
            if obj.product_id.id == order.product_id.id:
                qty = max(0, order.qty_planned - order.qty_received)
            else:
                for comp in order.components:
                    if comp.product_id.id == obj.product_id.id:
                        qty = max(0, comp.qty_issued - comp.qty_planned)
                        break
            vals[obj.id] = qty
        return vals

    def get_qty_issued(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.wizard_id.production_id
            qty = 0
            if obj.product_id.id == order.product_id.id:
                qty = max(0, -order.qty_received)
            else:
                for comp in order.components:
                    if comp.product_id.id == obj.product_id.id:
                        qty = max(0, comp.qty_issued)
                        break
            vals[obj.id] = qty
        return vals

BarcodeReceiveMFGLine.register()
