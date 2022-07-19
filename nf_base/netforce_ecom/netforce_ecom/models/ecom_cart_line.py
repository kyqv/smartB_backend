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
from decimal import Decimal
import math

class CartLine(Model):
    _name = "ecom.cart.line"
    _fields = {
        "cart_id": fields.Many2One("ecom.cart", "Cart", required=True, on_delete="cascade"),
        "sequence": fields.Integer("Item No.", required=True),
        "product_id": fields.Many2One("product", "Product", required=True, on_delete="cascade"),
        "description": fields.Text("Description"),
        "qty": fields.Integer("Qty", required=True),
        "unit_price": fields.Decimal("Unit Price", required=True),
        "discount_percent": fields.Decimal("Discount Percent"),
        "discount_amount": fields.Decimal("Discount Amount"),
        "promotion_amount": fields.Decimal("Promotion Amount",function="_get_amount"),
        "amount_before_discount": fields.Decimal("Amount Before Discount", function="_get_amount", function_multi=True),
        "amount": fields.Decimal("Amount", function="_get_amount", function_multi=True),
        "special_price": fields.Decimal("Special Price", function="_get_amount", function_multi=True),
        "has_discount": fields.Boolean("Has Discount", function="_get_amount", function_multi=True),
        "image": fields.File("Image"),
        "images": fields.One2Many("ecom.cart.line.image", "line_id", "Images"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),
    }
    _order = "sequence"
    _defaults = {
        "is_discounted": False,
    }

    def _get_amount(self, ids, context={}):
        vals = {}
        cart_ids=[]
        for obj in self.browse(ids):
            cart_ids.append(obj.cart_id.id)
        cart_ids=list(set(cart_ids))
        for cart in get_model("ecom.cart").browse(cart_ids):
            prod_qtys={}
            prom_amts={}
            prom_pcts={}
            for line in cart.lines:
                prod_qtys.setdefault(line.product_id.id,0)
                prod_qtys[line.product_id.id]+=line.qty
            for prom in cart.used_promotions:
                if prom.amount and prom.product_id:
                    prom_amts.setdefault(prom.product_id.id,0)
                    prom_amts[prom.product_id.id]+=prom.amount
                elif prom.percent:
                    prom_pcts.setdefault(prom.product_id.id,0)
                    prom_pcts[prom.product_id.id]+=prom.percent
            for line in cart.lines:
                amt_before_disc = line.qty * line.unit_price
                amt=amt_before_disc
                has_disc=False
                if line.discount_percent:
                    amt -= amt_before_disc*line.discount_percent / 100
                    has_disc = True
                if line.discount_amount:
                    amt -= line.discount_amount
                    has_disc = True
                amt_before_prom=amt
                prom_amt=prom_amts.get(line.product_id.id,Decimal(0))/prod_qtys[line.product_id.id]*line.qty
                prom_pct=prom_pcts.get(line.product_id.id,Decimal(0))+prom_pcts.get(None,0)
                if prom_pct:
                    prom_amt+=math.ceil(amt_before_prom/line.qty*prom_pct/100)*line.qty
                if prom_amt:
                    amt -= prom_amt
                    has_disc = True
                special_price = amt / line.qty if line.qty else None
                if line.id in ids:
                    vals[line.id] = {
                        "promotion_amount": prom_amt,
                        "amount_before_discount": amt_before_disc,
                        "amount": amt,
                        "special_price": special_price,
                        "has_discount": has_disc,
                    }
        return vals

    def change_qty(self, ids, qty):
        print("CartLine.change_qty", ids, qty)
        obj = self.browse(ids)[0]
        if qty==obj.qty:
            return
        if qty > 0:
            disc_amt=obj.discount_amount*qty/obj.qty
            obj.write({"qty": qty,"discount_amount": disc_amt})
        else:
            obj.delete()
        cart = obj.cart_id
        cart.update_promotions()

CartLine.register()
