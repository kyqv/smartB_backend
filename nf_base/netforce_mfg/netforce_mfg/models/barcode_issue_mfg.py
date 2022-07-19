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
import time
from pprint import pprint


class BarcodeIssueMFG(Model):
    _name = "barcode.issue.mfg"
    _transient = True
    _fields = {
        "location_from_id": fields.Many2One("stock.location", "From Location", condition=[["type", "=", "internal"]]),
        "production_id": fields.Many2One("production.order", "Production Order", condition=[["state", "=", "in_progress"]]),
        "location_to_id": fields.Many2One("stock.location", "To Location", condition=[["type", "=", "internal"]]),
        "journal_id": fields.Many2One("stock.journal", "Stock Journal"),
        "lines": fields.One2Many("barcode.issue.mfg.line", "wizard_id", "Lines"),
        "state": fields.Selection([["pending", "Pending"], ["done", "Completed"]], "Status", required=True),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "container_from_id": fields.Many2One("stock.container", "From Container"),
    }

    _defaults = {
        "state": "done",
    }

    def onchange_production(self, context={}):
        data = context["data"]
        order_id = data["production_id"]
        order = get_model("production.order").browse(order_id)
        data["location_to_id"] = order.production_location_id.id
        return data

    def fill_products(self, ids, context={}):
        obj = self.browse(ids)[0]
        contents = obj.location_from_id.get_contents()
        order = obj.production_id
        for comp in order.components:
            qty_remain = comp.qty_planned - comp.qty_issued
            if qty_remain < 0.001:
                continue
            for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
                if prod_id != comp.product_id.id:
                    continue
                if comp.container_id and cont_id != comp.container_id.id:
                    continue
                if comp.lot_id and lot_id != comp.lot_id.id:
                    continue
                used_qty = min(qty, qty_remain)
                qty_remain -= used_qty
                vals = {
                    "wizard_id": obj.id,
                    "product_id": comp.product_id.id,
                    "lot_id": lot_id,
                    #"qty": used_qty,
                    "qty": 0,
                    "uom_id": comp.uom_id.id,  # TODO: convert UoM
                    "qty2": qty2,
                    "container_from_id": comp.container_id.id,
                    "container_loss_id": comp.container_id.id,
                }
                get_model("barcode.issue.mfg.line").create(vals)
                if qty_remain < 0.001:
                    break

    def clear(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "container_from_id": None,
            "production_id": None,
            "location_to_id": None,
            "lines": [("delete_all",)],
        }
        obj.write(vals)

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.lines:
            raise Exception("Product list is empty")
        pick_vals = {
            "type": "internal",
            "related_id": "production.order,%d" % obj.production_id.id,
            "ref": "Transfer to %s" % obj.production_id.number,
            "journal_id": obj.journal_id.id,
            "lines": [],
        }
        for line in obj.lines:
            if line.mode == "loss" and not line.location_loss_id.id:
                raise Exception("Invalid Loss Location")
            if abs(line.qty - line.qty_stock) > 0.001 and line.mode == "loss" and line.location_loss_id.id:
                loss_vals = {
                    "qty": abs(line.qty - line.qty_stock),
                    "product_id": line.product_id.id,
                    "uom_id": line.uom_id.id,
                    "lot_id": line.lot_id.id,
                }
                if line.qty > line.qty_stock:
                    loss_vals["container_from_id"] = line.container_loss_id.id
                    loss_vals["container_to_id"] = line.container_from_id.id
                    loss_vals["location_from_id"] = line.location_loss_id.id
                    loss_vals["location_to_id"] = obj.location_from_id.id
                elif line.qty < line.qty_stock:
                    loss_vals["location_from_id"] = obj.location_from_id.id
                    loss_vals["location_to_id"] = line.location_loss_id.id
                    loss_vals["container_from_id"] = line.container_from_id.id
                    loss_vals["container_to_id"] = line.container_loss_id.id
                pick_vals["lines"].append(("create", loss_vals))
            line_vals = {
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "qty2": line.qty2,
                "lot_id": line.lot_id.id,
                "location_from_id": obj.location_from_id.id,
                "location_to_id": obj.location_to_id.id,
                "container_from_id": line.container_from_id.id,
                "container_to_id": line.container_to_id.id,
            }
            pick_vals["lines"].append(("create", line_vals))
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "internal"})
        if obj.state == "done":
            get_model("stock.picking").set_done([pick_id])
        elif obj.state == "pending":
            get_model("stock.picking").pending([pick_id])
        pick = get_model("stock.picking").browse(pick_id)
        obj.clear()
        return {
            "flash": "Goods transfer %s created successfully" % pick.number,
            "focus_field": "production_id",
        }

BarcodeIssueMFG.register()
