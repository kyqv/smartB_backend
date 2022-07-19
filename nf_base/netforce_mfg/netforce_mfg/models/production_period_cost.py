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


class ProductionPeriodCost(Model):
    _name = "production.period.cost"
    _string = "Production Period Cost"
    _fields = {
        "period_id": fields.Many2One("production.period", "Production Period", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product","Cost Product"),
        "amount": fields.Decimal("Period Actual Amount",required=True),
        "alloc_amount": fields.Decimal("Production Order Amount",function="get_alloc_amount"),
    }

    def get_alloc_amount(self,ids,context={}):
        period_ids=[]
        for obj in self.browse(ids):
            period_ids.append(obj.period_id.id)
        period_ids=list(set(period_ids))
        total_costs={}
        for cost in get_model("production.cost").search_browse([["order_id.period_id","in",period_ids]]):
            period_id=cost.order_id.period_id.id
            prod_id=cost.product_id.id
            k=(period_id,prod_id)
            total_costs.setdefault(k,0)
            total_costs[k]+=cost.amount
        vals={}
        for obj in self.browse(ids):
            k=(obj.period_id.id,obj.product_id.id)
            vals[obj.id]=total_costs.get(k,0)
        return vals

ProductionPeriodCost.register()
