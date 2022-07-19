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
from netforce import utils
from netforce import tasks
import time


class PriceList(Model):
    _name = "price.list"
    _string = "Price List"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "code": fields.Char("Code", search=True),
        "type": fields.Selection([["sale", "Sales"], ["purchase", "Purchasing"]], "Type", required=True, search=True),
        "date": fields.Date("Date", search=True),
        "base_price": fields.Selection([["product", " List Price In Product"], ["other_pricelist", "Other Price List"], ["volume", "Product Volume"]], "Base Price"),
        "other_pricelist_id": fields.Many2One("price.list", "Other Price List"),
        #"factor": fields.Decimal("Factor", scale=6),
        "discount_percent": fields.Decimal("Discount (%)"),
        "discount": fields.Decimal("Discount"),  # XXX: deprecated
        "lines": fields.One2Many("price.list.item", "list_id", "Price List Items"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "currency_id": fields.Many2One("currency", "Currency", required=True, search=True),
        "rounding": fields.Decimal("Rounding Multiple"),
        "rounding_method": fields.Selection([["nearest", "Nearest"], ["lower", "Lower"], ["upper", "Upper"]], "Rounding Method"),
        "sale_channels": fields.One2Many("sale.channel", "pricelist_id","Sales Channels"),
        "categs": fields.One2Many("price.list.categ", "list_id","Product Categories"),
    }

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "currency_id": _get_currency,
    }

    def update_items(self, ids, context={}):
        job_id=context.get("job_id")
        for obj in self.browse(ids):
            obj.lines.delete()
            for categ in obj.categs:
                prods=get_model("product").search_browse([["categ_id","child_of",categ.categ_id.id]])
                for i,prod in enumerate(prods):
                    if job_id:
                        if tasks.is_aborted(job_id):
                            return
                        tasks.set_progress(job_id,i*100/len(prods),"Product %s of %s of category %s"%(i+1,len(prods),categ.categ_id.name))
                    discount_percent=categ.discount_percent or 0
                    price=(prod.sale_price or 0)*(1-discount_percent/100)
                    price=int(price) # XXX
                    vals={
                        "list_id": obj.id,
                        "product_id": prod.id,
                        "discount_percent": categ.discount_percent,
                        "discount_text": categ.discount_text,
                        "price": price,
                    }
                    get_model("price.list.item").create(vals)

    def get_price(self, list_id, prod_id, qty, uom_id=None, context={}):
        print("get_price", list_id, prod_id, qty, uom_id)
        if not qty:
            qty=0
        price=None
        for item in get_model("price.list.item").search_browse([["list_id", "=", list_id], ["product_id", "=", prod_id]]):
            if item.min_qty and qty < item.min_qty:
                continue
            if item.max_qty and qty > item.max_qty:
                continue
            price=item.price
            break
        if not price:
            prod=get_model("product").browse(prod_id)
            price=prod.sale_price # XXX
        if price is None:
            return
        if not uom_id:
            return price
        prod=get_model("product").browse(prod_id)
        price_uom_id=prod.sale_price_uom_id.id or prod.uom_id.id
        price_conv=get_model("uom").convert(price,uom_id,price_uom_id,product_id=prod.id)
        return price_conv

PriceList.register()
