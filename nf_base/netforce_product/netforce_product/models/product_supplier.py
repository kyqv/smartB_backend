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


class ProductSupplier(Model):
    _name = "product.supplier"
    _string = "Product Supplier"
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True, on_delete="cascade"),
        "sequence": fields.Integer("Sequence"),
        "supplier_id": fields.Many2One("contact", "Supplier", required=True),
        "supplier_product_code": fields.Char("Supplier Product Code"),
        "supplier_product_name": fields.Char("Supplier Product Name"),
        "purchase_price": fields.Char("Purchase Price"),
    }
    _order = "sequence,id"
    _defaults = {
        "sequence": 1,
    }

    def name_get(self,ids,context={}):
        vals=[]
        settings=get_model("settings").browse(1)
        for obj in self.browse(ids):
            vals.append([obj.id,"%s: %s %s"%(obj.supplier_id.name,obj.purchase_price,settings.currency_id.code)])
        return vals 

ProductSupplier.register()
