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
import time
from netforce.access import get_active_company, get_active_user, check_permission_other


class BarcodeTransfer(Model):
    _name = "barcode.transfer"
    _transient = True
    _fields = {
        "location_from_id": fields.Many2One("stock.location", "From Location", condition=[["type", "=", "internal"]]),
        "container_from_id": fields.Many2One("stock.container", "From Container"),
        "location_to_id": fields.Many2One("stock.location", "To Location", condition=[["type", "=", "internal"]]),
        "journal_id": fields.Many2One("stock.journal", "Stock Journal"),
        "lines": fields.One2Many("barcode.transfer.line", "wizard_id", "Lines"),
        "state": fields.Selection([["pending", "Pending"], ["done", "Completed"]], "Status", required=True),
        "approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"]], "Related To"),
    }

    _defaults = {
        "state": "done",
    }

    def onchange_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return {}
        prod = get_model("product").browse(prod_id)
        line["uom_id"] = prod.uom_id.id
        return data

    def onchange_lot(self, context):
        data = context["data"]
        loc_id = data["location_from_id"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line["product_id"]
        lot_id = line["lot_id"]
        res = get_model("stock.location").compute_balance([loc_id], prod_id, lot_id=lot_id)
        line["qty"] = res["bal_qty"]
        return data

    def fill_products(self, ids, context={}):
        obj = self.browse(ids)[0]
        order = obj.production_id
        if not obj.container_from_id:
            contents = obj.location_from_id.get_contents()
            for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
                prod = get_model("product").browse(prod_id)
                vals = {
                    "wizard_id": obj.id,
                    "product_id": prod_id,
                    "lot_id": lot_id,
                    "qty": qty,
                    "uom_id": prod.uom_id.id,
                    "qty2": qty2,
                    "location_from_id": obj.location_from_id.id,
                    "location_to_id": obj.location_to_id.id,
                }
                get_model("barcode.transfer.line").create(vals)
            return
            #raise Exception("No container selected")
        contents = obj.container_from_id.get_contents()
        for (prod_id, lot_id, loc_id), (qty, amt, qty2) in contents.items():
            if loc_id != obj.location_from_id.id:
                continue
            prod = get_model("product").browse(prod_id)
            vals = {
                "wizard_id": obj.id,
                "product_id": prod_id,
                "lot_id": lot_id,
                "qty": qty,
                "uom_id": prod.uom_id.id,
                "qty2": qty2,
                "location_from_id": obj.location_from_id.id,
                "location_to_id": obj.location_to_id.id,
                "container_from_id": obj.container_from_id.id,
                "container_to_id": obj.container_from_id.id,
            }
            get_model("barcode.transfer.line").create(vals)
        obj.write({"container_from_id": None})

    def clear(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "location_to_id": None,
            "related_id": None,
            "lines": [("delete_all",)],
        }
        obj.write(vals)

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.lines:
            raise Exception("Product list is empty")
        pick_vals = {
            "type": "internal",
            "journal_id": obj.journal_id.id,
            "lines": [],
            "done_approved_by_id": obj.approved_by_id.id,
        }
        rel = obj.related_id
        if rel:
            pick_vals["related_id"] = "%s,%d" % (rel._model, rel.id)
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "lot_id": line.lot_id.id,
                "location_from_id": obj.location_from_id.id,
                "location_to_id": obj.location_to_id.id,
                "container_from_id": line.container_from_id.id,
                "container_to_id": line.container_to_id.id,
            }
            if line.related_id:
                line_vals["related_id"] = "%s,%d" % (line.related_id._model, line.related_id.id)
            pick_vals["lines"].append(("create", line_vals))
        pick_id = get_model("stock.picking").create(pick_vals, context=pick_vals)
        if obj.state == "done":
            get_model("stock.picking").set_done([pick_id])
        elif obj.state == "pending":
            get_model("stock.picking").pending([pick_id])
        pick = get_model("stock.picking").browse(pick_id)
        obj.clear()
        return {
            "next": {
                "name": "pick_internal",
                "mode": "page",
                "active_id": pick.id
            },
            "flash": "Goods transfer %s created successfully" % pick.number,
            "focus_field": "related_id",
        }

    def approve(self, ids, context={}):
        if not check_permission_other("stock_transfer"):
            raise Exception("Permission denied")
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"approved_by_id": user_id})
        return {
            "next": {
                "name": "barcode_transfer",
                "active_id": obj.id,
            },
            "flash": "Stock transfer approved successfully",
        }

BarcodeTransfer.register()
