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


class PriceListItem(Model):
    _name = "price.list.item"
    _string = "Price List Item"
    _fields = {
        "list_id": fields.Many2One("price.list", "Price List", required=True, on_delete="cascade", search=True),
        "type": fields.Selection([["sale", "Sales"], ["purchase", "Purchasing"]], "Type", function="_get_related", function_context={"path": "list_id.type"}, search=True),
        "currency_id": fields.Many2One("currency", "Currency", function="_get_related", function_context={"path": "list_id.currency_id"}, search=True),
        "product_id": fields.Many2One("product", "Product", required=True, search=True, on_delete="cascade"),
        "price": fields.Decimal("Price", required=True, scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "discount_percent": fields.Decimal("Discount %"),
        "min_qty": fields.Decimal("Min Qty"),
        "max_qty": fields.Decimal("Max Qty"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "discount_text": fields.Char("Discount Text"),
    }

PriceListItem.register()
