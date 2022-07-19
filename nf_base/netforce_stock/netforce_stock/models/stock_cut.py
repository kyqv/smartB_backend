from netforce.model import Model, fields, get_model
from netforce import access
from netforce import tasks
from netforce import database
from netforce import utils
from datetime import *
import time
import json
import random
import requests


class Cut(Model):
    _name = "stock.cut"
    _string = "Stock Cutting"
    _fields = {
        "date": fields.Date("Date"),
        "orders": fields.One2Many("stock.cut.order","cut_id","Orders"),
        "stock": fields.One2Many("stock.cut.stock","cut_id","Stock"),
        "patterns": fields.One2Many("stock.cut.pattern","cut_id","Patterns"),
        "total_waste": fields.Decimal("Total Waste",function="get_total_waste"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def get_total_waste(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            tot=0
            for line in obj.patterns:
                tot+=line.total_waste or 0
            vals[obj.id]=tot
        return vals

    def solve(self,ids,context={}):
        obj=self.browse(ids[0])
        orders=[]
        for o in obj.orders:
            orders.append({
                "width": o.width,
                "qty": o.qty,
                "qty_type": o.qty_type,
            })
        stock=[]
        for s in obj.stock:
            stock.append({
                "width": s.width,
                "qty": s.qty,
                "jumbo": s.jumbo,
            })
        conf={
            "orders": orders,
            "stock": stock,
        }
        url="http://compass.netforce.com:12080/solve"
        data=utils.json_dumps(conf)
        req=requests.post(url,data=data)
        if req.status_code!=200:
            raise Exception("Request failed: %s"%req.status_code)
        res=req.json()
        pats=res.get("patterns")
        if not pats:
            raise Exception("Missing patterns")
        obj.patterns.delete()
        for p in pats:
            vals={
                "cut_id": obj.id,
                "stock_width": p["stock_width"],
                "num": p["num_repeat"],
            }
            i=1
            for c in p["cuts"]:
                vals["width%s"%i]=c[0]
                vals["qty%s"%i]=c[1]
                i+=1
            get_model("stock.cut.pattern").create(vals)

Cut.register()
