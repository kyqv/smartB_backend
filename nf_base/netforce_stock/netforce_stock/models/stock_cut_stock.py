from netforce.model import Model, fields, get_model
from netforce import access
from netforce import tasks
from netforce import database
from datetime import *
import time


class Stock(Model):
    _name = "stock.cut.stock"
    _fields = {
        "cut_id": fields.Many2One("stock.cut","Cutting",required=True,on_delete="cascade"),
        "width": fields.Decimal("Stock Width",required=True),
        "qty": fields.Integer("Stock Qty",required=True),
        "jumbo": fields.Boolean("Jumbo"),
        "pat_qty": fields.Integer("Cut Qty",function="get_pat_qty")
    }

    def get_pat_qty(self,ids,context={}):
        cut=None
        for obj in self.browse(ids):
            cut=obj.cut_id
            break
        qtys={}
        for pat in cut.patterns:
            qtys.setdefault(pat.stock_width,0)
            qtys[pat.stock_width]+=pat.num or 0
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=qtys.get(obj.width)
        return vals

Stock.register()
