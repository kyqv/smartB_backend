from netforce.model import Model, fields, get_model
from netforce import access
from netforce import tasks
from netforce import database
from datetime import *
import time


class Pat(Model):
    _name = "stock.cut.pattern"
    _fields = {
        "cut_id": fields.Many2One("stock.cut","Cutting",required=True,on_delete="cascade"),
        "stock_width": fields.Decimal("Stock Width",required=True),
        "num": fields.Integer("Repeat Times",required=True),
        "width1": fields.Decimal("Width #1",required=True),
        "qty1": fields.Decimal("Qty #1",required=True),
        "width2": fields.Decimal("Width #2"),
        "qty2": fields.Decimal("Qty #2"),
        "width3": fields.Decimal("Width #3"),
        "qty3": fields.Decimal("Qty #3"),
        "width4": fields.Decimal("Width #4"),
        "qty4": fields.Decimal("Qty #4"),
        "width5": fields.Decimal("Width #5"),
        "qty5": fields.Decimal("Qty #5"),
        "total_cut": fields.Decimal("Unit Cut",function="get_waste",function_multi=True),
        "waste": fields.Decimal("Unit Waste",function="get_waste",function_multi=True),
        "total_waste": fields.Decimal("Total Waste",function="get_waste",function_multi=True),
    }

    def get_waste(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            w=0
            if obj.width1 and obj.qty1:
                w+=obj.width1*obj.qty1
            if obj.width2 and obj.qty2:
                w+=obj.width2*obj.qty2
            if obj.width3 and obj.qty3:
                w+=obj.width3*obj.qty3
            if obj.width4 and obj.qty4:
                w+=obj.width4*obj.qty4
            if obj.width5 and obj.qty5:
                w+=obj.width5*obj.qty5
            waste=obj.stock_width-w
            vals[obj.id]={
                "total_cut": w,
                "waste": waste,
                "total_waste": waste*obj.num,
            }
        return vals

Pat.register()
