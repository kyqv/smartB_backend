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
from netforce.utils import get_data_path
from datetime import *
import time


class Bom(Model):
    _name = "bom"
    _string = "Bill of Material"
    _name_field = "number"
    _key = ["number"]
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "product_id": fields.Many2One("product", "FG Product", required=True, search=True),
        "qty": fields.Decimal("Qty", required=True, scale=6),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "FG Warehouse"),
        "production_location_id": fields.Many2One("stock.location", "Production Location"),
        "virt_production_location_id": fields.Many2One("stock.location", "Virtual Production Location",condition=[["type","=","production"]]),
        "routing_id": fields.Many2One("routing", "Routing"),
        "lines": fields.One2Many("bom.line", "bom_id", "Lines"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "max_qty_loss": fields.Decimal("Max Qty Loss", scale=6),
        "container": fields.Selection([["sale", "From Sales Order"]], "FG Container"),
        "lot": fields.Selection([["production", "From Production Order"]], "FG Lot"),
        "rm_product_id": fields.Many2One("product","RM Product",store=False,function_search="search_rm_product",search=True),
        "type": fields.Selection([["normal","Normal"],["phantom","Phantom"]], "BoM Type", required=True),
        "rm_cost_amount": fields.Decimal("Raw Materials Cost",function="get_cost",function_multi=True),
        "direct_labor_amount": fields.Decimal("Direct Labor Amount"),
        "total_direct_labor": fields.Decimal("Total RM + Direct Labor",function="get_cost",function_multi=True),
        "factory_overhead_amount": fields.Decimal("Factory Overhead Amount"),
        "total_factory_overhead": fields.Decimal("Total Factory Cost",function="get_cost",function_multi=True),
        "other_overhead_amount": fields.Decimal("Finance & Operating Expenses Absorbed"),
        "total_other_overhead": fields.Decimal("Total Cost Excl. Wastage",function="get_cost",function_multi=True),
        "waste_amount": fields.Decimal("Wastage Cost Amount",function="get_cost",function_multi=True),
        "waste_percent": fields.Decimal("Wastage Cost Percent (%)"),
        "extra_amount": fields.Decimal("Extra Cost Amount",function="get_cost",function_multi=True),
        "extra_percent": fields.Decimal("Extra Cost Percent (%)"),
        "cost_amount_total": fields.Decimal("Total Cost Amount",function="get_cost",function_multi=True),
    }

    def _get_number(self, context={}):
        while 1:
            num = get_model("sequence").get_number("bom")
            if not num:
                return None
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment("bom")

    _defaults = {
        "number": _get_number,
        "type": "normal",
    }

    def onchange_product(self,context={}):
        data=context['data']
        path=context['path']
        line=get_data_path(data,path,parent=True)
        product_id=line['product_id']
        if product_id:
            product=get_model('product').browse(product_id)
            line["weight"]=product.weight
            line['uom_id']=product.uom_id.id
            if product.locations:
                line["location_id"]=product.locations[0].location_id.id
        return data

    def onchange_qty2(self,context={}):
        data=context['data']
        path=context['path']
        line=get_data_path(data,path,parent=True)
        prod_id=line['product_id']
        if not prod_id:
            return
        prod=get_model("product").browse(prod_id)
        if not prod.weight:
            return
        line["qty"]=line["qty2"]/prod.weight
        return data

    def copy(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            vals={
                "number": "%s (Copy)"%obj.number,
                "product_id": obj.product_id.id,
                "qty": obj.qty,
                "uom_id": obj.uom_id.id,
                "location_id": obj.location_id.id,
                "routing_id": obj.routing_id.id,
                "comments": obj.comments,
                "lines": [],
            }
            for line in obj.lines:
                line_vals={
                    "product_id": line.product_id.id,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "location_id": line.location_id.id,
                    "qty2": line.qty2,
                    "notes": line.notes,
                    "issue_method": line.issue_method,
                }
                vals["lines"].append(("create",line_vals))
            new_id=self.create(vals)
            n+=1
        return {
            "flash": "%d BoMs copied"%n,
            "new_id": new_id,
        }

    def get_cost(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            tot1=0
            for line in obj.lines:
                tot1+=line.cost_amount or 0
            tot2=tot1+(obj.direct_labor_amount or 0)
            tot3=tot2+(obj.factory_overhead_amount or 0)
            tot4=tot3+(obj.other_overhead_amount or 0)
            amt_waste=tot4*(obj.waste_percent or 0)/100
            tot5=tot4+amt_waste
            amt_extra=tot5*(obj.extra_percent or 0)/100
            tot6=tot5+amt_extra
            vals[obj.id]={
                "rm_cost_amount": tot1,
                "total_direct_labor": tot2,
                "total_factory_overhead": tot3,
                "total_other_overhead": tot4,
                "waste_amount": amt_waste,
                "extra_amount": amt_extra,
                "cost_amount_total": tot6,
            }
        return vals

    def search_rm_product(self, clause, context={}):
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        bom_ids = []
        for line in get_model("bom.line").search_browse([["product_id","in",product_ids]]):
            bom_ids.append(line.bom_id.id)
        cond = [["id","in",bom_ids]]
        return cond

    def update_product_cost(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            prod=obj.product_id
            cost=obj.cost_amount_total or 0
            prod.write({"cost_price":cost})
            n+=1
        return {
            "alert": "%d products updated"%n,
        }

Bom.register()
