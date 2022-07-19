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
from netforce.access import get_active_company, get_active_user, check_permission_other


class BarcodeSafeIn(Model):
    _name = "barcode.safe.in"
    _transient = True
    _fields = {
        "location_from_id": fields.Many2One("stock.location", "From Location", condition=[["type", "=", "internal"]]),
        "location_to_id": fields.Many2One("stock.location", "To Location", condition=[["type", "=", "internal"]]),
        "product_categ_id": fields.Many2One("product.categ", "Product Category"),
        "container": fields.Many2One("stock.container", "Container"),
        "journal_id": fields.Many2One("stock.journal", "Stock Journal"),
        "lines": fields.One2Many("barcode.safe.in.line", "wizard_id", "Lines"),
        "state": fields.Selection([["pending", "Pending"], ["done", "Completed"]], "Status", required=True),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "ref": fields.Char("Pick Number"),
    }

    _defaults = {
        "state": "done",
    }

    def fill_products(self, ids, context={}):
        obj = self.browse(ids)[0]
        contents = obj.location_from_id.get_contents(context={"product_categ_id": obj.product_categ_id.id})
        for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
            prod = get_model("product").browse(prod_id)
            vals = {
                "wizard_id": obj.id,
                "product_id": prod_id,
                "lot_id": lot_id,
                "qty": qty,
                "qty2": qty2,
                "uom_id": prod.uom_id.id,
                "container_from_id": cont_id,
                "container_to_id": cont_id,
            }
            get_model("barcode.safe.in.line").create(vals)

    def clear(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "product_categ_id": None,
            "lines": [("delete_all",)],
        }
        obj.write(vals)

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.approved_by_id:
            raise Exception("Close Safe has to approved first")
        if not obj.lines:
            raise Exception("Product list is empty")
        pick_vals = {
            "type": "internal",
            "ref": "DC To Safe",
            "journal_id": obj.journal_id.id,
            "lines": [],
            "done_approved_by_id": obj.approved_by_id.id,
        }
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
            pick_vals["lines"].append(("create", line_vals))
        pick_id = get_model("stock.picking").create(
            pick_vals, context={"pick_type": "internal", "noupdate_production": True})
        if obj.state == "done":
            get_model("stock.picking").set_done([pick_id], context={"noupdate_production": True})
        elif obj.state == "pending":
            get_model("stock.picking").pending([pick_id])
        pick = get_model("stock.picking").browse(pick_id)
        move_ids = []
        for line in pick.lines:
            move_ids.append(line.id)
        production_ids = get_model("stock.move").get_production_orders(move_ids)
        get_model("production.order").update_status(list(set(production_ids)))
        vals = {
            "ref": pick.number,
        }
        obj.write(vals)
        obj.clear()
        return {
            "flash": "Goods transfer %s created successfully" % pick.number,
            "focus_field": "production_id",
        }

    def approve_popup(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "approve_barcode_safe_in",
                "refer_id": obj.id,
            }
        }

    def approve(self, ids, context={}):
        if not check_permission_other("production_safe_in"):
            raise Exception("Permission denied")
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"approved_by_id": user_id})
        return {
            "next": {
                "name": "barcode_safe_in",
                "active_id": obj.id,
            },
            "flash": "DC to safe approved successfully",
        }

    def disapprove(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"approved_by_id": None})
        return {
            "flash": "Disapprove successfully",
        }

    def run_report(self, ids, context={}):
        print("barcode.safe.in run_report")
        # obj.write({"is_printed":True})
        return {
            "next": {
                "name": "report_safe_in",
                "ids": ids,
            }
        }

    def get_report_data(self, ids, context={}):
        print("barcode.safe.in get_report_data", ids)
        obj = self.browse(ids)[0]
        data = {
            "location_from": obj.location_from_id.name,
            "location_to": obj.location_to_id.name,
            "lines": [],
        }
        contents = obj.location_from_id.get_contents(context={"product_categ_id": obj.product_categ_id.id})
        for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
            prod = get_model("product").browse(prod_id)
            production_location = ""
            state = ""
            container_number = ""
            if cont_id:
                cont = get_model("stock.container").browse(cont_id)
                container_number = cont.number
            if lot_id:
                lot = get_model("stock.lot").browse(lot_id)
                lot_number = lot.number
                production = get_model("production.order").search_browse([["number", "=", lot_number]])
                if production:
                    production_location = production[0].production_location_id.name
                    state = production[0].state
                else:
                    production = ""
                    state = ""
            vals = {
                "container_number": container_number,
                "prod_code": prod.code,
                "prod_description": prod.description,
                "qty": round(qty, 2),
                "uom": prod.uom_id.name,
                "qty2": qty2,
                "production_location": production_location,
                "state": state,
            }
            data["lines"].append(vals)
        data["lines"] = sorted(data["lines"], key=lambda line: line['container_number'])
        print(data)
        return data

    def container_fill(self, ids, context={}):
        obj = self.browse(ids)[0]
        contents = obj.location_from_id.get_contents(context={"product_categ_id": obj.product_categ_id.id})
        if not obj.container:
            raise Exception("No container selected")
        container = obj.container
        container_in_lines = []
        for line in obj.lines:
            container_in_lines.append(line.container_from_id.id)
        container_in_lines = list(set(container_in_lines))
        for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
            prod = get_model("product").browse(prod_id)
            if cont_id != container.id or container.id in container_in_lines:
                continue
            vals = {
                "wizard_id": obj.id,
                "product_id": prod_id,
                "lot_id": lot_id,
                "qty": qty,
                "uom_id": prod.uom_id.id,
                "qty2": qty2,
                "container_from_id": cont_id,
                "container_to_id": cont_id,
            }
            get_model("barcode.safe.in.line").create(vals)
        obj.write({"container": None})
        return {
            "flash": "Product Added from container %s" % container.number,
            "focus_field": "container",
        }

BarcodeSafeIn.register()
