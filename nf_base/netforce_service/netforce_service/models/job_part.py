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


class JobPart(Model):
    _name = "job.part"
    _audit_log = True
    _fields = {
        "job_id": fields.Many2One("job", "Job", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", required=True),
        "qty_planned": fields.Decimal("Planned Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "From Warehouse", required=True),
        "qty_issued": fields.Decimal("Issued Qty", function="get_qty_issued"),
        "unit_price": fields.Decimal("Sale Unit Price"),
        "amount": fields.Decimal("Sale Amount", function="get_amount"),
    }

    def get_amount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.qty_issued and obj.unit_price:
                vals[obj.id] = obj.qty_issued * obj.unit_price
            else:
                vals[obj.id] = None
        return vals

    def get_qty_issued(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            job = obj.job_id
            total_qty = 0
            for pick in job.pickings:
                for move in pick.lines:
                    if move.product_id.id != obj.product_id.id or move.state != "done":
                        continue
                    qty = get_model("uom").convert(move.qty, move.uom_id.id, obj.uom_id.id)
                    if move.location_from_id.id == obj.location_id.id and move.location_to_id.id != obj.location_id.id:
                        total_qty += qty
                    elif move.location_from_id.id != obj.location_id.id and move.location_to_id.id == obj.location_id.id:
                        total_qty -= qty
            vals[obj.id] = total_qty
        return vals

JobPart.register()
