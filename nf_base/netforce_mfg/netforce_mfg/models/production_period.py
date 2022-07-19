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
from netforce.database import get_connection
from datetime import *
import time


class ProductionPeriod(Model):
    _name = "production.period"
    _string = "Production Period"
    _name_field="number"
    _fields = {
        "number": fields.Char("Number",required=True,search=True),
        "date_from": fields.Date("Date From",required=True),
        "date_to": fields.Date("Date To",required=True),
        "production_orders": fields.One2Many("production.order","period_id","Production Orders"),
        "costs": fields.One2Many("production.period.cost","period_id","Period Costs"),
        "amount_total": fields.Decimal("Period Actual Total",function="get_total",function_multi=True),
        "alloc_total": fields.Decimal("Production Order Total",function="get_total",function_multi=True),
    }

    def update_period_costs(self,ids,context={}):
        obj=self.browse(ids)[0]
        cost_prod_ids=[]
        for cost in get_model("production.cost").search_browse([["order_id.period_id","=",obj.id]]):
            prod_id=cost.product_id.id
            cost_prod_ids.append(prod_id)
        cost_prod_ids=list(set(cost_prod_ids))
        cur_prod_ids=[c.product_id.id for c in obj.costs]
        new_prod_ids=[prod_id for prod_id in cost_prod_ids if prod_id not in cur_prod_ids]
        for prod_id in new_prod_ids:
            vals={
                "period_id": obj.id,
                "product_id": prod_id,
                "amount": 0,
            }
            get_model("production.period.cost").create(vals)

    def get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            alloc=0
            for cost in obj.costs:
                amt+=cost.amount or 0
                alloc+=cost.alloc_amount or 0
            vals[obj.id]={
                "amount_total": amt,
                "alloc_total": alloc,
            }
        return vals

ProductionPeriod.register()
