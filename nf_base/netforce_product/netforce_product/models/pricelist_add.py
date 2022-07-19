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


class PricelistAdd(Model):
    _name = "pricelist.add"
    _transient = True
    _fields = {
        "pricelist_id": fields.Many2One("price.list", "Price List", required=True, on_delete="cascade"),
        "product_categs": fields.Many2Many("product.categ", "Product Categories"),
    }
    _defaults = {
        "pricelist_id": lambda self, ctx: ctx["refer_id"],
    }

    def add_products(self, ids, context={}):
        obj = self.browse(ids)[0]
        pricelist = obj.pricelist_id
        categ_ids = [c.id for c in obj.product_categs]
        for prod in get_model("product").search_browse([["categs.id", "in", categ_ids]]):
            factor = pricelist.factor or 1.0
            if pricelist.base_price == "product":
                base_price = prod.sale_price or 0
            elif pricelist.base_price == "other_pricelist":
                if not pricelist.other_pricelist_id:
                    raise Exception("Missing base price list")
                base_price = get_model("price.list").get_price(
                    pricelist.other_pricelist_id.id, prod.id, 1) or 0  # XXX: qty
            elif pricelist.base_price == "volume":
                base_price = prod.volume or 0
            else:
                raise Exception("Invalid base price type")
            price = utils.round_amount(base_price * factor, pricelist.rounding, pricelist.rounding_method)
            vals = {
                "list_id": pricelist.id,
                "product_id": prod.id,
                "price": price,
            }
            get_model("price.list.item").create(vals)
        return {
            "next": {
                "name": "pricelist_item",
            },
            "flash": "Products added to price list",
        }

PricelistAdd.register()
