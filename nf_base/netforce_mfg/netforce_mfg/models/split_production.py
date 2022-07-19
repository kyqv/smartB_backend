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
import re
from netforce.access import get_active_company, get_active_user, check_permission_other


class SplitProduction(Model):
    _name = "split.production"
    _transient = True
    _fields = {
        "order_id": fields.Many2One("production.order", "Production Order", required=True),
        "order_to_id": fields.Many2One("production.order", "To Production Order", required=True),
        "product_list": fields.Json("Product List"),
        "order_to_list": fields.Json("Production To List"),
        "product_id": fields.Many2One("product", "Product"),
        "planned_qty": fields.Decimal("Planned Qty", readonly=True),
        "actual_qty": fields.Decimal("Actual Qty", readonly=True),
        "split_qty": fields.Decimal("Split Qty"),
        "split_qty2": fields.Decimal("Split Secondary Qty"),
        "team_id": fields.Many2One("mfg.team", "Production Team"),
        "remark": fields.Char("Remark"),
        "ratio_method": fields.Selection([["planned", "Planned Qty"], ["actual", "Actual Qty"]], "Ratio Method", required=True),
        "journal_id": fields.Many2One("stock.journal", "Journal", required=True, condition=[["type", "=", "internal"]]),
        "container_id": fields.Many2One("stock.container", "Container"),
        "lines": fields.One2Many("split.production.line", "wizard_id", "Lines"),
        "remain_planned_qty": fields.Decimal("Remain Planned Qty", function="get_remain_planned_qty"),
        "remain_actual_qty": fields.Decimal("Remain Actual Qty", function="get_remain_actual_qty"),
        "approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
    }

    def _get_planned_qty(self, context={}):
        order_id = int(context["refer_id"])
        order = get_model("production.order").browse(order_id)
        return order.qty_planned

    def _get_actual_qty(self, context={}):
        order_id = int(context["refer_id"])
        order = get_model("production.order").browse(order_id)
        return order.qty_received

    def _get_product(self, context={}):
        order_id = int(context["refer_id"])
        order = get_model("production.order").browse(order_id)
        return order.product_id.id

    def _get_container_id(self, context={}):
        order_id = int(context["refer_id"])
        order = get_model("production.order").browse(order_id)
        return order.container_id.id

    def _get_product_ids(self, context={}):
        order_id = int(context["refer_id"])
        order = get_model("production.order").browse(order_id)
        prods = []
        for comp in order.components:
            prods.append(comp.product_id.id)
        prods.append(order.product_id.id)
        return prods

    def _get_order_to_ids(self, context={}):
        order_id = int(context["refer_id"])
        order = get_model("production.order").browse(order_id)
        order_to_ids = self.get_order_to_list(order.id)
        return order_to_ids

    _defaults = {
        "order_id": lambda self, ctx: int(ctx["refer_id"]),
        "planned_qty": _get_planned_qty,
        "actual_qty": _get_actual_qty,
        "product_id": _get_product,
        "product_list": _get_product_ids,
        "order_to_list": _get_order_to_ids,
        #"split_parents": True,
        "split_qty": 0,
        "container_id": _get_container_id,
        "ratio_method": "actual",
        "remain_planned_qty": _get_planned_qty,
        "remain_actual_qty": _get_actual_qty
    }

    def get_product_list(self, order_id):
        prods = []
        order = get_model("production.order").browse(order_id)
        if order:
            for comp in order.components:
                prods.append(comp.product_id.id)
            prods.append(order.product_id.id)
        return prods

    def get_product_ids(self, ids, context={}):
        res = {}
        prods = []
        obj = self.browse(ids)[0]
        order = obj.order_id
        if order:
            for comp in order.components:
                prods.append(comp.product_id.id)
            prods.append(order.product_id.id)
        res[obj.id] = prods
        return res

    def get_order_to_list(self, order_id):
        order_to_ids = [order_id]
        order = get_model("production.order").browse(order_id)
        order_parent = order.parent_id
        while order_parent:
            order_to_ids.append(order_parent.id)
            order_parent = order_parent.parent_id
        order_to_ids = list(set(order_to_ids))
        return order_to_ids

    def get_order_to_ids(self, ids, context={}):
        res = {}
        obj = self.browse(ids)[0]
        order_id = obj.order_id.id
        res[obj.id] = self.get_order_to_list(order_id)
        return res

    def get_remain_actual_qty(self, ids, context={}):
        res = {}
        obj = self.browse(ids)[0]
        if obj.ratio_method == "actual":
            total_qty = 0
            for line in obj.lines:
                total_qty += line.qty
            res[obj.id] = obj.actual_qty - total_qty
        else:
            res[obj.id] = obj.actual_qty
        return res

    def get_remain_planned_qty(self, ids, context={}):
        res = {}
        obj = self.browse(ids)[0]
        if obj.ratio_method == "planned":
            total_qty = 0
            for line in obj.lines:
                total_qty += line.qty
            res[obj.id] = obj.planned_qty - total_qty
        else:
            res[obj.id] = obj.planned_qty
        return res

    def onchange_order(self, context={}):
        data = context["data"]
        order_id = data["order_id"]
        order = get_model("production.order").browse(order_id)
        data["product_list"] = self.get_product_list(order_id)
        data["product_id"] = order.product_id.id
        data["order_to_list"] = self.get_order_to_list(order_id)
        data["order_to_id"] = None
        self.onchange_product(context)
        return data

    def get_split_num(self, root_num, context={}):
        root_num = re.sub("-P[0-9][0-9]$", "", root_num)
        for i in range(2, 100):
            num = root_num + "-P%.2d" % i
            res = get_model("production.order").search([["number", "=", num]])
            if not res:
                return num
        raise Exception("Failed to generate production order number (root=%s)" % root_num)

    def get_split_container(self, prev_cont_num, order_num, context={}):
        part_no = order_num.rpartition("-")[2]
        if not part_no or not part_no.startswith("P") or not len(part_no) == 3:
            raise Exception("Can not find split part number of production order %s" % order_num)
        new_cont_num = prev_cont_num + "-" + part_no
        res = get_model("stock.container").search([["number", "=", new_cont_num]])
        if res:
            new_cont_id = res[0]
        else:
            vals = {
                "number": new_cont_num,
            }
            new_cont_id = get_model("stock.container").create(vals)
        return new_cont_id

    def check_split_container(self, order_comp_id):
        return True

    def get_lot(self, new_lot_num, context={}):
        res = get_model("stock.lot").search([["number", "=", new_lot_num]])
        if res:
            new_lot_id = res[0]
        else:
            vals = {
                "number": new_lot_num,
            }
            new_lot_id = get_model("stock.lot").create(vals)
        return new_lot_id

    def copy_order(self, order_id, qty, team_id, remark):
        order = get_model("production.order").browse(order_id)
        old_order_num = order.number
        new_order_num = self.get_split_num(old_order_num)
        vals = {
            "number": new_order_num,
            "order_date": time.strftime("%Y-%m-%d"),
            "due_date": order.due_date,
            "ref": order.ref,
            "sale_id": order.sale_id.id,
            "parent_id": order.parent_id.id,
            "product_id": order.product_id.id,
            "qty_planned": qty,
            "uom_id": order.uom_id.id,
            "bom_id": order.bom_id.id,
            "routing_id": order.routing_id.id,
            "production_location_id": order.production_location_id.id,
            "location_id": order.location_id.id,
            "team_id": team_id,
            "remark": remark,
            "state": order.state,
            "components": [],
            "operations": [],
        }
        if order.container_id:
            vals["container_id"] = self.get_split_container(order.container_id.number, new_order_num)
        if order.lot_id and order.lot_id.number == old_order_num:  # XXX
            vals["lot_id"] = self.get_lot(new_order_num)
        ratio = qty / order.qty_planned
        for comp in order.components:
            comp_vals = {
                "product_id": comp.product_id.id,
                "qty_planned": round(comp.qty_planned * ratio, 2),
                "uom_id": comp.uom_id.id,
                "location_id": comp.location_id.id,
                "issue_method": comp.issue_method,
                "container_id": comp.container_id.id,
            }
            if comp.container_id and self.check_split_container(comp.id):  # MTS need no need to split scrap box
                comp_vals["container_id"] = self.get_split_container(comp.container_id.number, new_order_num)
            # if comp.lot_id and comp.lot_id.number==old_order_num: # XXX
                # comp_vals["lot_id"]=self.get_lot(new_order_num)
            comp_vals["lot_id"] = comp.lot_id.id  # Should be old number
            vals["components"].append(("create", comp_vals))
        for op in order.operations:
            op_vals = {
                "workcenter_id": op.workcenter_id.id,
                "employee_id": op.employee_id.id,
                "planned_duration": op.planned_duration * ratio,
            }
            vals["operations"].append(("create", op_vals))
        new_id = get_model("production.order").create(vals)
        return new_id

    def modif_order(self, order_id, qty, team_id, remark):
        order = get_model("production.order").browse(order_id)
        ratio = qty / order.qty_planned
        old_order_num = order.number
        new_order_num = old_order_num + "-P01"
        vals = {
            "number": new_order_num,
            "qty_planned": round(order.qty_planned * ratio, 2),
            "team_id": team_id,
            "remark": remark,
        }
        if order.container_id:
            vals["container_id"] = self.get_split_container(order.container_id.number, new_order_num)
        if order.lot_id and order.lot_id.number == old_order_num:  # XXX
            vals["lot_id"] = self.get_lot(new_order_num)
        order.write(vals)
        for comp in order.components:
            vals = {
                "qty_planned": round(comp.qty_planned * ratio, 2),
            }
            if comp.container_id and self.check_split_container(comp.id):  # MTS no need to split scrap box
                vals["container_id"] = self.get_split_container(comp.container_id.number, new_order_num)
            # if comp.lot_id and comp.lot_id.number==old_order_num: # XXX
                # vals["lot_id"]=self.get_lot(new_order_num)
            vals["lot_id"] = comp.lot_id.id  # Should be old number
            comp.write(vals)
        for op in order.operations:
            vals = {
                "planned_duration": op.planned_duration * ratio,
            }
            op.write(vals)

    def split_order(self, order_id, ratios):
        order = get_model("production.order").browse(order_id)
        if order.state not in ("draft", "waiting_confirm", "waiting_material", "waiting_suborder", "ready", "in_progress"):
            raise Exception("Invalid state to split order (%s)" % order.number)
        for r in ratios[:1]:
            split_ids = [(r[2], order_id)]
        for r in ratios[1:]:
            split_qty = order.qty_planned * r[0]
            team_id = r[1]
            remark = r[3]
            split_id = self.copy_order(order.id, split_qty, team_id, remark)
            split_ids.append((r[2], split_id))
        r = ratios[0]
        split_qty = order.qty_planned * r[0]
        team_id = r[1]
        remark = r[3]
        self.modif_order(order.id, split_qty, team_id, remark)
        for sub in order.sub_orders:
            if sub.state not in ("draft", "waiting_confirm", "waiting_material", "waiting_suborder", "ready", "in_progress"):
                continue
            sub_split_ids = self.split_order(sub.id, ratios)
            if sub.sub_orders:
                split_ids += sub_split_ids
            for i in range(len(sub_split_ids)):
                sub_split_id = sub_split_ids[i][1]
                split_id = split_ids[i][1]
                get_model("production.order").write([sub_split_id], {"parent_id": split_id})
        return split_ids

    def do_split(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.approved_by_id:
            raise Exception("Split order has to be approved first")
        order = obj.order_id
        if len(obj.lines) < 2:
            raise Exception("Split needs at least 2 lines")
        total_qty = sum(l.qty for l in obj.lines)
        if not obj.ratio_method:
            raise Exception("Please select ratio method")
        if obj.ratio_method == "planned" and abs(total_qty - obj.planned_qty) > 0.01:
            raise Exception("Total split qty has to be equal to planned qty")
        if obj.ratio_method == "actual" and abs(total_qty - obj.actual_qty) > 0.01:
            raise Exception("Total split qty has to be equal to actual qty")
        ratios = []
        if obj.ratio_method == "planned":
            for line in obj.lines:
                ratios.append((line.qty / obj.planned_qty, line.team_id.id, line.id, line.remark))
        elif obj.ratio_method == "actual":
            for line in obj.lines:
                ratios.append((line.qty / obj.actual_qty, line.team_id.id, line.id, line.remark))
        split_order = order
        if obj.order_to_id:
            # if obj.split_parents:
            while split_order.parent_id:
                split_order = split_order.parent_id
                if split_order.id == obj.order_to_id.id:
                    break
        split_order_ids = self.split_order(split_order.id, ratios)

        # Combine Split Order
        end_order = obj.order_id.parent_id
        if obj.order_to_id and obj.order_to_id.parent_id:
            end_order = obj.order_to_id.parent_id
        if end_order:
            comps = []
            for end_sub in end_order.sub_orders:
                for comp in end_order.components:
                    if comp.product_id.id == end_sub.product_id.id:
                        comps.append((comp.product_id.id, comp.location_id.id, comp.issued_method))
                        comp.delete()
            comps = list(set(comps))
            for prod_id, loc_id, issued_method in comps:
                for end_sub in end_order.sub_orders:
                    if end_sub.product_id.id == prod_id:
                        vals = {
                            "order_id": end_order.id,
                            "product_id": end_sub.product_id.id,
                            "qty_planned": end_sub.qty_planned,
                            "uom_id": end_sub.uom_id.id,
                            "location_id": loc_id,
                            "issue_method": issued_method,
                            "lot_id": end_sub.lot_id.id,
                            "container_id": end_sub.container_id.id,
                        }
                        get_model("production.component").create(vals)

        if obj.ratio_method == "actual":
            self.split_transfer(split_order_ids=split_order_ids, split_prod_id=obj.id)
        return {
            "next": {
                "name": "production",
            },
            "flash": "Order split successfully",
        }

    def split_transfer(self, split_order_ids, split_prod_id):
        split_prod = get_model("split.production").browse(split_prod_id)
        pick_vals = {
            "type": "internal",
            "journal_id": split_prod.journal_id.id,
            "lines": [],
            "done_approved_by_id": split_prod.approved_by_id.id
        }
        for split_line, split_order_id in split_order_ids:
            split_order = get_model("production.order").browse(split_order_id)
            for line in split_prod.lines:
                cont_to_id = None
                lot_id = None
                if line.id == split_line:
                    if split_prod.product_id.id == split_order.product_id.id:
                        lot_id = split_order.lot_id.id
                        cont_to_id = split_order.container_id.id
                    else:
                        for comp in split_order.components:
                            if split_prod.product_id.id == comp.product_id.id:
                                lot_id = comp.lot_id.id
                                cont_to_id = comp.container_id.id
                if cont_to_id:
                    break
            if cont_to_id:
                move_vals = {
                    "product_id": split_prod.product_id.id,
                    "qty": line.qty,
                    "uom_id": split_prod.product_id.uom_id.id,
                    "qty2": line.qty2,
                    "lot_id": lot_id,
                    "location_from_id": split_prod.order_id.location_id.id,
                    "location_to_id": split_prod.order_id.location_id.id,
                    "container_from_id": split_prod.container_id.id,
                    "container_to_id": cont_to_id,
                }
                pick_vals["lines"].append(("create", move_vals))
        if len(pick_vals["lines"]) > 0:
            pick_id = get_model("stock.picking").create(pick_vals, context=pick_vals)
            get_model("stock.picking").set_done([pick_id])
            split_order_ids.reverse()
        for order_id in split_order_ids:
            order = get_model("production.order").browse(order_id[1])
            if order.parent_id:
                order.parent_id.update_status()

    def approve(self, ids, context={}):
        if not check_permission_other("production_approve_split"):
            raise Exception("Permission denied")
        obj = self.browse(ids)[0]
        user_id = get_active_user()
        obj.write({"approved_by_id": user_id})
        return {
            "next": {
                "name": "split_production",
                "active_id": obj.id,
            },
            "flash": "Split order approved successfully",
        }

    def onchange_product(self, context={}):
        data = context["data"]
        order_id = data["order_id"]
        order = get_model("production.order").browse(order_id)
        prod_id = data["product_id"]
        data["planned_qty"] = 0
        data["actual_qty"] = 0
        if order.product_id.id == prod_id:
            data["planned_qty"] = order.qty_planned
            data["actual_qty"] = order.qty_received
            data["container_id"] = order.container_id.id
        else:
            for comp in order.components:
                if comp.product_id.id == prod_id:
                    data["planned_qty"] = comp.qty_planned
                    data["actual_qty"] = comp.qty_stock
                    data["container_id"] = comp.container_id.id
        data["remain_planned_qty"] = data["planned_qty"]
        data["remain_actual_qty"] = data["actual_qty"]
        return data

    def add_lines(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.ratio_method:
            raise Exception("Invalid Ratio Method")
        remain = obj.remain_planned_qty if obj.ratio_method == "planned" else obj.remain_actual_qty
        total_qty = 0
        for line in obj.lines:
            if line.product_id.id != obj.product_id.id \
                    or line.ratio_method != obj.ratio_method:
                line.delete()
        for line in obj.lines:
            total_qty += line.qty
        if obj.split_qty != 0 and remain + 0.001 >= obj.split_qty:
            # part_no=len(obj.lines)+1
            # cont_num=obj.container_id.number+"-P%.2d"%part_no
            vals = {
                "wizard_id": obj.id,
                "ratio_method": obj.ratio_method,
                "product_id": obj.product_id.id,
                "qty": obj.split_qty,
                "qty2": obj.split_qty2,
                "team_id": obj.team_id.id,
                "remark": obj.remark,
                #"container_num": cont_num,
            }
            get_model("split.production.line").create(vals)
            # part_no=1
            # for line in obj.lines:
            # cont_num=obj.container_id.number+"-P%.2d"%part_no
            #line.write({"container_num": cont_num})
            # part_no+=1
            obj.split_qty = 0
            obj.team_id = None
        else:
            raise Exception("Split Qty is too high!")
        return {
            "flash": "Add line success",
            "focus_field": "split_qty"
        }

    def clear_lines(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"lines": [("delete_all",)]})
        return {
            "flash": "Clear all split lines",
            "focus_field": "split_qty"
        }

SplitProduction.register()
