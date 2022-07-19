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
from netforce import access
from decimal import Decimal
import math

class SaleOrderLine(Model):
    _name = "sale.order.line"
    _name_field = "order_id"
    _fields = {
        "order_id": fields.Many2One("sale.order", "Sales Order", required=True, on_delete="cascade", search=True),
        "product_id": fields.Many2One("product", "Product", search=True),
        "description": fields.Text("Description", required=True, search=True),
        "qty": fields.Decimal("Qty"),
        "uom_id": fields.Many2One("uom", "UoM"),
        "uom2_id": fields.Many2One("uom", "UoM2"),
        "unit_price": fields.Decimal("Unit Price", search=True, scale=6),
        "tax_id": fields.Many2One("account.tax.rate", "Tax Rate"),
        "amount": fields.Decimal("Amount", function="get_amount", function_multi=True, store=True, function_order=1, search=True),
        "amount_cur": fields.Decimal("Amount", function="get_amount", function_multi=True, store=True, function_order=1, search=True),
        "qty_stock": fields.Decimal("Qty (Stock UoM)"),
        "qty_delivered": fields.Decimal("Shipped Qty", function="get_qty_delivered"),
        "qty_invoiced": fields.Decimal("Invoiced Qty", function="get_qty_invoiced"),
        "qty_produced": fields.Decimal("Produced Qty", function="get_qty_produced"),
        "contact_id": fields.Many2One("contact", "Contact", function="_get_related", function_search="_search_related", function_context={"path": "order_id.contact_id"}, search=True),
        "date": fields.Date("Date", function="_get_related", function_search="_search_related", function_context={"path": "order_id.date"}, search=True),
        "user_id": fields.Many2One("base.user", "Owner", function="_get_related", function_search="_search_related", function_context={"path": "order_id.user_id"}, search=True),
        "amount_discount": fields.Decimal("Discount Amount", function="get_amount", function_multi=True),
        "state": fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed"), ("done", "Completed"), ("voided", "Voided")], "Status", function="_get_related", function_search="_search_related", function_context={"path": "order_id.state"}, search=True),
        "qty2": fields.Decimal("Qty2"),
        "location_id": fields.Many2One("stock.location", "Warehouse Location", condition=[["type", "=", "internal"]]),
        "reserve_location_id": fields.Many2One("stock.location", "Reservation Location", condition=[["type", "=", "internal"]]),
        "product_categs": fields.Many2Many("product.categ", "Product Categories", function="_get_related", function_context={"path": "product_id.categs"}, function_search="_search_related", search=True),
        "product_categ_id": fields.Many2One("product.categ", "Product Category", function="_get_related", function_context={"path": "product_id.categ_id"}, function_search="_search_related", search=True),
        "discount": fields.Decimal("Disc %"),  # XXX: rename to discount_percent later
        "discount_amount": fields.Decimal("Disc Amt"),
        "qty_avail": fields.Decimal("Qty In Stock", function="get_qty_avail"),
        "agg_amount": fields.Decimal("Total Amount", agg_function=["sum", "amount"]),
        "agg_qty": fields.Decimal("Total Order Qty", agg_function=["sum", "qty"]),
        "remark": fields.Char("Remark"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),
        "sequence": fields.Char("Item No.",function="get_sequence_old"), # XXX: deprecated
        "sequence_no": fields.Integer("Item No."),
        "index": fields.Integer("Index",function="get_index"),
        "due_date": fields.Date("Due Date"),
        "est_cost_amount": fields.Float("Est. Cost Amount",function="get_est_profit",function_multi=True), # XXX: deprecated
        "est_profit_amount": fields.Float("Est. Profit Amount",function="get_est_profit",function_multi=True),
        "est_margin_percent": fields.Float("Est. Margin %",function="get_est_profit",function_multi=True),
        "act_cost_amount": fields.Float("Act. Cost Amount",function="get_act_profit",function_multi=True),
        "act_profit_amount": fields.Float("Act. Profit Amount",function="get_act_profit",function_multi=True,store=True),
        "act_margin_percent": fields.Float("Act. Margin %",function="get_act_profit",function_multi=True),
        "promotion_amount": fields.Decimal("Prom Amt",function="get_amount",function_multi=True),
        "agg_act_profit": fields.Decimal("Total Actual Profit", agg_function=["sum", "act_profit_amount"]),
        "production_id": fields.Many2One("production.order","Production Order"),
        "lot_id": fields.Many2One("stock.lot","Lot / Serial Number"),
        "ship_address_id": fields.Many2One("address", "Shipping Address"),
        "packaging_id": fields.Many2One("stock.packaging", "Packaging"),
        "delivery_slot_id": fields.Many2One("delivery.slot","Delivery Slot"),
        "ship_tracking": fields.Char("Tracking Numbers", function="get_ship_tracking"),
        "addons": fields.Many2Many("product.addon","Addons"),
        "supplier_id": fields.Many2One("contact","Supplier",condition=[["supplier","=",True]]),
        "track_id": fields.Many2One("account.track.categ", "Track-1", condition=[["type", "=", "1"]]), #2020-11-02 Chin
        "track2_id": fields.Many2One("account.track.categ", "Track-2", condition=[["type", "=", "2"]]), #2020-11-02 Chin
        "cost_price": fields.Decimal("Cost Price"),
        "cost_amount": fields.Decimal("Cost Amount",function="get_profit",function_multi=True),
        "profit_amount": fields.Decimal("Profit Amount",function="get_profit",function_multi=True),
        "margin_percent": fields.Decimal("Margin %",function="get_profit",function_multi=True),
        "type": fields.Selection([["item","Item"],["group","Group"]],"Line Type"),
        "notes": fields.Text("Notes"),
        "amount_tax": fields.Decimal("Tax Amount",function="get_tax_amount",function_multi=True),
        "amount_incl_tax": fields.Decimal("Amount Including Tax",function="get_tax_amount",function_multi=True),
        "amount_excl_tax": fields.Decimal("Amount Excluding Tax",function="get_tax_amount",function_multi=True),
    }
    _order="sequence_no,id"

    def get_sequence_old(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=str(obj.sequence_no)
        return vals

    def create(self, vals, context={}):
        id = super(SaleOrderLine, self).create(vals, context)
        self.function_store([id])
        return id

    def write(self, ids, vals, context={}):
        super(SaleOrderLine, self).write(ids, vals, context)
        self.function_store(ids)

    def get_amount(self, ids, context={}):
        vals = {}
        settings = get_model("settings").browse(1)
        sale_ids=[]
        for line in self.browse(ids):
            sale_ids.append(line.order_id.id)
        sale_ids=list(set(sale_ids))
        for sale in get_model("sale.order").browse(sale_ids):
            prod_qtys={}
            prom_amts={}
            prom_pcts={}
            for line in sale.lines:
                prod_qtys.setdefault(line.product_id.id,0)
                prod_qtys[line.product_id.id]+=line.qty or 0
            for line in sale.used_promotions:
                if line.amount and line.product_id:
                    prom_amts.setdefault(line.product_id.id,0)
                    prom_amts[line.product_id.id]+=line.amount
                elif line.percent:
                    prom_pcts.setdefault(line.product_id.id,0)
                    prom_pcts[line.product_id.id]+=line.percent
            for line in sale.lines:
                amt=None
                amount_cur=None
                disc=None
                prom_amt=None
                if line.qty and line.unit_price:
                    amt = (line.qty or 0) * (line.unit_price or 0)
                    if line.discount:
                        disc = amt * line.discount / 100
                    else:
                        disc = 0
                    if line.discount_amount:
                        disc += line.discount_amount
                    amt-=disc
                    amt_before_prom=amt
                    prom_amt=prom_amts.get(line.product_id.id,Decimal(0))/prod_qtys[line.product_id.id]*line.qty if line.qty else 0
                    prom_pct=prom_pcts.get(line.product_id.id,Decimal(0))+prom_pcts.get(None,0)
                    if prom_pct:
                        prom_amt+=math.ceil(amt_before_prom/line.qty*prom_pct/100)*line.qty if line.qty else 0
                    if prom_amt:
                        amt-=prom_amt
                    order = line.order_id
                    amount_cur=get_model("currency").convert(amt, order.currency_id.id, settings.currency_id.id),
                vals[line.id] = {
                    "amount": amt,
                    "amount_cur": amount_cur,
                    "amount_discount": disc,
                    "promotion_amount": prom_amt,
                }
        return vals

    def get_qty_delivered(self, ids, context={}):
        order_ids = []
        for obj in self.browse(ids):
            order_ids.append(obj.order_id.id)
        order_ids = list(set(order_ids))
        vals = {}
        for order in get_model("sale.order").browse(order_ids):
            delivered_qtys = {}
            for move in order.stock_moves:
                if move.state != "done":
                    continue
                if move.expand_picking_id:
                    continue
                prod_id = move.product_id.id
                k = (prod_id, move.location_from_id.id)
                delivered_qtys.setdefault(k,0)
                delivered_qtys[k] += move.qty  # XXX: uom
                k = (prod_id, move.location_to_id.id)
                delivered_qtys.setdefault(k,0)
                delivered_qtys[k] -= move.qty  # XXX: uom
            for line in order.lines:
                k = (line.product_id.id, line.reserve_location_id.id or line.location_id.id)
                delivered_qty = delivered_qtys.get(k) or 0  # XXX: uom
                used_qty = min(line.qty or 0, delivered_qty)
                vals[line.id] = used_qty
                if k in delivered_qtys:
                    delivered_qtys[k] -= used_qty
            for line in reversed(order.lines):
                k = (line.product_id.id, line.reserve_location_id.id or line.location_id.id)
                remain_qty = delivered_qtys.get(k) or 0  # XXX: uom
                if remain_qty:
                    vals[line.id] += remain_qty
                    delivered_qtys[k] -= remain_qty
        for id,qty in vals.items():
            vals[id]=max(qty,0)
        vals = {x: vals[x] for x in ids}
        return vals

    def get_qty_produced(self, ids, context={}):
        sale_ids=[]
        for obj in self.browse(ids):
            sale_ids.append(obj.order_id.id)
        sale_ids=list(set(sale_ids))
        qtys={}
        for sale in get_model("sale.order").browse(sale_ids):
            for order in sale.production_orders:
                k = (sale.id,order.product_id.id)
                qtys.setdefault(k,0)
                qtys[k]+=order.qty_received
        vals={}
        for obj in self.browse(ids):
            k = (obj.order_id.id,obj.product_id.id)
            qty=qtys.get(k,0)
            vals[obj.id]=qty
        return vals

    def get_qty_invoiced(self, ids, context={}):
        order_ids = []
        for obj in self.browse(ids):
            order_ids.append(obj.order_id.id)
        order_ids = list(set(order_ids))
        vals = {}
        for order in get_model("sale.order").browse(order_ids):
            inv_qtys = {}
            for inv in order.invoices:
                if inv.state not in ("draft","waiting_payment","paid"):
                    continue
                for line in inv.lines:
                    prod_id = line.product_id.id
                    inv_qtys.setdefault(prod_id, 0)
                    inv_qtys[prod_id] += line.qty
            for line in order.lines:
                if line.id not in ids:
                    continue
                prod_id = line.product_id.id
                inv_qty = inv_qtys.get(prod_id, 0)  # XXX: uom
                used_qty = min(line.qty, inv_qty)
                vals[line.id] = used_qty
                if prod_id in inv_qtys:
                    inv_qtys[prod_id] -= used_qty
            for line in reversed(order.lines):
                prod_id = line.product_id.id
                remain_qty = inv_qtys.get(prod_id, 0)  # XXX: uom
                if remain_qty:
                    vals[line.id] += remain_qty
                    inv_qtys[prod_id] -= remain_qty
        vals = {x: vals[x] for x in ids}
        return vals

    def get_qty_avail(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            prod_id = obj.product_id.id
            loc_id = obj.location_id.id
            if prod_id and loc_id:
                res = get_model("stock.location").compute_balance([loc_id], prod_id)
                qty = res["bal_qty"]
            else:
                qty = None
            vals[obj.id] = qty
        return vals

    def get_est_profit(self,ids,context={}):
        sale_ids=[]
        for line in self.browse(ids):
            sale_ids.append(line.order_id.id)
        sale_ids=list(set(sale_ids))
        item_costs={}
        for sale in get_model("sale.order").browse(sale_ids):
            for cost in sale.est_costs:
                k=(sale.id,cost.sequence)
                if k not in item_costs:
                    item_costs[k]=0
                amt=cost.amount or 0
                if cost.currency_id:
                    rate=sale.get_relative_currency_rate(cost.currency_id.id)
                    amt=amt*rate
                item_costs[k]+=amt
        vals={}
        for line in self.browse(ids):
            k=(line.order_id.id,line.sequence)
            cost=item_costs.get(k,0)
            profit=line.amount-cost
            margin=profit*100/line.amount if line.amount else None
            vals[line.id]={
                "est_cost_amount": cost,
                "est_profit_amount": profit,
                "est_margin_percent": margin,
            }
        return vals

    def get_act_profit(self,ids,context={}):
        sale_ids=[]
        for line in self.browse(ids):
            sale_ids.append(line.order_id.id)
        sale_ids=list(set(sale_ids))
        item_costs={}
        for sale in get_model("sale.order").browse(sale_ids):
            for line in sale.track_entries:
                k=(sale.id,line.track_id.code)
                if k not in item_costs:
                    item_costs[k]=0
                # TODO: convert currency
                item_costs[k]-=line.amount
        vals={}
        for line in self.browse(ids):
            track_code="%s / %s"%(line.order_id.number,line.sequence)
            k=(line.order_id.id,track_code)
            cost=item_costs.get(k) or 0
            profit=(line.amount or 0)-cost
            margin=profit*100/line.amount if line.amount else None
            vals[line.id]={
                "act_cost_amount": cost,
                "act_profit_amount": profit,
                "act_margin_percent": margin,
            }
        return vals

    def get_ship_tracking(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            track_nos = []
            if obj.due_date:
                for pick in obj.order_id.pickings:
                    if pick.date[:10]==obj.due_date and pick.ship_tracking:
                        track_nos.append(pick.ship_tracking)
            vals[obj.id] = ", ".join(track_nos)
        return vals

    def get_profit(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.cost_price is not None:
                cost=obj.cost_price*(obj.qty or 0)
                profit=(obj.amount or 0)-cost
                margin=profit*100/obj.amount if obj.amount else None
            else:
                cost=None
                profit=None
                margin=None
            vals[obj.id]={
                "cost_amount": cost,
                "profit_amount": profit,
                "margin_percent": margin,
            }
        return vals

    def get_index(self,ids,context={}):
        order_ids=[]
        for obj in self.browse(ids):
            order_ids.append(obj.order_id.id)
        order_ids=list(set(order_ids))
        vals={}
        for order in get_model("sale.order").browse(order_ids):
            i=1
            for line in order.lines:
                if line.id in ids:
                    vals[line.id]=i
                i+=1
        return vals

    #def get_filter(self,access_type,context={}):
    #    company_id=access.get_active_company()
    #    if not company_id:
    #        return True
    #    return [["order_id.company_id","child_of",company_id]]

    def view_sale(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": obj.order_id.id,
            }
        }

    def get_tax_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt_tax=0
            amt_incl=0
            amt_excl=0
            tax_id = obj.tax_id.id
            sale=obj.order_id
            if tax_id and sale.tax_type != "no_tax" and obj.tax_id.rate:
                base_amt = get_model("account.tax.rate").compute_base(tax_id, obj.amount or 0, tax_type=sale.tax_type)
                tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                for comp_id, tax_amt in tax_comps.items():
                    amt_tax += tax_amt
            if sale.tax_type=="tax_ex":
                amt_excl=obj.amount or 0
                amt_incl=amt_excl+amt_tax
            elif sale.tax_type=="tax_in":
                amt_incl=obj.amount or 0
                amt_excl=amt_incl-amt_tax
            vals[obj.id]={
                "amount_tax": amt_tax,
                "amount_incl_tax": amt_incl,
                "amount_excl_tax": amt_excl,
            }
        return vals

SaleOrderLine.register()
