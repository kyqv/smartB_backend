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
import time


class TransformLine(Model):
    _name = "stock.transform.line"
    _fields = {
        "transform_id": fields.Many2One("stock.transform","Transform",required=True,search=True,on_delete="cascade"),
        "type": fields.Selection([["in","From"],["out","To"],["service","Service"]],"Type",required=True),
        "product_id": fields.Many2One("product","To Product",required=True,search=True,condition=[["type","=","stock"]]),
        "lot_id": fields.Many2One("stock.lot","Lot / Serial No.",search=True),
        #"cost_price": fields.Decimal("Cost Unit Price",function="get_cost_price"),
        "cost_price": fields.Decimal("Cost Unit Price",scale=6),
        "cost_amount": fields.Decimal("Cost Amount",function="get_cost_amt"),
        "qty": fields.Decimal("Qty",required=True),
        "uom_id": fields.Many2One("uom","UoM",required=True),
        "qty2": fields.Decimal("Qty2"),
        "weight": fields.Decimal("Gross Weight", function="get_gross_weight", store=False),
        "location_id": fields.Many2One("stock.location", "Location", condition=[["type", "=", "internal"]], search=True),
        "picking_id": fields.Many2One("stock.picking","Goods Receipt"),
        "supplier_id": fields.Many2One("contact","Supplier"),
        "move_id": fields.Many2One("stock.move","Stock Movement"),
    }

    def get_cost_price(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=obj.move_id.cost_price if obj.move_id else None
        return vals

    def get_cost_amt(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=obj.cost_price*obj.qty if obj.cost_price else None
        return vals

    def get_gross_weight(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.lot_id:
                vals[obj.id]=obj.lot_id.weight
            else:
                vals[obj.id]=obj.product_id.weight if obj.product_id else None
        return vals

TransformLine.register()
