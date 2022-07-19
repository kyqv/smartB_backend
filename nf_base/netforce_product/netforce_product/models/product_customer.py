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

from netforce.model import Model, fields


class ProductCustomer(Model):
    _name = "product.customer"
    _string = "Product Customer"
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True, on_delete="cascade"),
        "sequence": fields.Integer("Sequence"),
        "customer_id": fields.Many2One("contact", "Customer", required=True),
        "customer_product_code": fields.Char("Customer Product Code"),
        "customer_product_name": fields.Char("Customer Product Name"),
        "packaging_id": fields.Many2One("stock.packaging","Packaging"),
    }
    _order = "sequence,id"
    _defaults = {
        "sequence": 1,
    }

ProductCustomer.register()
