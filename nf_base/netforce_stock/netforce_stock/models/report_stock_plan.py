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
from netforce import access
from netforce.database import get_connection
from datetime import *
from dateutil.relativedelta import *
import time
import math

def get_total_qtys(prod_ids, loc_id, date_from, date_to, states, categ_ids):
    db = get_connection()
    q = "SELECT " \
        " m.product_id,p.uom_id AS prod_uom_id,m.location_from_id,m.location_to_id,m.uom_id,SUM(m.qty) AS total_qty " \
        " FROM stock_move m " \
        " LEFT JOIN product p on m.product_id=p.id " \
        " WHERE m.state IN %s"
    q_args = [tuple(states)]
    if date_from:
        q += " AND m.date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND m.date<=%s"
        q_args.append(date_to + " 23:59:59")
    if prod_ids:
        q += " AND m.product_id IN %s"
        q_args.append(tuple(prod_ids))
    if loc_id:
        q += " AND (m.location_from_id=%s OR m.location_to_id=%s)"
        q_args += [loc_id, loc_id]
    if categ_ids:
        q += " AND p.categ_id IN %s"
        q_args.append(tuple(categ_ids))
    company_id = access.get_active_company()
    if company_id:
        q += " AND m.company_id=%s"
        q_args.append(company_id)
    q += " GROUP BY m.product_id,p.uom_id,m.location_from_id,m.location_to_id,m.uom_id"
    print("q",q)
    print("q_args",q_args)
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        qty = get_model("uom").convert(r.total_qty,r.uom_id,r.prod_uom_id)
        k = (r.product_id, r.location_from_id, r.location_to_id)
        totals.setdefault(k, 0)
        totals[k] += qty
    return totals

class ReportStockPlan(Model):
    _name = "report.stock.plan"
    _transient = True
    _fields = {
        "product_categ_id": fields.Many2One("product.categ", "Product Category", on_delete="cascade"),
        "supplier_id": fields.Many2One("contact","Supplier"),
        "plan_horizon": fields.Integer("Planning Horizon (days)"),
    }
    _defaults={
        "plan_horizon": 5,
    }

    def get_report_data(self, ids, context={}):
        print("StockPlan.get_report_data",ids)
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        categ_id=params.get("product_categ_id")
        if categ_id:
            categ_ids=get_model("product.categ").search([["id","child_of",categ_id]])
        else:
            categ_ids=None
        print("categ_ids",categ_ids)
        supplier_id=params.get("supplier_id")
        plan_horizon=params.get("plan_horizon")
        if supplier_id:
            filter_prod_ids=[]
            for prod in get_model("product").search_browse([]): # XXX: make faster
                if prod.suppliers and prod.suppliers[0].supplier_id.id==supplier_id:
                    filter_prod_ids.append(prod.id)
        else:
            filter_prod_ids=None
        print("filter_prod_ids",filter_prod_ids)
        date_to=(date.today()+timedelta(days=plan_horizon)).strftime("%Y-%m-%d")
        print("getting qtys...")
        t0=time.time()
        res = get_total_qtys(filter_prod_ids, None, None, date_to, ["done","pending","approved","forecast"], categ_ids)
        t1=time.time()
        print("got qtys in %.2f s"%(t1-t0))
        loc_types={}
        for loc in get_model("stock.location").search_browse([]):
            loc_types[loc.id]=loc.type
        qtys_horiz={}
        for (prod_id,loc_from_id,loc_to_id),qty in res.items():
            qtys_horiz.setdefault(prod_id,0)
            if loc_types[loc_from_id]=="internal":
                qtys_horiz[prod_id]-=qty
            if loc_types[loc_to_id]=="internal":
                qtys_horiz[prod_id]+=qty
        print("qtys_horiz",qtys_horiz)
        min_qtys=get_model("stock.order").get_min_qtys()
        #print("min_qtys",min_qtys)
        below_prod_ids=[]
        for prod_id,qty in qtys_horiz.items():
            min_qty=min_qtys.get(prod_id,0)
            if qty<min_qty:
                below_prod_ids.append(prod_id)
        #print("below_prod_ids",below_prod_ids)
        lines=[]
        for prod in get_model("product").browse(below_prod_ids):
            qty_horiz=qtys_horiz.get(prod.id,0)
            min_qty=min_qtys.get(prod.id,0)
            req_qty=min_qty-qty_horiz
            if prod.supply_method=="purchase":
                supply_method="Purchase"
                if prod.purchase_uom_id and prod.purchase_uom_id.id!=prod.uom_id.id:
                    order_uom=prod.purchase_uom_id
                    if not prod.purchase_to_stock_uom_factor:
                        raise Exception("Missing purchase to stock UoM factor for product %s"%prod.code)
                    order_qty=req_qty/prod.purchase_to_stock_uom_factor
                else:
                    order_uom=prod.uom_id
                    order_qty=req_qty
                order_lead_time=prod.purchase_lead_time
                if prod.purchase_min_qty and order_qty<prod.purchase_min_qty:
                    order_qty=prod.purchase_min_qty
                if prod.purchase_qty_multiple and order_qty%prod.purchase_qty_multiple!=0:
                    n=math.ceil(order_qty/prod.purchase_qty_multiple)
                    order_qty=n*prod.purchase_qty_multiple
            elif prod.supply_method=="production":
                supply_method="Production"
                order_uom=prod.uom_id
                order_qty=req_qty
                order_lead_time=prod.mfg_lead_time
                if prod.mfg_min_qty and order_qty<prod.mfg_min_qty:
                    order_qty=prod.mfg_min_qty
                if prod.mfg_qty_multiple and order_qty%prod.mfg_qty_multiple!=0:
                    n=math.ceil(order_qty/prod.mfg_qty_multiple)
                    order_qty=n*prod.mfg_qty_multiple
            else:
                supply_method=None
                order_uom=None
                order_qty=None
                order_lead_time=None
            line_vals={
                "product_id": prod.id,
                "product_code": prod.code,
                "product_name": prod.name,
                "plan_qty_horiz": qty_horiz,
                "min_qty": min_qty,
                "req_qty": req_qty,
                "stock_uom_name": prod.uom_id.name,
                "order_qty": order_qty,
                "order_uom_name": order_uom and order_uom.name or None,
                "order_lead_time": order_lead_time,
                "supply_method": supply_method,
                "supplier_name": prod.suppliers and prod.suppliers[0].supplier_id.name or None,
            }
            lines.append(line_vals)
        lines.sort(key=lambda l: l["product_code"])
        #print("lines",lines)
        data = {
            "company_name": comp.name,
            "plan_horizon": plan_horizon,
            "lines": lines,
        }
        return data

ReportStockPlan.register()
