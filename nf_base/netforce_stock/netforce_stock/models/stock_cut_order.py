from netforce.model import Model, fields, get_model
from netforce import access
from netforce import tasks
from netforce import database
from datetime import *
import time


class Order(Model):
    _name = "stock.cut.order"
    _fields = {
        "cut_id": fields.Many2One("stock.cut","Cutting",required=True,on_delete="cascade"),
        "width": fields.Decimal("Order Width",required=True),
        "qty": fields.Integer("Order Qty",required=True),
        "qty_type": fields.Selection([["allow","Allow Extra Qty"],["exact","Exact Qty"]],"Qty Type"),
        "pat_qty": fields.Integer("Cut Qty",function="get_pat_qty")
    }

    def get_pat_qty(self,ids,context={}):
        cut=None
        for obj in self.browse(ids):
            cut=obj.cut_id
            break
        qtys={}
        for pat in cut.patterns:
            qtys.setdefault(pat.width1,0)
            qtys[pat.width1]+=(pat.qty1 or 0)*(pat.num or 0)
            qtys.setdefault(pat.width2,0)
            qtys[pat.width2]+=(pat.qty2 or 0)*(pat.num or 0)
            qtys.setdefault(pat.width3,0)
            qtys[pat.width3]+=(pat.qty3 or 0)*(pat.num or 0)
            qtys.setdefault(pat.width4,0)
            qtys[pat.width4]+=(pat.qty4 or 0)*(pat.num or 0)
            qtys.setdefault(pat.width5,0)
            qtys[pat.width5]+=(pat.qty5 or 0)*(pat.num or 0)
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=qtys.get(obj.width)
        return vals

Order.register()
