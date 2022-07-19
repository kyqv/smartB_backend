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
from decimal import Decimal
import math

class SaleReturnLine(Model):
    _name = "sale.return.line"
    _name_field = "order_id"
    _fields = {
        "order_id": fields.Many2One("sale.return", "Sales Return", required=True, on_delete="cascade", search=True),
        "product_id": fields.Many2One("product", "Product", search=True),
        "description": fields.Text("Description", required=True, search=True),
        "qty": fields.Decimal("Qty"),
        "uom_id": fields.Many2One("uom", "UoM"),
        "unit_price": fields.Decimal("Unit Price", required=True, search=True, scale=6),
        "tax_id": fields.Many2One("account.tax.rate", "Tax Rate"),
        "amount": fields.Decimal("Amount", function="get_amount", function_multi=True, store=True, function_order=1, search=True),
        "amount_cur": fields.Decimal("Amount", function="get_amount", function_multi=True, store=True, function_order=1, search=True),
        "qty_stock": fields.Decimal("Qty (Stock UoM)"),
        "qty_received": fields.Decimal("Received Qty", function="get_qty_received"),
        "qty_invoiced": fields.Decimal("Invoiced Qty", function="get_qty_invoiced"),
        "contact_id": fields.Many2One("contact", "Contact", function="_get_related", function_search="_search_related", function_context={"path": "order_id.contact_id"}, search=True),
        "date": fields.Date("Date", function="_get_related", function_search="_search_related", function_context={"path": "order_id.date"}, search=True),
        "user_id": fields.Many2One("base.user", "Owner", function="_get_related", function_search="_search_related", function_context={"path": "order_id.user_id"}, search=True),
        "amount_discount": fields.Decimal("Discount Amount", function="get_amount", function_multi=True),
        "state": fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed"), ("done", "Completed"), ("voided", "Voided")], "Status", function="_get_related", function_search="_search_related", function_context={"path": "order_id.state"}, search=True),
        "qty2": fields.Decimal("Secondary Qty"),
        "location_id": fields.Many2One("stock.location", "Location", condition=[["type", "=", "internal"]]),
        "product_categs": fields.Many2Many("product.categ", "Product Categories", function="_get_related", function_context={"path": "product_id.categs"}, function_search="_search_related", search=True),
        "discount": fields.Decimal("Disc %"),  # XXX: rename to discount_percent later
        "discount_amount": fields.Decimal("Disc Amt"),
        "qty_avail": fields.Decimal("Qty In Stock", function="get_qty_avail"),
        "agg_amount": fields.Decimal("Total Amount", agg_function=["sum", "amount"]),
        "agg_qty": fields.Decimal("Total Order Qty", agg_function=["sum", "qty"]),
        "remark": fields.Char("Remark"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),
        "sequence": fields.Char("Item No."),
        "return_type": fields.Selection([["refund","Refund"],["exchange","Exchange"]],"Return Type"),
        "reason_code_id": fields.Many2One("reason.code","Reason Code",condition=[["type","=","sale_return"]]),
    }

    def create(self, vals, context={}):
        id = super().create(vals, context)
        self.function_store([id])
        return id

    def write(self, ids, vals, context={}):
        super().write(ids, vals, context)
        self.function_store(ids)

    def get_amount(self, ids, context={}):
        vals = {}
        settings = get_model("settings").browse(1)
        sale_ids=[]
        for line in self.browse(ids):
            sale_ids.append(line.order_id.id)
        sale_ids=list(set(sale_ids))
        for sale in get_model("sale.return").browse(sale_ids):
            prod_qtys={}
            for line in sale.lines:
                prod_qtys.setdefault(line.product_id.id,0)
                prod_qtys[line.product_id.id]+=line.qty
            for line in sale.lines:
                amt = line.qty * line.unit_price
                if line.discount:
                    disc = amt * line.discount / 100
                else:
                    disc = 0
                if line.discount_amount:
                    disc += line.discount_amount
                amt-=disc
                order = line.order_id
                vals[line.id] = {
                    "amount": amt,
                    "amount_cur": get_model("currency").convert(amt, order.currency_id.id, settings.currency_id.id),
                    "amount_discount": disc,
                }
        return vals

    def get_qty_received(self, ids, context={}):
        order_ids = []
        for obj in self.browse(ids):
            order_ids.append(obj.order_id.id)
        order_ids = list(set(order_ids))
        vals = {}
        for order in get_model("sale.return").browse(order_ids):
            received_qtys = {}
            for move in order.stock_moves:
                if move.state != "done":
                    continue
                prod_id = move.product_id.id
                k = (prod_id, move.location_to_id.id)
                received_qtys.setdefault(k, 0)
                received_qtys[k] += move.qty  # XXX: uom
                k = (prod_id, move.location_from_id.id)
                received_qtys.setdefault(k, 0)
                received_qtys[k] -= move.qty  # XXX: uom
            for line in order.lines:
                k = (line.product_id.id, line.location_id.id)
                received_qty = received_qtys.get(k, 0)  # XXX: uom
                used_qty = min(line.qty, received_qty)
                vals[line.id] = used_qty
                if k in received_qtys:
                    received_qtys[k] -= used_qty
            for line in reversed(order.lines):
                k = (line.product_id.id, line.location_id.id)
                remain_qty = received_qtys.get(k, 0)  # XXX: uom
                if remain_qty:
                    vals[line.id] += remain_qty
                    received_qtys[k] -= remain_qty
        vals = {x: vals[x] for x in ids}
        return vals

    def get_qty_invoiced(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            order = obj.order_id
            qty = 0
            for inv in order.invoices:
                if inv.state == "voided":
                    continue
                for line in inv.lines:
                    if obj.product_id:
                        if line.product_id.id != obj.product_id.id:
                            continue
                    else:
                        if line.product_id or line.description != obj.description:
                            continue
                    if inv.type == "out":
                        qty += line.qty  # XXX: uom
                    elif inv.type == "in":
                        qty -= line.qty  # XXX: uom
            vals[obj.id] = qty
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

SaleReturnLine.register()
