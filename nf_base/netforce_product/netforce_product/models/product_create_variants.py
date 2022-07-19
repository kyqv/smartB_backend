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


class CreateVariants(Model):
    _name = "prod.create.variants"
    _transient = True
    _fields = {
        "related_id": fields.Many2One("product", "Product", required=True, on_delete="cascade"),
        "variant_value": fields.One2Many("product.variant.values", "popup_id", "Options"),
    }

    def _get_id(self, context={}):
        related_id = context["refer_id"]
        return related_id

    _defaults = {
        "related_id": _get_id,
    }

    def create_variants(self, ids, context={}):
        print("##################################")
        print("product.create_variants", ids)
        obj = self.browse(ids[0])
        prod = obj.related_id
        if prod.type != "master":
            raise Exception("Not a master product")
        if not obj.variant_value:
            raise Exception("No variant attribute for this product")
        variants = [{}]
        for attr in obj.variant_value:
            new_variants = []
            for variant in variants:
                for attr_val in attr.values:
                    new_variant = variant.copy()
                    new_variant[attr.attribute_id.id] = {
                        "code": attr_val.code, "name": attr_val.name, "id": attr_val.id}
                    new_variants.append(new_variant)
            variants = new_variants
        print("variants", len(variants), variants)
        count = 1
        for variant in variants:
            name = prod.name
            code = prod.code
            attributes = []
            for k, v in variant.items():
                name += " " + v['name']
                code += "_" + v['code']
                attributes_vals = {
                    "attribute_id": k,
                    "option_id": v['id'],
                }
                attributes.append(("create", attributes_vals))
            vals = {
                "code": code,
                "name": name,
                "type": "stock",
                "uom_id": prod.uom_id.id,
                "parent_id": prod.id,
                "location_id": prod.location_id.id,
                "attributes": attributes,
            }
            get_model("product").create(vals)
            count += 1
        return {
            "next": {
                "name": "product",
                "mode": "form",
                "active_id": prod.id,
            },
            "flash": "%d variants created" % len(variants),
        }

CreateVariants.register()
