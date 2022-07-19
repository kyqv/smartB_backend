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


class ProductGroup(Model):
    _name = "product.group"
    _string = "Product Group"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Group Name", required=True, search=True),
        "code": fields.Char("Group Code", search=True),
        "parent_id": fields.Many2One("product.group", "Parent"),
        "products": fields.Many2Many("product", "Products"),
        "filter_products": fields.Many2Many("product","Products",function="get_filter_products"),
        "image": fields.File("Image"),
        "company_id": fields.Many2One("company","Company"),
        "description" :fields.Text("Description"),
        "sequence": fields.Integer("Sequence"),
        "color": fields.Char("Color"),
    }
    _order = "sequence,name"

    def get_filter_products(self,ids,context={}):
        group_id=ids[0]
        cond=[["groups.id","=",group_id],["is_published","=",True]]
        if context.get("product_filter"):
            cond.append(context["product_filter"])
        prod_ids=get_model("product").search(cond)
        vals={
            group_id: prod_ids,
        }
        return vals

ProductGroup.register()
