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


class Component(Model):
    _name = "production.component"
    _string = "Production Component"
    _fields = {
        "order_id": fields.Many2One("production.order", "Production Order", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "RM Product", required=True),
        "qty_planned": fields.Decimal("Planned Qty", required=True, scale=6),
        "qty_issued": fields.Decimal("Issued Qty", function="get_qty_issued", scale=6),
        "qty_received": fields.Decimal("Received Qty", function="get_qty_received", scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "RM Warehouse", required=True),
        "issue_method": fields.Selection([["manual", "Manual"], ["backflush", "Backflush"], ["purchase","Purchase"]], "Issue Method", required=True),
        #"stock_moves": fields.One2Many("stock.move","component_id","Stock Moves"),
        "lot_id": fields.Many2One("stock.lot", "RM Lot"),
        "container_id": fields.Many2One("stock.container", "RM Container"),
        "qty_stock": fields.Decimal("Qty In Stock", function="get_qty_stock", scale=6),
        "notes": fields.Text("Notes"),
        "cost_price": fields.Decimal("Cost Price",function="get_cost",function_multi=True,scale=6),
        "cost_amount": fields.Decimal("Cost Amount",function="get_cost",function_multi=True),
    }
    _defaults = {
        "issue_method": "manual",
    }

    def get_qty_received(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.order_id
            total_qty = 0
            for pick in order.pickings:
                for move in pick.lines:
                    if move.product_id.id != obj.product_id.id or move.state != "done":
                        continue
                    qty = get_model("uom").convert(move.qty, move.uom_id.id, obj.uom_id.id)
                    if move.location_from_id.id == obj.location_id.id and move.location_to_id.id != obj.location_id.id:
                        total_qty -= qty
                    elif move.location_from_id.id != obj.location_id.id and move.location_to_id.id == obj.location_id.id:
                        total_qty += qty
            vals[obj.id] = total_qty
        return vals

    def get_qty_issued(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.order_id
            total_qty = 0
            for pick in order.pickings:
                for move in pick.lines:
                    if move.product_id.id != obj.product_id.id or move.state != "done":
                        continue
                    qty = get_model("uom").convert(move.qty, move.uom_id.id, obj.uom_id.id)
                    if move.location_from_id.id == obj.location_id.id and move.location_to_id.id != obj.location_id.id:
                        if obj.container_id and obj.lot_id and \
                                (not move.container_from_id or not move.lot_id or obj.container_id.id != move.container_from_id.id or obj.lot_id.id != move.lot_id.id):
                            continue
                        if obj.container_id and (not move.container_from_id or obj.container_id.id != move.container_from_id.id):
                            continue
                        if obj.lot_id and (not move.lot_id or obj.lot_id.id != move.lot_id.id):
                            continue
                        total_qty += qty
                    elif move.location_from_id.id != obj.location_id.id and move.location_to_id.id == obj.location_id.id:
                        if obj.container_id and obj.lot_id and \
                                (not move.container_to_id or not move.lot_id or obj.container_id.id != move.container_to_id.id or obj.lot_id.id != move.lot_id.id):
                            continue
                        if obj.container_id and (not move.container_to_id or obj.container_id.id != move.container_to_id.id):
                            continue
                        if obj.lot_id and (not move.lot_id or obj.lot_id.id != move.lot_id.id):
                            continue
                        total_qty -= qty
            vals[obj.id] = total_qty
        return vals

    def copy_to_pick_out(self, ids, context={}):
        prod_loc_id = get_model("stock.location").search([["type", "=", "production"]])[0]
        refs = set()
        lines = []
        for obj in self.browse(ids):
            qty_remain = obj.qty_planned - obj.qty_issued
            line_vals = {
                "product_id": obj.product_id.id,
                "qty": qty_remain,
                "uom_id": obj.uom_id.id,
                "location_from_id": obj.location_id.id,
                "location_to_id": prod_loc_id,
                "component_id": obj.id,
            }
            lines.append(("create", line_vals))
            refs.add(obj.order_id.number)
        settings = get_model("settings").browse(1)
        pick_vals = {
            "type": "out",
            "ref": " ".join(sorted(refs)),
            "journal_id": settings.pick_out_journal_id.id,
            "lines": lines,
        }
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "out"})
        return {
            "name": "pick_out_edit",
            "active_id": pick_id,
        }

    def get_qty_stock(self, ids, context={}):
        keys = []
        for obj in self.browse(ids):
            if not obj.location_id:
                continue
            key = (obj.product_id.id, obj.lot_id.id, obj.location_id.id, obj.container_id.id)
            keys.append(key)
        bals = get_model("stock.balance").compute_key_balances(keys)
        vals = {}
        for obj in self.browse(ids):
            loc_id = obj.location_id.id
            if loc_id:
                key = (obj.product_id.id, obj.lot_id.id, obj.location_id.id, obj.container_id.id)
                qty = bals[key][0]
            else:
                qty = None
            vals[obj.id] = qty
        return vals

    def get_cost_old(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod=obj.product_id
            cost_price=prod.cost_price or 0
            vals[obj.id]={
                "cost_price": cost_price,
                "cost_amount": cost_price*obj.qty_issued,
            }
        return vals

    def get_cost(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.order_id
            total_qty = 0
            total_cost=0
            for pick in order.pickings:
                for move in pick.lines:
                    if move.product_id.id != obj.product_id.id or move.state != "done":
                        continue
                    qty = get_model("uom").convert(move.qty, move.uom_id.id, obj.uom_id.id)
                    cost=move.cost_amount or 0
                    if move.location_from_id.id == obj.location_id.id and move.location_to_id.id != obj.location_id.id:
                        if obj.lot_id and (not move.lot_id or obj.lot_id.id != move.lot_id.id):
                            continue
                        total_qty += qty
                        total_cost+=cost
                    elif move.location_from_id.id != obj.location_id.id and move.location_to_id.id == obj.location_id.id:
                        if obj.lot_id and (not move.lot_id or obj.lot_id.id != move.lot_id.id):
                            continue
                        total_qty -= qty
                        total_cost-=cost
            vals[obj.id] = {
                "cost_amount": total_cost,
                "cost_price": total_cost/total_qty if total_qty else None,
            }
        return vals

Component.register()
