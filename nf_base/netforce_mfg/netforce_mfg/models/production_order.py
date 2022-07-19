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
from datetime import *
import time
from netforce import database
from netforce.utils import get_file_path
from netforce.access import get_active_company, get_active_user, check_permission_other
from netforce.utils import get_data_path
from netforce import access


class ProductionOrder(Model):
    _name = "production.order"
    _string = "Production Order"
    _name_field = "number"
    _multi_company = True
    _key = ["company_id", "number"]  # need migration first otherwise can't add constraint...
    _audit_log = True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Reference", search=True), 
        "related_id": fields.Reference([["sale.order","Sales Order"]], "Related To"),
        "date_created": fields.Date("Date Created", required=True, search=True),
        "order_date": fields.Date("Start Date", required=True, search=True),
        "customer_id": fields.Many2One("contact", "Customer"),
        "due_date": fields.Date("Due Date",search=True),
        "due_date_week": fields.Char("Due Date Week",function="get_date_agg",function_multi=True),
        "due_date_month": fields.Char("Due Date Month",function="get_date_agg",function_multi=True),
        "location_id": fields.Many2One("stock.location", "FG Warehouse", required=True, condition=[["type", "=", "internal"]]),
        "product_id": fields.Many2One("product", "FG Product", required=True, search=True, condition=[["supply_method","=","production"]]),
        "qty_planned": fields.Decimal("Planned Qty", required=True, scale=6),
        "qty_received": fields.Decimal("Received Qty", function="get_qty_received", function_multi=True, scale=6),
        "qty_received_uos": fields.Decimal("Received Qty (UoS)", function="get_qty_received_uos", scale=6),
        "qty2_received": fields.Decimal("Received Secondary Qty", function="get_qty_received", function_multi=True, scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "bom_id": fields.Many2One("bom", "Bill of Material"),
        "routing_id": fields.Many2One("routing", "Routing"),
        "components": fields.One2Many("production.component", "order_id", "Components"),
        "operations": fields.One2Many("production.operation", "order_id", "Operations"),
        "qc_results": fields.One2Many("qc.result", "production_id", "QC Results"),
        "state": fields.Selection([["draft", "Draft"], ["confirmed","Confirmed"], ["in_progress", "In Progress"], ["done", "Completed"], ["voided", "Voided"]], "Status", required=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "sale_id": fields.Many2One("sale.order", "Sales Order", search=True),
        "parent_id": fields.Many2One("production.order", "Parent Production Order", search=True),
        "sub_orders": fields.One2Many("production.order", "parent_id", "Sub Production Orders"),
        "production_location_id": fields.Many2One("stock.location", "Production Location"),
        "overdue": fields.Boolean("Overdue", function="get_overdue", function_search="search_overdue"),
        "team_id": fields.Many2One("mfg.team", "Team", search=True),
        "time_start": fields.DateTime("Start Time", readonly=True),
        "time_stop": fields.DateTime("Finish Time", readonly=True),
        "duration": fields.Decimal("Duration (Hours)", function="get_duration"),
        "done_qty_loss_approved_by_id": fields.Many2One("base.user", "Approved Qty Loss By", readonly=True),
        "split_approved_by_id": fields.Many2One("base.user", "Approved By", readonly=True),
        "container_id": fields.Many2One("stock.container", "FG Container"),
        "lot_id": fields.Many2One("stock.lot", "FG Lot"),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "remark": fields.Text("Remark"),
        "company_id": fields.Many2One("company", "Company"),
        "supplier_id": fields.Many2One("contact", "Supplier"),
        "pickings": fields.Many2Many("stock.picking", "Stock Pickings", function="get_pickings"),
        "invoices": fields.One2Many("account.invoice", "related_id", "Invoices"),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "track_id": fields.Many2One("account.track.categ","Tracking Code"),
        "track_entries": fields.One2Many("account.track.entry",None,"Tracking Entries",function="get_track_entries",function_write="write_track_entries"),
        "track_balance": fields.Decimal("Tracking Balance",function="_get_related",function_context={"path":"track_id.balance"}),
        "total_rm_cost": fields.Decimal("Total RM Cost",function="get_total_cost",function_multi=True),
        "total_cost": fields.Float("Total FG Cost",function="get_total_cost",function_multi=True),
        "unit_cost": fields.Float("FG Unit Cost",function="get_total_cost",function_multi=True),
        "period_id": fields.Many2One("production.period","Production Period"),
        "sale_lines": fields.One2Many("sale.order.line","production_id","Sales Order Lines"),
        "purchase_orders": fields.One2Many("purchase.order","related_id","Purchase Orders"),
        "receive_fg_qty": fields.Decimal("Received Qty"), 
        "receive_fg_qty_gb": fields.Decimal("Received Qty (Grade-B)"), # XXX: deprecated
        "receive_fg_qty_waste": fields.Decimal("Received Qty (Waste)"), # XXX: deprecated 
        "receive_fg_done": fields.Boolean("Complete Production Order"), 
        "gradings": fields.One2Many("stock.grade.line","production_id","Gradings"),
        "adjust_rm_product_id": fields.Many2One("product","RM Product"), 
        "adjust_rm_qty": fields.Decimal("Issued Qty"), 
        "qc_checked": fields.Boolean("QC Checked"),
        "received_date": fields.Date("Received Date",function="get_received_date"),
    }
    _order = "number desc, id desc"

    def _get_number(self, context={}):
        while 1:
            num = get_model("sequence").get_number("production")
            if not num:
                return None
            user_id = access.get_active_user()
            access.set_active_user(1)
            res = self.search([["number", "=", num ]])
            access.set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment("production")

    _defaults = {
        "number": _get_number,
        "state": "draft",
        "order_date": lambda *a: time.strftime("%Y-%m-%d"),
        "date_created": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
    }

    def get_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d=datetime.strptime(obj.due_date,"%Y-%m-%d") if obj.due_date else None
            due_month=d.strftime("%Y-%m") if obj.due_date else None
            due_week=d.strftime("%Y-W%W") if obj.due_date else None
            vals[obj.id]={
                "due_date_week": due_week,
                "due_date_month": due_month,
            }
        return vals

    def onchange_product(self, context):
        data = context["data"]
        prod_id = data["product_id"]
        prod = get_model("product").browse(prod_id)
        data["qty_planned"] = 1
        if prod.uom_id:
            data["uom_id"] = prod.uom_id.id
        res=get_model("bom").search([["product_id","=",prod_id]])
        if res:
            data["bom_id"]=res[0]
            data=self.onchange_bom(context)
        return data

    def onchange_bom(self, context):
        data = context["data"]
        bom_id = data["bom_id"]
        bom = get_model("bom").browse(bom_id)
        data["routing_id"] = bom.routing_id.id
        data["location_id"] = bom.location_id.id
        data["production_location_id"] = bom.production_location_id.id
        if not data["uom_id"]:
            data["uom_id"] = bom.uom_id.id
        components = []
        def _add_components(bom,qty_planned,order_uom_id):
            ratio = (qty_planned or 0) / bom.qty
            if order_uom_id != bom.uom_id.id:
                prod_order_uom = get_model("uom").browse(order_uom_id)
                ratio = ratio / prod_order_uom.ratio / bom.uom_id.ratio
            for line in bom.lines:
                prod=line.product_id
                res=get_model("bom").search([["product_id","=",prod.id]])
                ph_bom=None
                if res:
                    rm_bom_id=res[0]
                    rm_bom=get_model("bom").browse(rm_bom_id)
                    if rm_bom.type=="phantom":
                        ph_bom=rm_bom
                if ph_bom:
                    qty_planned=round(line.qty * ratio, 2)
                    _add_components(ph_bom,qty_planned,line.uom_id.id)
                else:
                    components.append({
                        "product_id": line.product_id.id,
                        "qty_planned": round(line.qty * ratio, 2),
                        "uom_id": line.uom_id.id,
                        "location_id": line.location_id.id,
                        "issue_method": line.issue_method,
                        "notes": line.notes,
                    })
        _add_components(bom,data["qty_planned"],data["uom_id"])
        data["components"] = components
        routing = bom.routing_id
        if routing:
            ratio = (data["qty_planned"] or 0) / bom.qty
            ops = []
            for line in routing.lines:
                ops.append({
                    "workcenter_id": line.workcenter_id.id,
                    "planned_duration": (line.duration or 0) * ratio,
                })
            data["operations"] = ops
        return data

    def onchange_routing(self, context):
        data = context["data"]
        bom_id = data["bom_id"]
        qty_planned = data["qty_planned"]
        bom = get_model("bom").browse(bom_id)
        ratio = qty_planned / bom.qty
        routing_id = data["routing_id"]
        routing = get_model("routing").browse(routing_id)
        ops = []
        for line in routing.lines:
            ops.append({
                "workcenter_id": line.workcenter_id.id,
                "planned_duration": (line.duration or 0) * ratio,
            })
        data["operations"] = ops
        return data

    def create_components(self, ids, context={}):
        for obj in self.browse(ids):
            bom = obj.bom_id
            if not bom:
                continue
            ratio = obj.qty_planned / bom.qty
            for line in bom.lines:
                if not line.location_id:
                    raise Exception("Missing location for RM %s in BoM %s"%(line.product_id.name,bom.number))
                prod=line.product_id
                res=get_model("bom").search([["product_id","=",prod.id]])
                ph_bom_id=None
                if res:
                    rm_bom_id=res[0]
                    rm_bom=get_model("bom").browse(rm_bom_id)
                    if rm_bom.type=="phantom":
                        ph_bom_id=rm_bom.id
                if ph_bom_id:
                    qty_planned=round(line.qty * ratio, 2)
                    obj.create_phantom_components(ph_bom_id,qty_planned)
                else:
                    vals = {
                        "order_id": obj.id,
                        "product_id": prod.id,
                        "qty_planned": round(line.qty * ratio, 2),
                        "uom_id": line.uom_id.id,
                        "location_id": line.location_id.id,
                        "issue_method": line.issue_method,
                        "notes": line.notes,
                    }
                    get_model("production.component").create(vals)

    def create_phantom_components(self, ids, bom_id, qty_planned, context={}):
        obj=self.browse(ids[0])
        bom=get_model("bom").browse(bom_id)
        ratio = qty_planned / bom.qty
        for line in bom.lines:
            if not line.location_id:
                raise Exception("Missing location for RM %s in BoM %s"%(line.product_id.name,bom.number))
            prod=line.product_id
            res=get_model("bom").search([["product_id","=",prod.id]])
            ph_bom_id=None
            if res:
                rm_bom_id=res[0]
                rm_bom=get_model("bom").browse(rm_bom_id)
                if rm_bom.type=="phantom":
                    ph_bom_id=rm_bom.id
            if ph_bom_id:
                qty_planned=round(line.qty * ratio, 2)
                obj.create_phantom_components(ph_bom_id,qty_planned)
            else:
                vals = {
                    "order_id": obj.id,
                    "product_id": prod.id,
                    "qty_planned": round(line.qty * ratio, 2),
                    "uom_id": line.uom_id.id,
                    "location_id": line.location_id.id,
                    "issue_method": line.issue_method,
                }
                get_model("production.component").create(vals)

    def create_operations(self, ids, context={}):
        for obj in self.browse(ids):
            bom = obj.bom_id
            if not bom:
                continue
            ratio = obj.qty_planned / bom.qty
            routing = bom.routing_id
            if not routing:
                continue
            for line in routing.lines:
                vals = {
                    "order_id": obj.id,
                    "workcenter_id": line.workcenter_id.id,
                    "planned_duration": (line.duration or 0) * ratio,
                }
                get_model("production.operation").create(vals)

    def confirm(self, ids, context={}):
        settings = get_model("settings").browse(1)
        if settings.approve_production and not access.check_permission_other("approve_production"):
            raise Exception("User does not have permission to approve production orders (approve_production).")
        for obj in self.browse(ids):
            if not obj.due_date:
                raise Exception("Missing due date")
            if not obj.production_location_id:
                raise Exception("Missing production location in order %s ([%s] %s)"%(obj.number,obj.product_id.code,obj.product_id.name))
            obj.write({"state": "confirmed"})
            obj.create_planned_moves()
            obj.create_planned_purchase()

    def in_progress(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "in_progress"})
            if not obj.time_start:
                t = time.strftime("%Y-%m-%d %H:%M:%S")
                obj.write({"time_start": t})

    def done(self, ids, context={}):
        for obj in self.browse(ids):
            obj.create_fg_moves(date=obj.due_date)
            obj.create_backflush_moves(date=obj.order_date)
            obj.clear_wip_moves()
            obj.delete_planned_moves()
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            obj.write({"state": "done", "time_stop": t})

    def get_qty_received(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_qty = {
                "qty_received": 0,
                "qty2_received": 0,
            }
            for pick in obj.pickings:
                for move in pick.lines:
                    if move.product_id.id != obj.product_id.id or move.state != "done":
                        continue
                    qty = get_model("uom").convert(move.qty, move.uom_id.id, obj.uom_id.id)
                    if obj.components[0].product_id.id==obj.product_id.id and pick.type=="out":  #Max 2020 Oct 22
                        continue
                    if move.location_from_id.id != obj.location_id.id and move.location_to_id.id == obj.location_id.id:
                        total_qty["qty_received"] += qty or 0
                        total_qty["qty2_received"] += move.qty2 or 0
                    elif move.location_from_id.id == obj.location_id.id and move.location_to_id.id != obj.location_id.id:
                        total_qty["qty_received"] -= qty or 0
                        total_qty["qty2_received"] -= move.qty2 or 0
            vals[obj.id] = total_qty
        return vals

    def get_qty_received_uos(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            prod = get_model("product").browse(obj.product_id.id)
            if prod and prod["uos_factor"] and prod["uos_factor"] != 0:
                vals[obj.id] = round(obj.qty_received / prod["uos_factor"], 2)
        return vals

    def copy_to_pick_out(self, ids, rm_product_id=None, rm_qty=None, date=None, set_done=False, context={}):
        obj = self.browse(ids)[0]
        if obj.production_location_id.type=="internal":
            pick_type="internal"
        else:
            pick_type="out"
        pick_vals = {
            "type": pick_type,
            "ref": obj.number+" RM",
            "related_id": "production.order,%s" % obj.id,
            "lines": [],
        }
        if date:
            pick_vals["date"]=date+" 00:00:00"
        for comp in obj.components:
            if rm_product_id and comp.product_id.id!=rm_product_id:
                continue
            if comp.location_id.id==obj.production_location_id.id:
                continue
            if rm_qty:
                qty_remain=rm_qty
            else:
                qty_remain = comp.qty_planned - comp.qty_issued
                if qty_remain <= 0.001:
                    continue
            if qty_remain>0:
                line_vals = {
                    "product_id": comp.product_id.id,
                    "qty": qty_remain,
                    "uom_id": comp.uom_id.id,
                    "location_from_id": comp.location_id.id,
                    "location_to_id": obj.production_location_id.id,
                    "related_id": "production.order,%s" % obj.id,
                }
            else:
                line_vals = {
                    "product_id": comp.product_id.id,
                    "qty": -qty_remain,
                    "uom_id": comp.uom_id.id,
                    "location_from_id": obj.production_location_id.id,
                    "location_to_id": comp.location_id.id,
                    "related_id": "production.order,%s" % obj.id,
                }
            pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            return {
                "flash": "Nothing remaining to issue",
            }
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": pick_type})
        pick = get_model("stock.picking").browse(pick_id)
        if set_done:
            pick.set_done()
        return {
            "next": {
                "name": "pick_internal" if pick_type=="internal" else "pick_out",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Picking %s created from production order %s" % (pick.number, obj.number),
            "pick_id": pick_id,
        }

    def copy_to_pick_in(self, ids, qty_received=None, set_done=False, qty_received_gb=None, qty_received_waste=None, date=None, context={}):
        obj = self.browse(ids)[0]
        if obj.production_location_id.type=="internal":
            pick_type="internal"
        else:
            pick_type="in"
        pick_vals = {
            "type": pick_type,
            "ref": obj.number+" FG",
            "related_id": "production.order,%s" % obj.id,
            "lines": [],
        }
        if date:
            pick_vals["date"]=date+" 00:00:00"
        if qty_received!=None:
            qty_remain=qty_received
        else:
            qty_remain = obj.qty_planned - obj.qty_received
        if qty_remain > 0:
            prod=obj.product_id
            line_vals = {
                "product_id": prod.id,
                "qty": qty_remain,
                "uom_id": obj.uom_id.id,
                "location_from_id": obj.production_location_id.id,
                "location_to_id": obj.location_id.id,
                "cost_price": prod.cost_price or 0,
                "cost_amount": (prod.cost_price or 0)*qty_remain,
            }
            pick_vals["lines"].append(("create", line_vals))
        """
        if not qty_received_gb: # XXX
            for comp in obj.components:
                qty_remain = comp.qty_planned - comp.qty_issued
                if qty_remain >= 0:
                    continue
                line_vals = {
                    "product_id": comp.product_id.id,
                    "qty": -qty_remain,
                    "uom_id": comp.uom_id.id,
                    "location_from_id": obj.production_location_id.id,
                    "location_to_id": comp.location_id.id,
                }
                pick_vals["lines"].append(("create", line_vals))
        if qty_received_gb:
            prod=obj.product_id
            prod_gb=prod.product_gb_id
            if not prod_gb:
                raise Exception("Missing grade-B product for %s"%prod.name)
            loc_gb_id=obj.location_id.id
            for comp in obj.components:
                if comp.product_id.id==prod_gb.id:
                    loc_gb_id=comp.location_id.id
                    break
            line_vals = {
                "product_id": prod_gb.id,
                "qty": qty_received_gb,
                "uom_id": prod_gb.uom_id.id,
                "location_from_id": obj.production_location_id.id,
                "location_to_id": loc_gb_id,
            }
            pick_vals["lines"].append(("create", line_vals))
        if qty_received_waste:
            prod=obj.product_id
            res = get_model("stock.location").search([["type", "=", "waste"]])
            if not res:
                raise Exception("Missing waste location")
            waste_loc_id = res[0]
            line_vals = {
                "product_id": prod.id,
                "qty": qty_received_waste,
                "uom_id": prod.uom_id.id,
                "location_from_id": obj.production_location_id.id,
                "location_to_id": waste_loc_id,
            }
            pick_vals["lines"].append(("create", line_vals))
        """
        if not pick_vals["lines"]:
            raise Exception("Nothing remaining to receive")
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": pick_type})
        pick = get_model("stock.picking").browse(pick_id)
        if set_done:
            pick.set_done()
        return {
            "next": {
                "name": "pick_internal" if pick_type=="internal" else "pick_in",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Picking %s created from production order %s" % (pick.number, obj.number),
            "pick_id": pick_id,
        }

    def copy_to_pick_in_done(self,ids,context={}): 
        if 'qty_received' in context:
            qty_received = context['qty_received']
            self.copy_to_pick_in(ids,set_done=True,qty_received=qty_received,context=context)
        else:
            self.copy_to_pick_in(ids,set_done=True,context=context)

    def copy_to_pick_out_done(self,ids,context={}):
        self.copy_to_pick_out(ids,set_done=True,context=context)

    def get_qty_backflush(self, component=None):
        if component:
            return component.qty_planned - component.qty_issued
        return 0

    def void(self, ids, context={}):
        for obj in self.browse(ids):
            for pick in obj.pickings:
                if pick.state!="voided":
                    raise Exception("There are still stock movements related to this order")
        for obj in self.browse(ids):
            obj.write({"state": "voided"})

    def void_related(self,ids,context={}):
        for obj in self.browse(ids):
            for pick in obj.pickings:
                if pick.state!="voided":
                    pick.void()
            obj.void()

    def delete(self, ids, **kw):
        for obj in self.browse(ids):
            for pick in obj.pickings:
                if pick.state!="voided":
                    raise Exception("There are still stock transactions related to this order")
        super().delete(ids, **kw)

    def copy(self, ids, context):
        obj = self.browse(ids)[0]
        vals = {
            "due_date": obj.due_date,
            "product_id": obj.product_id.id,
            "qty_planned": obj.qty_planned,
            "uom_id": obj.uom_id.id,
            "bom_id": obj.bom_id.id,
            "routing_id": obj.routing_id.id,
            "location_id": obj.location_id.id,
            "production_location_id": obj.production_location_id.id,
        }
        comps = []
        for comp in obj.components:
            comps.append({
                "product_id": comp.product_id.id,
                "qty_planned": comp.qty_planned,
                "uom_id": comp.uom_id.id,
                "location_id": comp.location_id.id,
                "issue_method": comp.issue_method,
            })
        vals["components"] = [("create", v) for v in comps]
        opers = []
        for oper in obj.operations:
            opers.append({
                "workcenter_id": oper.workcenter_id.id,
                "planned_duration": oper.planned_duration,
            })
        vals["operations"] = [("create", v) for v in opers]
        prod_id = get_model("production.order").create(vals)
        prod = get_model("production.order").browse(prod_id)
        return {
            "next": {
                "name": "production",
                "mode": "form",
                "active_id": prod_id,
            },
            "flash": "Production order %s copied from %s" % (prod.number, obj.number),
        }

    def copy_to_purchase_old(self, ids, context={}):
        obj = self.browse(ids)[0]
        suppliers = {}
        for line in obj.components:
            prod = line.product_id
            if prod.supply_method != "purchase":
                continue
            if not prod.suppliers:
                raise Exception("Missing supplier for product '%s'" % prod.name)
            supplier_id = prod.suppliers[0].supplier_id.id
            suppliers.setdefault(supplier_id, []).append((prod.id, line.qty_planned, line.uom_id.id,line.location_id.id))
        if not suppliers:
            raise Exception("No purchase orders to create")
        order_ids = []
        for supplier_id, lines in suppliers.items():
            order_vals = {
                "contact_id": supplier_id,
                "ref": obj.number,
                "related_id": "production.order,%s"%obj.id,
                "lines": [],
            }
            for prod_id, qty, uom_id,location_id in lines:
                prod = get_model("product").browse(prod_id)
                line_vals = {
                    "product_id": prod_id,
                    "description": prod.description or "/",
                    "qty": qty,
                    "uom_id": uom_id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "sale_id": obj.sale_id.id,
                    "location_id" : location_id,
                }
                order_vals["lines"].append(("create", line_vals))
            order_id = get_model("purchase.order").create(order_vals)
            order_ids.append(order_id)
        orders = get_model("purchase.order").browse(order_ids)
        return {
            "next": {
                "name": "purchase",
                "search_condition": [["ref", "=", obj.number]],
            },
            "flash": "Purchase orders created successfully: " + ", ".join([o.number for o in orders]),
        }

    def copy_to_purchase(self, ids, context={}):
        suppliers = {}
        sup_refs={}
        for obj in self.browse(ids):
            if obj.state=="voided":
                continue
            for line in obj.components:
                prod = line.product_id
                if not prod:
                    continue
                if prod.supply_method != "purchase":
                    continue
                if not prod.suppliers:
                    raise Exception("Missing supplier for product '%s'" % prod.name)
                supplier_id = prod.suppliers[0].supplier_id.id
                qtys=suppliers.setdefault(supplier_id,{})
                k=(prod.id,line.uom_id.id)
                if k not in qtys:
                    qtys[k]=0
                qtys[k]+=line.qty_planned
                sup_refs.setdefault(supplier_id,[]).append(obj.number)
        if not suppliers:
            raise Exception("No purchase orders to create")
        po_ids = []
        for supplier_id, qtys in suppliers.items():
            refs=list(set(sup_refs[supplier_id]))
            purch_vals = {
                "contact_id": supplier_id,
                "ref": ", ".join(refs),
                "related_id": "production.order,%s"%ids[0], # XXX
                "lines": [],
                "company_id": obj.company_id.id,
            }
            for (prod_id,sale_uom_id),sale_qty in qtys.items(): # XXX: line order
                prod = get_model("product").browse(prod_id)
                if prod.purchase_uom_id and sale_uom_id==prod.sale_uom_id.id:
                    purch_uom_id=prod.purchase_uom_id.id
                    purch_qty=sale_qty*(prod.sale_to_stock_uom_factor or 1)/(prod.purchase_to_stock_uom_factor or 1)
                else:
                    purch_uom_id=sale_uom_id
                    purch_qty=sale_qty
                loc_id=prod.locations[0].location_id.id if prod.locations else None
                line_vals = {
                    "product_id": prod_id,
                    "description": prod.description or "/",
                    "qty": purch_qty,
                    "uom_id": purch_uom_id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "location_id": loc_id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            po_ids.append(po_id)
        return {
            "next": {
                "name": "purchase",
            },
            "flash": "%s purchase orders created successfully."%len(po_ids),
            "purchase_ids": po_ids,
        }

    def to_draft(self, ids, context={}):
        obj = self.browse(ids)[0]
        if obj.pickings:
            raise Exception("There are still stock movements for production order %s"%obj.number)
        obj.write({"state": "draft"})

    def get_overdue(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.due_date:
                vals[obj.id] = obj.due_date < time.strftime(
                    "%Y-%m-%d") and obj.state in ("draft", "waiting_confirm", "waiting_suborder", "waiting_material", "ready", "in_progress")
            else:
                vals[obj.id] = False
        return vals

    def search_overdue(self, clause, context={}):
        return [["due_date", "<", time.strftime("%Y-%m-%d")], ["state", "in", ["draft", "waiting", "ready"]]]

    def create_backflush_moves(self, ids, date=None, context={}):
        print("create_backflush_moves", ids)
        for obj in self.browse(ids):
            lines = []
            for comp in obj.components:
                if comp.issue_method != "backflush":
                    continue
                qty=comp.qty_planned*obj.qty_received/obj.qty_planned
                if qty > 0:
                    line_vals = {
                        "product_id": comp.product_id.id,
                        "qty": qty,
                        "uom_id": comp.uom_id.id,
                        "location_from_id": comp.location_id.id,
                        "location_to_id": obj.production_location_id.id,
                    }
                    lines.append(("create", line_vals))
                elif qty < 0:
                    line_vals = {
                        "product_id": comp.product_id.id,
                        "qty": -qty,
                        "uom_id": comp.uom_id.id,
                        "location_from_id": obj.production_location_id.id,
                        "location_to_id": comp.location_id.id,
                    }
                    lines.append(("create", line_vals))
            settings = get_model("settings").browse(1)
            if lines:
                pick_vals = {
                    "type": "internal",
                    "ref": obj.number+" RM BACKFLUSH",
                    "journal_id": settings.pick_internal_journal_id.id,
                    "related_id": "production.order,%s" % obj.id,
                    "lines": lines,
                }
                if date:
                    pick_vals["date"]=date+" 00:00:00"
                pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "internal"})
                #get_model("stock.picking").assign_lots([pick_id]) # XXX: check line split!
                #get_model("stock.picking").delete_missing_lot_lines([pick_id]) # XXX
                get_model("stock.picking").set_done([pick_id])

    def create_fg_moves(self, ids, date=None, context={}):
        obj=self.browse(ids[0])
        settings=get_model("settings").browse(1)
        if not settings.mfg_order_create_fg:
            return
        pick_vals = {
            "type": "internal",
            "ref": obj.number+" FG",
            "related_id": "production.order,%s" % obj.id,
            "lines": [],
        }
        if date:
            pick_vals["date"]=date+" 00:00:00"
        lot_id=None
        prod=obj.product_id
        categ=prod.categ_id
        if categ and categ.lot_sequence_id:
            lot_seq=categ.lot_sequence_id
            while True:
                num = get_model("sequence").get_next_number(lot_seq.id)
                res=get_model("stock.lot").search([["number","=",num]])
                if not res:
                    break
                get_model("sequence").increment_number(lot_seq.id)
            vals={
                "number": num,
                "product_id": prod.id,
            }
            lot_id=get_model("stock.lot").create(vals)
        prod=obj.product_id
        qty_remain = obj.qty_planned - obj.qty_received
        if qty_remain>0:
            line_vals = {
                "product_id": prod.id,
                "lot_id": lot_id,
                "qty": qty_remain,
                "uom_id": obj.uom_id.id,
                "location_from_id": obj.production_location_id.id,
                "location_to_id": obj.location_id.id,
                "cost_price": prod.cost_price or 0,
                "cost_amount": (prod.cost_price or 0)*obj.qty_planned,
            }
            pick_vals["lines"].append(("create", line_vals))
        if pick_vals["lines"]:
            pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "internal"})
            pick=get_model("stock.picking").browse(pick_id)
            pick.set_done(context={"no_check_stock":True})

    def create_planned_moves(self, ids, context={}):
        print("create_planned_moves", ids)
        obj=self.browse(ids[0])
        pick_out_id=obj.copy_to_pick_out(date=obj.due_date).get("pick_id")
        if pick_out_id:
            get_model("stock.picking").pending([pick_out_id])
        pick_in_id=obj.copy_to_pick_in(date=obj.order_date).get("pick_id")
        if pick_in_id:
            get_model("stock.picking").pending([pick_in_id])

    def create_planned_purchase(self, ids, context={}):
        print("create_planned_purchase", ids)
        suppliers = {}
        sup_refs={}
        for obj in self.browse(ids):
            if obj.state=="voided":
                continue
            for line in obj.components:
                if line.issue_method!="purchase":
                    continue
                prod = line.product_id
                if not prod:
                    continue
                if not prod.suppliers:
                    raise Exception("Missing supplier for product '%s'" % prod.name)
                supplier_id = prod.suppliers[0].supplier_id.id
                qtys=suppliers.setdefault(supplier_id,{})
                k=(prod.id,line.uom_id.id)
                if k not in qtys:
                    qtys[k]=0
                qtys[k]+=line.qty_planned
                sup_refs.setdefault(supplier_id,[]).append(obj.number)
        if not suppliers:
            return
        po_ids = []
        for supplier_id, qtys in suppliers.items():
            refs=list(set(sup_refs[supplier_id]))
            purch_vals = {
                "contact_id": supplier_id,
                "ref": ", ".join(refs),
                "related_id": "production.order,%s"%ids[0], # XXX
                "lines": [],
                "company_id": obj.company_id.id,
            }
            for (prod_id,sale_uom_id),sale_qty in qtys.items(): # XXX: line order
                prod = get_model("product").browse(prod_id)
                if prod.purchase_uom_id and sale_uom_id==prod.sale_uom_id.id:
                    purch_uom_id=prod.purchase_uom_id.id
                    purch_qty=sale_qty*(prod.sale_to_stock_uom_factor or 1)/(prod.purchase_to_stock_uom_factor or 1)
                else:
                    purch_uom_id=sale_uom_id
                    purch_qty=sale_qty
                loc_id=prod.locations[0].location_id.id if prod.locations else None
                line_vals = {
                    "product_id": prod_id,
                    "description": prod.description or "/",
                    "qty": purch_qty,
                    "uom_id": purch_uom_id,
                    "unit_price": prod.purchase_price or 0,
                    "tax_id": prod.purchase_tax_id.id,
                    "location_id": loc_id,
                }
                purch_vals["lines"].append(("create", line_vals))
            po_id = get_model("purchase.order").create(purch_vals)
            po_ids.append(po_id)
        return {
            "next": {
                "name": "purchase",
            },
            "flash": "%s purchase orders created successfully."%len(po_ids),
            "purchase_ids": po_ids,
        }

    def delete_planned_moves(self, ids, context={}):
        obj=self.browse(ids[0])
        for pick in obj.pickings:
            if pick.state in ("pending","approved"):
                pick.delete()

    def clear_wip_moves(self, ids, context={}):
        print("clear_wip_moves", ids)
        obj = self.browse(ids[0])
        #if obj.production_location_id.type!="internal":
        #    raise Exception("Invalid production location type for order %s"%obj.number)
        int_loc_id=obj.production_location_id.id
        if obj.bom_id and obj.bom_id.virt_production_location_id:
            prod_loc_id = obj.bom_id.virt_production_location_id.id
        else:
            res = get_model("stock.location").search([["type", "=", "production"]])
            if not res:
                raise Exception("Location of type 'production' not found")
            prod_loc_id = res[0]
        settings = get_model("settings").browse(1)
        in_moves=[]
        out_moves=[]
        for move in obj.stock_moves:
            if move.state!="done":
                continue
            if move.location_to_id.id==int_loc_id and move.location_from_id.id!=int_loc_id:
                in_moves.append(move)
            if move.location_from_id.id==int_loc_id and move.location_to_id.id!=int_loc_id:
                out_moves.append(move)
        if in_moves:
            vals = {
                "type": "out",
                "related_id": "production.order,%s" % obj.id,
                "ref": obj.number+" CLEAR RM",
                "journal_id": settings.pick_out_journal_id.id,
                "date": obj.order_date+" 00:00:00",
                "lines": [],
            }
            for move in in_moves:
                vals["lines"].append(("create",{
                    "product_id": move.product_id.id,
                    "lot_id": move.lot_id.id,
                    "qty": move.qty,
                    "uom_id": move.uom_id.id,
                    "location_from_id": int_loc_id,
                    "location_to_id": prod_loc_id,
                    "related_id": "production.order,%s" % obj.id,
                }))
            pick_id = get_model("stock.picking").create(vals, context={"pick_type": "out"})
            get_model("stock.picking").set_done([pick_id])
        if out_moves:
            vals = {
                "type": "in",
                "related_id": "production.order,%s" % obj.id,
                "ref": obj.number+" CLEAR FG",
                "journal_id": settings.pick_in_journal_id.id,
                "date": obj.order_date+" 00:00:00",
                "lines": [],
            }
            for move in out_moves:
                cost_price=move.product_id.cost_price or 0
                vals["lines"].append(("create",{
                    "product_id": move.product_id.id,
                    "lot_id": move.lot_id.id,
                    "qty": move.qty,
                    "uom_id": move.uom_id.id,
                    "location_from_id": prod_loc_id,
                    "location_to_id": int_loc_id,
                    "related_id": "production.order,%s" % obj.id,
                    "cost_price": cost_price,
                    "cost_amount": cost_price*move.qty,
                }))
            pick_id = get_model("stock.picking").create(vals, context={"pick_type": "in"})
            get_model("stock.picking").set_done([pick_id])

    def get_pickings(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            pick_ids = []
            for move in obj.stock_moves:
                pick_id = move.picking_id.id
                if pick_id not in pick_ids:
                    pick_ids.append(pick_id)
            vals[obj.id] = pick_ids
        return vals

    def get_track_entries(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if not obj.track_id:
                vals[obj.id]=[]
                continue
            res=get_model("account.track.entry").search([["track_id","child_of",obj.track_id.id]])
            vals[obj.id]=res
        return vals

    def get_total_cost_old(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total_amt=0
            for cost in obj.track_entries:
                total_amt-=cost.amount
            vals[obj.id]={
                "total_cost": total_amt,
                "unit_cost": total_amt/obj.qty_received if obj.qty_received else None,
            }
        return vals

    def get_total_cost(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total_rm_cost=0
            for comp in obj.components:
                total_rm_cost+=comp.cost_amount or 0
            total_cost=total_rm_cost
            vals[obj.id]={
                "total_rm_cost": total_rm_cost,
                "total_cost": total_cost,
                "unit_cost": total_cost/obj.qty_received if obj.qty_received else None,
            }
        return vals

    def get_last_order_qty(self,product_id,context={}):
        res=self.search([["product_id","=",product_id]],order="order_date desc",limit=1)
        if not res:
            return None
        obj_id=res[0]
        obj=self.browse(obj_id)
        return obj.qty_planned

    def copy_to_cust_invoice_labor(self, ids, context={}):
        print("mo.copy_to_cust_invoice_labor",ids)
        obj=self.browse(ids[0])
        if not obj.customer_id:
            raise Exception("Missing customer in production order")
        inv_vals = {
            "type": "out",
            "inv_type": "invoice",
            "contact_id": obj.customer_id.id,
            "lines": [],
            "company_id": obj.company_id.id,
            "ref": obj.number,
            "related_id": "production.order,%s"%obj.id,
        }
        if not obj.bom_id:
            raise Exception("Missing BoM")
        labor_costs={}
        for line in obj.bom_id.lines:
            labor_costs[line.product_id.id]=line.labor_amount
        for purch in obj.purchase_orders:
            for line in purch.lines:
                if not line.qty_received:
                    continue
                prod = line.product_id
                price=labor_costs.get(prod.id)
                if price is None:
                    raise Exception("Missing labor cost for product '%s'"%prod.name)
                line_vals = {
                    "product_id": prod.id,
                    "description": prod.description or "/",
                    "qty": line.qty_received,
                    "uom_id": line.uom_id.id,
                    "unit_price": price,
                    "account_id": prod.sale_account_id.id,
                    "tax_id": prod.sale_tax_id.id,
                }
                line_vals["amount"]=line_vals["qty"]*line_vals["unit_price"]
                inv_vals["lines"].append(("create",line_vals))
        if not inv_vals["lines"]:
            raise Exception("Nothing to invoice")
        inv_id = get_model("account.invoice").create(inv_vals, {"type": "out", "inv_type": "invoice"})
        inv=get_model("account.invoice").browse(inv_id)
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv_id,
            },
            "flash": "Invoice %s created from production order" % inv.number,
            "invoice_id": inv_id,
        }

    def receive_fg_confirm(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.receive_fg_qty:
            raise Exception("Missing received qty")
        access.set_active_company(obj.company_id.id)
        obj.copy_to_pick_in(qty_received=obj.receive_fg_qty,set_done=True,qty_received_gb=obj.receive_fg_qty_gb,qty_received_waste=obj.receive_fg_qty_waste)
        if obj.receive_fg_done:
            obj.done()

    def adjust_rm_confirm(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.adjust_rm_product_id:
            raise Exception("Missing RM product")
        if not obj.adjust_rm_qty:
            raise Exception("Missing issued qty")
        found_comp=None
        for comp in obj.components:
            if comp.product_id.id==obj.adjust_rm_product_id.id:
                found_comp=comp
                break
        if not found_comp:
            raise Exception("Component not found for product %s"%obj.adjust_rm_product_id.name)
        qty_diff=obj.adjust_rm_qty-found_comp.qty_issued
        if not qty_diff:
            raise Exception("Nothing to adjust")
        access.set_active_company(obj.company_id.id)
        res=obj.copy_to_pick_out(rm_product_id=obj.adjust_rm_product_id.id,rm_qty=qty_diff)
        pick_id=res["pick_id"]
        get_model("stock.picking").set_done([pick_id])
        return {
            "flash": "Issued qty adjusted successfully.",
        }

    def copy_to_transform(self,ids,context={}):
        vals={
            "lines": [],
        }
        for obj in self.browse(ids):
            line_vals={
                "type": "in",
                "product_id": obj.product_id.id,
                "lot_id": obj.lot_id.id,
                "qty": obj.qty_received,
                "uom_id": obj.uom_id.id,
                "location_id": obj.location_id.id,
            }
            vals["lines"].append(("create",line_vals))
        trans_id=get_model("stock.transform").create(vals)
        return {
            "next": {
                "name": "transform",
                "mode": "form",
                "active_id": trans_id,
            }
        }

    def copy_to_grading(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.components:
            raise Exception("Missing components")
        comp=obj.components[0]
        loc=comp.location_id
        vals={
            "location_id": loc.id,
            "ref": obj.number,
            "lines": [],
        }
        prod=comp.product_id
        if not comp.qty_issued:
            raise Exception("No qty issued for product %s"%prod.name)
        qty_grade=comp.qty_planned-comp.qty_issued
        if qty_grade<=0:
            raise Exception("No qty remaining for product %s"%prod.name)
        line_vals={
            "product_id": prod.id,
            "qty": qty_grade,
            "uom_id": comp.uom_id.id,
            "product_gb_id": prod.product_gb_id.id,
            "production_id": obj.id,
        }
        vals["lines"].append(("create",line_vals))
        grade_id=get_model("stock.grade").create(vals)
        return {
            "next": {
                "name": "grade",
                "mode": "form",
                "active_id": grade_id,
            }
        }

    def qc_check(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"qc_checked":True})

    def update_stock_dates(self,ids,context={}):
        for obj in self.browse(ids):
            date=obj.due_date+" 00:00:00"
            for pick in obj.pickings:
                pick.write({"date":date})
                for line in pick.lines:
                    line.write({"date":date})

    def get_received_date(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            min_date=None
            for pick in obj.pickings:
                if not min_date or pick.date<min_date:
                    min_date=pick.date
            vals[obj.id]=min_date[:10] if min_date else None
        return vals

ProductionOrder.register()
