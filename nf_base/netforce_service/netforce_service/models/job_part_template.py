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
import datetime


class PartTemplate(Model):
    _name = "job.part.template"
    _string = "Part Template"
    _fields = {
        "job_template_id": fields.Many2One("job.template", "Job Template", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product"),
        "qty": fields.Decimal("Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "From Warehouse", required=True),
        "unit_price": fields.Decimal("Sale Unit Price"),
        "amount": fields.Decimal("Sale Amount", function="get_amount"),
    }

    def onchange_product(self, context={}):
        data = context["data"]
        prod_id = data["product_id"]
        prod = get_model("product").browse(prod_id)
        data["uom_id"] = prod.uom_id.id
        data["unit_price"] = prod.sale_price
        return data

    def get_amount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = (obj.qty or 0) * (obj.unit_price or 0)
        return vals

PartTemplate.register()
