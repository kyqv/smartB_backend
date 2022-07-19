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


class ProductLocation(Model):
    _name = "product.location"
    _string = "Product Location"
    _fields = {
        "product_id": fields.Many2One("product","Product",on_delete="cascade"),
        "product_categ_id": fields.Many2One("product.categ","Product Categ",on_delete="cascade"),
        "sequence": fields.Integer("Sequence",required=True),
        "location_id": fields.Many2One("stock.location","Warehouse",required=True,on_delete="cascade"),
        "bin_location": fields.Char("Bin Location"),
        "reserve_location_id": fields.Many2One("stock.location","Reservation Location"),
        "stock_qty": fields.Decimal("Stock Qty",function="get_stock_qty"),
    }
    _order = "sequence"
    _defaults={
        "sequence": 1,
    }

    def get_stock_qty(self,ids,context={}):
        vals = {}
        for obj in self.browse(ids):
            qty=0
            for bal in get_model("stock.balance").search_browse([["product_id","=",obj.product_id.id],["location_id","=",obj.location_id.id]]):
                qty+=bal.qty_virt
            vals[obj.id]=qty
        return vals

ProductLocation.register()
