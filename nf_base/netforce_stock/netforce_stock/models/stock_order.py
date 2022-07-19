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
import time
from dateutil.relativedelta import *
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

class StockOrder(Model):
    _name = "stock.order"
    _fields = {
        "lines": fields.One2Many("stock.order.line","order_id","Lines"),
        "confirm_orders": fields.Boolean("Confirm Orders"),
    }

    def _get_lines(self,context={}):
        lines=self.get_product_order_qtys(context=context)
        return lines

    _defaults={
        "lines": _get_lines,
    }

    def get_product_order_qtys(self,context={}):
        print("StockOrder.get_product_order_qtys")
        plan_horizon=int(context.get("plan_horizon") or 0)
        print("plan_horizon",plan_horizon)
        date_to=(date.today()+timedelta(days=plan_horizon)).strftime("%Y-%m-%d") if plan_horizon else None
        print("getting qtys...")
        t0=time.time()
        prod_qtys=context.get("product_qtys")
        if prod_qtys:
            lines=[]
            for prod_id,qty in prod_qtys.items():
                prod_id=int(prod_id)
                prod=get_model("product").browse(prod_id)
                line_vals={
                    "product_id": prod.id,
                    "qty": qty,
                    "uom_id": prod.uom_id.id,
                    "date": time.strftime("%Y-%m-%d"),
                    "supply_method": prod.supply_method,
                    "supplier_id": prod.suppliers and prod.suppliers[0].supplier_id.id or None,
                }
                lines.append(line_vals)
            print("lines2",lines)
            return lines
        prod_ids=context.get("product_ids")
        if not prod_ids:
            return None
        res = get_total_qtys(prod_ids, None, None, date_to, ["done","pending","approved","forecast"], None)
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
        #print("qtys_horiz",qtys_horiz)
        min_qtys=self.get_min_qtys()
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
                if prod.purchase_uom_id and prod.purchase_uom_id.id!=prod.uom_id.id:
                    order_uom=prod.purchase_uom_id
                    if not prod.purchase_to_stock_uom_factor:
                        raise Exception("Missing purchase to stock UoM factor for product %s"%prod.code)
                    order_qty=req_qty/prod.purchase_to_stock_uom_factor
                    if prod.purchase_min_qty and order_qty<prod.purchase_min_qty:
                        order_qty=prod.purchase_min_qty
                    if prod.purchase_qty_multiple:
                        n=math.ceil(order_qty/prod.purchase_qty_multiple)
                        order_qty=n*prod.purchase_qty_multiple
                else:
                    order_uom=prod.uom_id
                    order_qty=req_qty
                if prod.purchase_min_qty and order_qty<prod.purchase_min_qty:
                    order_qty=prod.purchase_min_qty
                if prod.purchase_qty_multiple and order_qty%prod.purchase_qty_multiple!=0:
                    n=math.ceil(order_qty/prod.purchase_qty_multiple)
                    order_qty=n*prod.purchase_qty_multiple
            elif prod.supply_method=="production":
                order_uom=prod.uom_id
                order_qty=req_qty
                if prod.mfg_min_qty and order_qty<prod.mfg_min_qty:
                    order_qty=prod.mfg_min_qty
                if prod.mfg_qty_multiple and order_qty%prod.mfg_qty_multiple!=0:
                    n=math.ceil(order_qty/prod.mfg_qty_multiple)
                    order_qty=n*prod.mfg_qty_multiple
            else:
                order_uom=None
                order_qty=None
            line_vals={
                "product_id": prod.id,
                "qty": order_qty,
                "uom_id": order_uom.id,
                "date": time.strftime("%Y-%m-%d"),
                "supply_method": prod.supply_method,
                "supplier_id": prod.suppliers and prod.suppliers[0].supplier_id.id or None,
            }
            lines.append(line_vals)
        print("lines",lines)
        return lines

    def create_po(self,ids,context={}):
        obj=self.browse(ids[0])
        order_lines = {}
        for line in obj.lines:
            prod=line.product_id
            if line.supply_method!="purchase":
                continue
            supplier_id=line.supplier_id.id
            order_date=line.date
            if prod.purchase_lead_time is not None:
                due_date=(datetime.strptime(order_date,"%Y-%m-%d")+timedelta(days=prod.purchase_lead_time or 0)).strftime("%Y-%m-%d")
            else:
                due_date=None
            k=(supplier_id,order_date,due_date)
            order_lines.setdefault(k,[]).append(line.id)
        n=0
        for (supplier_id,order_date,due_date),line_ids in order_lines.items():
            vals={
                "contact_id": supplier_id,
                "date": order_date,
                "delivery_date": due_date,
                "lines": [],
            }
            for line in get_model("stock.order.line").browse(line_ids):
                prod=line.product_id
                if prod.purchase_uom_id and prod.purchase_uom_id.id!=prod.uom_id.id:
                    if not prod.purchase_to_stock_uom_factor:
                        raise Exception("Missing purchase to stock UoM factor for product %s"%prod.code)
                    qty_stock=line.qty*prod.purchase_to_stock_uom_factor
                else:
                    qty_stock=None
                loc_id=prod.locations[0].location_id.id if prod.locations else None
                if not loc_id:
                    loc_id=prod.categ_id.locations[0].location_id.id if prod.categ_id and prod.categ_id.locations else None
                if not loc_id:
                    raise Exception("Missing stock location for product %s"%prod.code)
                line_vals={
                    "product_id": prod.id,
                    "description": prod.description or prod.name,
                    "qty": line.qty,
                    "uom_id": line.uom_id.id,
                    "unit_price": prod.purchase_price or 0,
                    "qty_stock": qty_stock,
                    "location_id": loc_id,
                }
                vals["lines"].append(("create",line_vals))
            order_id=get_model("purchase.order").create(vals)
            if obj.confirm_orders:
                get_model("purchase.order").confirm([order_id])
            n+=1
        return {
            "num_orders": n,
        }

    def auto_create_purchase_orders(self,context={}):
        access.set_active_user(1)
        access.set_active_company(1) # XXX
        vals={
            "confirm_orders": True,
        }
        obj_id=self.create(vals)
        self.delete_planned_orders([obj_id])
        self.fill_products([obj_id])
        self.create_po([obj_id])

    def delete_planned_po(self,context={}):
        d=datetime.today().strftime("%Y-%m-%d")
        n=0
        for purch in get_model("purchase.order").search_browse([["date",">=",d]]):
            for pick in purch.pickings:
                pick.void()
                pick.delete()
            purch.to_draft()
            purch.delete()
            n+=1
        return {
            "num_orders": n,
        }

    def get_min_qtys(self,context={}):
        print("StockOrder.get_min_qtys")
        min_qtys={}
        for op in get_model("stock.orderpoint").search_browse([]):
            prod_id=op.product_id.id
            min_qtys.setdefault(prod_id,0)
            min_qtys[prod_id]+=op.min_qty
        print("min_qtys",min_qtys)
        return min_qtys

    def auto_create_production_orders(self,context={}):
        access.set_active_user(1)
        access.set_active_company(1) # XXX
        vals={
            "confirm_orders": True,
        }
        obj_id=self.create(vals)
        self.delete_planned_orders([obj_id])
        self.fill_products([obj_id])
        self.create_mo([obj_id])

    def delete_planned_mo(self,context={}):
        d=datetime.today().strftime("%Y-%m-%d")
        n=0
        for order in get_model("production.order").search_browse([["order_date",">=",d]]):
            if order.state in ("in_progress","done"):
                continue
            for pick in order.pickings:
                pick.void()
                pick.delete()
            order.to_draft()
            order.delete()
            n+=1
        return {
            "num_orders": n,
        }

    def create_mo(self,ids,context={}):
        print("StockOrder.create_mo",ids)
        obj=self.browse(ids[0])
        n=0
        for (i,line) in enumerate(obj.lines):
            if line.supply_method!="production":
                continue
            prod = line.product_id
            print("#"*80)
            print("#"*80)
            print("#"*80)
            print("Creating MO for product %s (%s/%s)"%(prod.name,i,len(obj.lines)))
            t0=time.time()
            res=get_model("bom").search([["product_id","=",prod.id]])
            if not res:
                raise Exception("BoM not found for product '%s'" % prod.name)
            bom_id = res[0]
            bom = get_model("bom").browse(bom_id)
            loc_id = bom.location_id.id
            if not loc_id:
                raise Exception("Missing FG location in BoM %s" % bom.number)
            routing = bom.routing_id
            if not routing:
                raise Exception("Missing routing in BoM %s" % bom.number)
            loc_prod_id = routing.location_id.id
            if not loc_prod_id:
                raise Exception("Missing production location in routing %s" % routing.number)
            uom = prod.uom_id
            order_date=line.date
            #if not prod.mfg_lead_time:
            #    raise Exception("Missing manufacturing lead time in product %s"%prod.code) # XXX: default to 1
            due_date=(datetime.strptime(order_date,"%Y-%m-%d")+timedelta(days=prod.mfg_lead_time or 1)).strftime("%Y-%m-%d") # XXX: -1
            order_vals = {
                "product_id": prod.id,
                "qty_planned": line.qty,
                "uom_id": line.uom_id.id,
                "bom_id": bom_id,
                "routing_id": routing.id,
                "production_location_id": loc_prod_id,
                "location_id": loc_id,
                "order_date": order_date,
                "due_date": due_date,
                "state": "waiting_confirm",
            }
            order_id = get_model("production.order").create(order_vals)
            get_model("production.order").create_components([order_id])
            get_model("production.order").create_operations([order_id])
            if obj.confirm_orders:
                get_model("production.order").confirm([order_id])
                get_model("production.order").in_progress([order_id])
            t1=time.time()
            print("==> MO created in %.2f s"%(t1-t0))
            n+=1
        return {
            "num_orders": n,
        }

    def delete_planned_orders(self,ids,context={}):
        res=self.delete_planned_po()
        num_po=res["num_orders"]
        self.delete_planned_mo()
        num_mo=res["num_orders"]
        return {
            "flash": "%d purchase orders and %s production orders deleted"%(num_po,num_mo),
        }

    def create_orders(self,ids,context={}):
        print("create_orders",ids)
        obj=self.browse(ids[0])
        res=obj.create_po()
        num_po=res["num_orders"]
        res=obj.create_mo()
        num_mo=res["num_orders"]
        msg="Stock ordering: %d purchase orders and %s production orders created"%(num_po,num_mo)
        return {
            "flash": msg,
        }

StockOrder.register()
