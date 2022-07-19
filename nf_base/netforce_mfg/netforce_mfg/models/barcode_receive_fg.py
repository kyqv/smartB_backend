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
from netforce.access import get_active_company, get_active_user, check_permission_other


class BarcodeReceiveFG(Model):
    _name = "barcode.receive.fg"
    _transient = True
    _fields = {
        "location_to_id": fields.Many2One("stock.location", "To Location", condition=[["type", "=", "internal"]]),
        "journal_id": fields.Many2One("stock.journal", "Stock Journal"),
        "production_id": fields.Many2One("production.order", "Production Order", condition=[["state", "=", "in_progress"]]),
        "location_from_id": fields.Many2One("stock.location", "From Location"),
        "lines": fields.One2Many("barcode.receive.fg.line", "wizard_id", "Lines"),
        "state": fields.Selection([["pending", "Pending"], ["done", "Completed"]], "Status", required=True),
        "issued_lines": fields.One2Many("barcode.receive.fg.line.issue", "wizard_id", "Issued Lines"),
        "total_qty_received": fields.Decimal("Total Received Qty", function="get_total_qty", function_multi=True, scale=6),
        "total_qty_issued": fields.Decimal("Total Issued Qty", function="get_total_qty", function_multi=True, scale=6),
        "total_qty_diff": fields.Decimal("Qty Loss", function="get_total_qty", function_multi=True, scale=6),
        "max_qty_loss": fields.Decimal("Max Qty Loss", function="get_total_qty", function_multi=True, scale=6),
        "approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
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
        qty_remain = order.qty_planned - order.qty_received
        if qty_remain > 0.01:
            line_vals = {
                "wizard_id": obj.id,
                "product_id": order.product_id.id,
                "qty": qty_remain,
                "uom_id": order.uom_id.id,
            }
            get_model("barcode.receive.fg.line").create(line_vals)
            found = True
        for comp in order.components:
            qty_remain = comp.qty_planned - comp.qty_issued
            if qty_remain >= -0.01:
                continue
            line_vals = {
                "wizard_id": obj.id,
                "product_id": comp.product_id.id,
                "qty": -qty_remain,
                "uom_id": comp.uom_id.id,
            }
            get_model("barcode.receive.fg.line").create(line_vals)
            found = True
        if not found:
            raise Exception("Nothing remaining to receive")
        for comp in order.components:
            if comp.qty_issued < 0.01:
                continue
            line_vals = {
                "wizard_id": obj.id,
                "product_id": comp.product_id.id,
                "qty": comp.qty_issued,
                "uom_id": comp.uom_id.id,
            }
            get_model("barcode.receive.fg.line.issue").create(line_vals)

    def clear(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "production_id": None,
            "location_from_id": None,
            "employee_id": None,
            "lines": [("delete_all",)],
            "issued_lines": [("delete_all",)],
        }
        obj.write(vals)

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.lines:
            raise Exception("Product list is empty")
        if obj.max_qty_loss != None and obj.total_qty_diff > obj.max_qty_loss and not obj.approved_by_id:
            raise Exception("Qty loss is too high, need approval")
        if not obj.issued_lines:
            raise Exception("Raw materials not yet issued, can not receive finished goods yet")
        pick_vals = {
            "type": "in",
            "related_id": "production.order,%d" % obj.production_id.id,
            "journal_id": obj.journal_id.id,
            "done_approved_by_id": obj.approved_by_id.id,
            "employee_id": obj.employee_id.id,
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

    def get_total_qty(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_in = 0
            total_out = 0
            for line in obj.lines:
                total_in += line.qty
            for line in obj.issued_lines:
                total_out += line.qty
            if obj.production_id:
                max_qty_loss = obj.production_id.max_qty_loss
            else:
                max_qty_loss = 0
            vals[obj.id] = {
                "total_qty_received": total_in,
                "total_qty_issued": total_out,
                "total_qty_diff": total_out - total_in,
                "max_qty_loss": max_qty_loss,
            }
        return vals

    def approve(self, ids, context={}):
        if not check_permission_other("production_receive_fg"):
            raise Exception("Permission denied")
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"approved_by_id": user_id})
        return {
            "next": {
                "name": "barcode_receive_fg",
                "active_id": obj.id,
            },
            "flash": "Goods receipt approved successfully",
        }

BarcodeReceiveFG.register()
