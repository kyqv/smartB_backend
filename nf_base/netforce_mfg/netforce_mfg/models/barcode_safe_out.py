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


class BarcodeSafeOut(Model):
    _name = "barcode.safe.out"
    _transient = True
    _fields = {
        "location_from_id": fields.Many2One("stock.location", "From Location", condition=[["type", "=", "internal"]]),
        "location_to_id": fields.Many2One("stock.location", "To Location", condition=[["type", "=", "internal"]]),
        "product_categ_id": fields.Many2One("product.categ", "Product Category"),
        "production_orders": fields.Many2Many("production.order", "Production Orders"),
        "containers": fields.Many2Many("stock.container", "Containers"),
        "journal_id": fields.Many2One("stock.journal", "Stock Journal"),
        "lines": fields.One2Many("barcode.safe.out.line", "wizard_id", "Lines"),
        "state": fields.Selection([["pending", "Pending"], ["done", "Completed"]], "Status", required=True),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "ref": fields.Char("Pick Number"),
        "container": fields.Many2One("stock.container", "Container"),
    }

    _defaults = {
        "state": "done",
    }

    def fill_products(self, ids, context={}):
        obj = self.browse(ids)[0]
        contents = obj.location_from_id.get_contents(context={"product_categ_id": obj.product_categ_id.id})
        if obj.production_orders:
            for order in obj.production_orders:
                for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
                    existed = False
                    if prod_id != order.product_id.id:
                        continue
                    if cont_id != order.container_id.id:
                        continue
                    used_qty = qty
                    vals = {
                        "wizard_id": obj.id,
                        "product_id": order.product_id.id,
                        "lot_id": lot_id,
                        "qty": used_qty,
                        "uom_id": order.uom_id.id,
                        "qty2": qty2,
                        "container_from_id": order.container_id.id,
                        "container_to_id": order.container_id.id,
                        "production_id": order.id,
                    }
                    for line in obj.lines:
                        if vals["wizard_id"] == line.wizard_id.id and \
                                vals["product_id"] == line.product_id.id and \
                                vals["lot_id"] == line.lot_id.id and \
                                vals["qty"] == line.qty and \
                                vals["uom_id"] == line.uom_id.id and \
                                vals["container_from_id"] == line.container_from_id.id and \
                                vals["container_to_id"] == line.container_to_id.id and \
                                vals["production_id"] == line.production_id.id:
                            existed = True
                    if not existed:
                        get_model("barcode.safe.out.line").create(vals)
                for comp in order.components:
                    qty_remain = comp.qty_planned - comp.qty_issued
                    if qty_remain < 0.001:
                        continue
                    for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
                        existed = False
                        if prod_id != comp.product_id.id:
                            continue
                        if cont_id != comp.container_id.id:
                            continue
                        # used_qty=min(qty,qty_remain)
                        used_qty = qty
                        qty_remain -= used_qty  # TODO: deduct from contents in case many MO same container?
                        vals = {
                            "wizard_id": obj.id,
                            "product_id": comp.product_id.id,
                            "lot_id": lot_id,
                            "qty": used_qty,
                            "uom_id": comp.uom_id.id,  # TODO: convert UoM
                            "container_from_id": comp.container_id.id,
                            "container_to_id": comp.container_id.id,
                            "production_id": order.id,
                        }
                        for line in obj.lines:
                            if vals["wizard_id"] == line.wizard_id.id and \
                                    vals["product_id"] == line.product_id.id and \
                                    vals["lot_id"] == line.lot_id.id and \
                                    vals["qty"] == line.qty and \
                                    vals["uom_id"] == line.uom_id.id and \
                                    vals["container_from_id"] == line.container_from_id.id and \
                                    vals["container_to_id"] == line.container_to_id.id and \
                                    vals["production_id"] == line.production_id.id:
                                existed = True
                        if not existed:
                            get_model("barcode.safe.out.line").create(vals)
                        if qty_remain < 0.001:
                            break
        else:
            for (prod_id, lot_id, cont_id), (qty, amt, qty2) in contents.items():
                existed = False
                prod = get_model("product").browse(prod_id)
                vals = {
                    "wizard_id": obj.id,
                    "product_id": prod_id,
                    "lot_id": lot_id,
                    "qty": qty,
                    "uom_id": prod.uom_id.id,
                    "container_from_id": cont_id,
                    "container_to_id": cont_id,
                }
                for line in obj.lines:
                    if vals["wizard_id"] == line.wizard_id.id and \
                            vals["product_id"] == line.product_id.id and \
                            vals["lot_id"] == line.lot_id.id and \
                            vals["uom_id"] == line.uom_id.id and \
                            vals["container_from_id"] == line.container_from_id.id and \
                            vals["container_to_id"] == line.container_to_id.id:
                        existed = True
                if not existed:
                    get_model("barcode.safe.out.line").create(vals)
        obj.write({"product_categ_id": None})

    def clear(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "product_categ_id": None,
            "production_orders": [("set", [])],
            "lines": [("delete_all",)],
        }
        obj.write(vals)

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.approved_by_id:
            raise Exception("Open safe has to approved first")
        if not obj.lines:
            raise Exception("Product list is empty")
        pick_vals = {
            "type": "internal",
            "ref": "Safe To DC",
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
                "ref": line.production_id.number,
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
                "name": "approve_barcode_safe_out",
                "refer_id": obj.id,
            }
        }

    def approve(self, ids, context={}):
        if not check_permission_other("production_safe_out"):
            raise Exception("Permission denied")
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"approved_by_id": user_id})
        return {
            "next": {
                "name": "barcode_safe_out",
                "active_id": obj.id,
            },
            "flash": "Safe to DC approved successfully",
        }

    def disapprove(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"approved_by_id": None})
        return {
            "flash": "Disapprove successfully",
        }

    def run_report(self, ids, context={}):
        print("barcode.safe.out run_report")
        # obj.write({"is_printed":True})
        return {
            "next": {
                "name": "report_safe_out",
                "ids": ids,
            }
        }

    def get_report_data(self, ids, context={}):
        print("barcode.safe.out get_report_data", ids)
        obj = self.browse(ids)[0]
        data = {
            "location_from": obj.location_from_id.name,
            "location_to": obj.location_to_id.name,
            "lines": [],
        }
        for line in obj.lines:
            vals = {
                "container_number": line.container_to_id.number,
                "prod_code": line.product_id.code,
                "prod_description": line.product_id.description,
                "qty": round(line.qty, 2),
                "uom": line.product_id.uom_id.name,
                "production_location": line.production_id.name,
                "state": line.production_id.state,
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
            get_model("barcode.safe.out.line").create(vals)
        obj.write({"container": None})
        return {
            "flash": "Product Added from container %s" % container.number,
            "focus_field": "container",
        }

BarcodeSafeOut.register()
