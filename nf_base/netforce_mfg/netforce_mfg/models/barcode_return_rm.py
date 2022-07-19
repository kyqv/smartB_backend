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


class BarcodeReturnRM(Model):
    _name = "barcode.return.rm"
    _transient = True
    _fields = {
        "location_to_id": fields.Many2One("stock.location", "To Location", condition=[["type", "=", "internal"]]),
        "production_id": fields.Many2One("production.order", "Production Order", condition=[["state", "=", "in_progress"]]),
        "location_from_id": fields.Many2One("stock.location", "From Location"),
        "journal_id": fields.Many2One("stock.journal", "Stock Journal"),
        "lines": fields.One2Many("barcode.return.rm.line", "wizard_id", "Lines"),
        "state": fields.Selection([["pending", "Pending"], ["done", "Completed"]], "Status", required=True),
    }

    _defaults = {
        "state": "done",
    }

    def onchange_production(self, context={}):
        data = context["data"]
        order_id = data["production_id"]
        order = get_model("production.order").browse(order_id)
        data["location_from_id"] = order.production_location_id.id
        return data

    def fill_products(self, ids, context={}):
        obj = self.browse(ids)[0]
        order = obj.production_id
        found = False
        for comp in order.components:
            if comp.qty_issued <= 0.01:
                continue
            vals = {
                "wizard_id": obj.id,
                "product_id": comp.product_id.id,
                "lot_id": comp.lot_id.id,
                "qty": comp.qty_issued,
                "uom_id": comp.uom_id.id,
            }
            get_model("barcode.return.rm.line").create(vals)
            found = True
        if not found:
            raise Exception("No products to return")

    def clear(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "production_id": None,
            "location_from_id": None,
            "lines": [("delete_all",)],
        }
        obj.write(vals)

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.lines:
            raise Exception("Product list is empty")
        pick_vals = {
            "type": "in",
            "related_id": "production.order,%d" % obj.production_id.id,
            "journal_id": obj.journal_id.id,
            "lines": [],
        }
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "lot_id": line.lot_id.id,
                "location_from_id": obj.location_from_id.id,
                "location_to_id": obj.location_to_id.id,
            }
            pick_vals["lines"].append(("create", line_vals))
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "in"})
        if obj.state == "done":
            get_model("stock.picking").set_done([pick_id])
        elif obj.state == "pending":
            get_model("stock.picking").pending([pick_id])
        pick = get_model("stock.picking").browse(pick_id)
        obj.clear()
        return {
            "flash": "Goods receipt %s created successfully" % pick.number,
            "focus_field": "production_id",
        }

BarcodeReturnRM.register()
