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


class ProductBrand(Model):
    _name = "product.brand"
    _string = "Brand"
    #_key=["code"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "description": fields.Text("Description", search=True),
        "image": fields.File("Image"),
        "code": fields.Char("Code"),
        "parent_id": fields.Many2One("product.brand","Parent Brand"),
        "sub_brands": fields.One2Many("product.brand","parent_id","Sub Brands"),
        "products": fields.One2Many("product","brand_id","Products", operator="child_of"),
        "num_products": fields.Integer("Number of products", function="get_num_products"),
        "groups": fields.Many2Many("product.brand.group","Group"),
        "categs": fields.Many2Many("product.categ","Categs"),
    }
    _order = "name"

    def get_num_products(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            nums = 0
            for product in obj.products:
                if not product.parent_id:
                    nums += 1
            vals[obj.id] = nums
        return vals 

ProductBrand.register()
