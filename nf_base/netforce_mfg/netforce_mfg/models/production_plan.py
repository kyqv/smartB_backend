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
from netforce import access
from netforce import tasks
from netforce import database
from datetime import *
import time

def get_total_qtys(prod_ids=None, lot_id=None, loc_ids=None, date_from=None, date_to=None, states=None, categ_id=None):
    db = database.get_connection()
    q = "SELECT " \
        " t1.product_id,t1.lot_id,t1.location_from_id,t1.location_to_id,t1.uom_id,SUM(t1.qty) AS total_qty " \
        " FROM stock_move t1 " \
        " LEFT JOIN product t2 on t1.product_id=t2.id " \
        " WHERE t1.state IN %s"
    q_args = [tuple(states)]
    if date_from:
        q += " AND t1.date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND t1.date<=%s"
        q_args.append(date_to + " 23:59:59")
    if prod_ids:
        q += " AND t1.product_id IN %s"
        q_args.append(tuple(prod_ids))
    if lot_id:
        q += " AND t1.lot_id=%s"
        q_args.append(lot_id)
    if loc_ids:
        q += " AND (t1.location_from_id IN %s OR t1.location_to_id IN %s)"
        q_args += [tuple(loc_ids), tuple(loc_ids)]
    if categ_id:
        q += " AND t2.categ_id=%s"
        q_args.append(categ_id)
    company_id = access.get_active_company()
    if company_id:
        q += " AND t1.company_id=%s"
        q_args.append(company_id)
    q += " GROUP BY t1.product_id,t1.lot_id,t1.location_from_id,t1.location_to_id,t1.uom_id"
    #print("q",q)
    #print("q_args",q_args)
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        prod = get_model("product").browse(r.product_id)
        uom = get_model("uom").browse(r.uom_id)
        qty = r.total_qty * uom.ratio / prod.uom_id.ratio
        k = (r.product_id, r.lot_id, r.location_from_id, r.location_to_id)
        totals.setdefault(k, 0)
        totals[k] += qty
    return totals

class ProductionPlan(Model):
    _name = "production.plan"
    _string = "Production Plan"
    _fields = {
        "number": fields.Char("Number", search=True), # XXX: deprecated
        "product_id": fields.Many2One("product", "Product", required=True, search=True),
        "customer_id": fields.Many2One("contact", "Customer", search=True),
        "date_from": fields.Date("From Date", search=True), # XXX: deprecated
        "date_to": fields.Date("To Date", search=True), # XXX: deprecated
        "date": fields.Date("Production Date", required=True, search=True),
        "plan_qty": fields.Decimal("Planned Production Qty", required=True),
        "uom_id": fields.Many2One("uom", "UoM", required=True),
        "location_id": fields.Many2One("stock.location", "To Warehouse", required=True), 
        "bom_id": fields.Many2One("bom", "BoM", search=True), # XXX: deprecated
        "priority": fields.Selection([["high", "High"], ["medium", "Medium"], ["low", "Low"]], "Priority", search=True),
        "state": fields.Selection([["open", "Open"], ["closed", "Closed"]], "Status", search=True), # XXX: deprecated
        "description": fields.Text("Description"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "year": fields.Char("Year", sql_function=["year", "due_date"]),
        "actual_qty": fields.Decimal("Actual Production Qty", function="get_actual_qty"),
        "stock_moves": fields.One2Many("stock.move","related_id","Stock Movements"),
    }
    _order = "date desc,product_id.code desc"
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def name_get(self, ids, context={}, **kw):
        res=[]
        for obj in self.browse(ids):
            name="%s/%s"%(obj.date,obj.product_id.code)
            res.append([obj.id,name])
        return res

    def get_actual_qty(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            cond = [["state", "=", "done"], ["order_date", "=", obj.date], ["product_id", "=", obj.product_id.id]]
            total = 0
            for order in get_model("production.order").search_browse(cond):
                total += get_model("uom").convert(order.qty_received, order.uom_id.id, obj.uom_id.id)
            vals[obj.id] = total
        return vals

    def get_forecast_qtys(self,date):
        print("get_forecast_qtys",date)
        loc_ids=get_model("stock.location").search([["type","in",["internal","view"]]])
        prod_ids=get_model("product").search([["supply_method","=","production"]])
        print("prod_ids",prod_ids)
        qtys = get_total_qtys(date_to=date,prod_ids=prod_ids,loc_ids=loc_ids,states=["done","pending","approved","forecast"])
        print("qtys",qtys)
        bals={}
        for (prod_id,lot_id,loc_from_id,loc_to_id),qty in qtys.items():
            bals.setdefault((loc_from_id,prod_id),0)
            bals[(loc_from_id,prod_id)]-=qty
            bals.setdefault((loc_to_id,prod_id),0)
            bals[(loc_to_id,prod_id)]+=qty
        res=[]
        for (loc_id,prod_id),qty in bals.items():
            if loc_id not in loc_ids:
                continue
            res.append((prod_id,loc_id,qty))
        return res

    def update_plan(self,context={}):
        job_id=context.get("job_id")
        t=time.strftime("%Y-%m-%d")
        del_ids=self.search([["date",">=",t]])
        for obj in self.browse(del_ids):
            obj.stock_moves.delete()
        self.delete(del_ids)
        res=get_model("stock.location").search([["type","=","production"]])
        if not res:
            raise Exception("Production location not found")
        prod_loc_id=res[0]
        res=get_model("stock.journal").search([["type","=","production_plan"]])
        if not res:
            raise Exception("Production plan stock journal not found")
        journal_id=res[0]
        num_days=90
        d=datetime.today()
        for i in range(num_days):
            ds=d.strftime("%Y-%m-%d")
            print("-"*80)
            print("making production plan for %s (%d/%d)"%(ds,i+1,num_days))
            if job_id:
                if tasks.is_aborted(job_id):
                    return
            res=self.get_forecast_qtys(ds)
            for prod_id,loc_id,qty in res:
                prod=get_model("product").browse(prod_id)
                res=get_model("stock.orderpoint").get_min_qty(prod_id,loc_id)
                if qty>=res["min_qty"]:
                    continue
                order_qty=res["max_qty"]-qty
                mfg_date=(d-timedelta(days=prod.mfg_lead_time or 0)).strftime("%Y-%m-%d")
                vals={
                    "date": mfg_date,
                    "product_id": prod_id,
                    "location_id": loc_id,
                    "plan_qty": order_qty,
                    "uom_id": prod.uom_id.id,
                }
                plan_id=self.create(vals)
                vals={
                    "journal_id": journal_id,
                    "date": ds+" 00:00:00",
                    "product_id": prod_id,
                    "qty": order_qty,
                    "uom_id": prod.uom_id.id,
                    "location_from_id": prod_loc_id,
                    "location_to_id": loc_id,
                    "state": "pending",
                    "related_id": "production.plan,%s"%plan_id,
                }
                get_model("stock.move").create(vals)
                res=get_model("bom").search([["product_id","=",prod_id]])
                if not res:
                    raise Exception("BoM not found for product '%s'"%prod.name)
                bom_id=res[0]
                bom=get_model("bom").browse(bom_id)
                ratio=order_qty/bom.qty
                for line in bom.lines:
                    prod=line.product_id
                    qty=line.qty*ratio
                    vals={
                        "journal_id": journal_id,
                        "date": mfg_date+" 00:00:00",
                        "product_id": prod.id,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "location_from_id": line.location_id.id,
                        "location_to_id": prod_loc_id,
                        "state": "pending",
                        "related_id": "production.plan,%s"%plan_id,
                    }
                    get_model("stock.move").create(vals)
            d+=timedelta(days=1)

ProductionPlan.register()
