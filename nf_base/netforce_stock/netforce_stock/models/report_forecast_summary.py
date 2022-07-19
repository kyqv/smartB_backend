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
from netforce import database
from datetime import *
from dateutil.relativedelta import *
import time
import io
from pprint import pprint
from decimal import *

def get_total_qtys(prod_ids=None, loc_id=None, date_from=None, date_to=None, states=None, categ_ids=None):
    db = database.get_connection()
    q = "SELECT " \
        " m.product_id,m.lot_id,p.uom_id AS prod_uom_id,m.location_from_id,m.location_to_id,m.uom_id,m.state,SUM(m.qty) AS total_qty " \
        " FROM stock_move m " \
        " JOIN product p on m.product_id=p.id" \
        " LEFT JOIN stock_lot l on m.lot_id=l.id WHERE true"
    q_args = []
    if states:
        q+=" AND m.state IN %s"
        q_args.append(tuple(states))
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
    q += " GROUP BY m.product_id,p.uom_id,m.location_from_id,m.location_to_id,m.uom_id,m.state,m.lot_id"
    #print("q",q)
    #print("q_args",q_args)
    res = db.query(q, *q_args)
    totals = {}
    for r in res:
        qty = get_model("uom").convert(r.total_qty,r.uom_id,r.prod_uom_id)
        k = (r.product_id, r.lot_id, r.location_from_id, r.location_to_id, r.state)
        totals.setdefault(k, 0)
        totals[k] += qty
    return totals

class ReportForecastSummary(Model):
    _name = "report.forecast.summary"
    _transient = True
    _fields = {
        "date": fields.Date("Date", required=True),
        "forecast_days": fields.Integer("Forecast Days",required=True),
        "show_shelf_life": fields.Boolean("Show Shelf Life"),
        "order_only": fields.Boolean("Only show products to order"),
        "product_id": fields.Many2One("product", "Product", on_delete="cascade"),
    }
    _defaults = {
        "date": lambda *a: date.today().strftime("%Y-%m-%d"),
        "forecast_days": 180,
        "show_shelf_life": True,
    }

    def get_report_data(self, ids, context={}):
        print("forecast_summary.get_report_data")
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)

        date = params.get("date")
        if not date:
            return
        forecast_days = params.get("forecast_days") or 30
        order_only=params.get("order_only")

        totals=get_total_qtys(date_to=date)

        locations={}
        for loc in get_model("stock.location").search_browse([],context={"active_test":False}):
            locations[loc.id]=loc

        prod_lot_qtys={}
        for (prod_id, lot_id, loc_from_id, loc_to_id, state), qty in totals.items():
            lot_qtys=prod_lot_qtys.setdefault(prod_id,{})
            lot_qtys.setdefault(lot_id,0)
            loc_from=locations[loc_from_id]
            loc_to=locations[loc_to_id]
            if loc_from.type!="internal" and loc_to.type=="internal":
                if state=="done":
                    lot_qtys[lot_id]+=qty
            elif loc_from.type=="internal" and loc_to.type!="internal":
                if state=="done":
                    lot_qtys[lot_id]-=qty
        #print("prod_lot_qtys",prod_lot_qtys)
        all_prod_ids=prod_lot_qtys.keys()

        prod_sorted_lot_ids={}
        prod_lots={}
        for prod_id,lot_qtys in prod_lot_qtys.items():
            sorted_lot_ids=[lot_id for lot_id in lot_qtys.keys() if lot_id]
            lots={}
            for lot in get_model("stock.lot").browse(sorted_lot_ids):
                lots[lot.id]=lot
            prod_lots[prod_id]=lots
            sorted_lot_ids.sort(key=lambda lot_id: lots[lot_id].expiry_date or "9999-12-31")
            prod_sorted_lot_ids[prod_id]=sorted_lot_ids
        #print("prod_sorted_lot_ids",prod_sorted_lot_ids)

        def get_total_qty(prod_id,date,min_shelf_life=None):
            print("get_total_qty",prod_id,date,min_shelf_life)
            lots=prod_lots.get(prod_id,{})
            lot_qtys=prod_lot_qtys[prod_id]
            print("lot_qtys",lot_qtys)
            total_qty=0
            for lot_id,lot_qty in lot_qtys.items():
                lot=lots.get(lot_id)
                if lot and lot.expiry_date and lot.expiry_date<=date:
                    continue
                if min_shelf_life and not lot:
                    continue
                if min_shelf_life in ("50","75") and lot.life_50_date and lot.life_50_date<=date:
                    continue
                if min_shelf_life=="75" and lot.life_75_date and lot.life_75_date<=date:
                    continue
                total_qty+=lot_qty
            print("=> total_qty=%s"%total_qty)
            return total_qty

        def add_qty(prod_id,qty,lot):
            print("add_qty",prod_id,qty,lot.id)
            lots=prod_lots.setdefault(prod_id,{})
            lot_qtys=prod_lot_qtys[prod_id]
            lot_qtys.setdefault(lot.id,0)
            lot_qtys[lot.id]+=qty
            lots.setdefault(lot.id,lot)
            sorted_lot_ids=[lot_id for lot_id in lot_qtys.keys() if lot_id]
            sorted_lot_ids.sort(key=lambda lot_id: lots[lot_id].expiry_date or "9999-12-31")
            prod_sorted_lot_ids[prod_id]=sorted_lot_ids

        def remove_qty(prod_id,date,qty,min_shelf_life=None):
            print("remove_qty",prod_id,date,qty,min_shelf_life)
            lots=prod_lots.setdefault(prod_id,{})
            lot_qtys=prod_lot_qtys[prod_id]
            remain_qty=qty
            if None in lot_qtys:
                other_qty=lot_qtys[None]
                used_qty=min(remain_qty,other_qty)
                lot_qtys[None]-=used_qty
                remain_qty-=used_qty
                if remain_qty<=0:
                    return
            sorted_lot_ids=prod_sorted_lot_ids[prod_id]
            for lot_id in sorted_lot_ids:
                if lot_id not in lots:
                    continue
                lot=lots[lot_id]
                if lot.expiry_date and lot.expiry_date<=date:
                    return
                if min_shelf_life=="50" and lot.life_50_date<=date:
                    return
                elif min_shelf_life=="75" and lot.life_75_date<=date:
                    return
                lot_qty=lot_qtys[lot_id]
                used_qty=min(remain_qty,lot_qty)
                lot_qtys[lot_id]-=used_qty
                remain_qty-=used_qty
                if remain_qty<=0:
                    return

        lines=[]
        for product_id in all_prod_ids:
            if params.get("product_id") and params["product_id"]!=product_id:
                continue
            product=get_model("product").browse(product_id)
            min_qty=product.min_qty or 0
            min_qty_50=product.min_qty_50 or 0
            min_qty_75=product.min_qty_75 or 0
            max_qty=product.max_qty or 0
            lead_time=product.purchase_lead_time or 0

            cond=[["product_id","=",product_id],["date",">=",date],["state","in",["pending","confirmed"]]]
            date_moves={}
            for move in get_model("stock.move").search_browse(cond,order="date,id"):
                ds=move.date[:10]
                date_moves.setdefault(ds,[]).append(move)
            cond=[["product_id","=",product_id],["forecast_id.date_from",">=",date]]
            date_sales={}
            for line in get_model("sale.forecast.line").search_browse(cond,order="forecast_id.date_from,id"):
                ds=line.forecast_id.date_from
                date_sales.setdefault(ds,[]).append(line)

            d=datetime.strptime(date,"%Y-%m-%d")
            max_date=d+timedelta(days=forecast_days)
            current_qty=None
            min_qty_date=None
            order_date=None
            while d<=max_date:
                ds=d.strftime("%Y-%m-%d")
                for move in date_moves.get(ds,[]):
                    if move.location_from_id.type!="internal" and move.location_to_id.type=="internal":
                        add_qty(product_id,move.qty,move.lot_id)
                    #elif move.location_from_id.type=="internal" and move.location_to_id.type!="internal":
                    #    remove_qty(product_id,ds,move.qty,move.min_shelf_life)
                for line in date_sales.get(ds,[]):
                    remove_qty(product_id,ds,line.plan_qty,line.min_shelf_life)
                qty=get_total_qty(product_id,ds)
                if current_qty is None:
                    current_qty=qty
                qty_50=get_total_qty(product_id,ds,"50")
                qty_75=get_total_qty(product_id,ds,"75")
                print("-"*80)
                print("date=%s qty=%s qty_50=%s qty_75=%s"%(ds,qty,qty_50,qty_75))
                order_qty=0
                if qty<min_qty:
                    order_qty=max(order_qty,max_qty-qty)
                if min_qty_50 and qty_50<min_qty_50:
                    order_qty=max(order_qty,max_qty-qty_50)
                if min_qty_75 and qty_75<min_qty_75:
                    order_qty=max(order_qty,max_qty-qty_75)
                if order_qty:
                    min_qty_date=ds
                    order_date=(datetime.strptime(min_qty_date,"%Y-%m-%d")-timedelta(days=lead_time)).strftime("%Y-%m-%d")
                    break
                d+=timedelta(days=1)
            show_alert=False
            if order_date and order_date<=time.strftime("%Y-%m-%d"):
                show_alert=True
            min_qty_months=round((datetime.strptime(min_qty_date,"%Y-%m-%d")-datetime.strptime(date,"%Y-%m-%d")).days/Decimal(30),1) if min_qty_date else None
            line_vals={
                "prod_id": product.id,
                "prod_code": product.code,
                "prod_name": product.name,
                "current_qty": current_qty,
                "min_qty": min_qty,
                "min_qty_50": min_qty_50,
                "min_qty_75": min_qty_75,
                "min_qty_date": min_qty_date,
                "min_qty_months": min_qty_months,
                "lead_time": lead_time,
                "order_date": order_date,
                "max_qty": max_qty,
                "order_qty": order_qty,
                "show_alert": show_alert,
            }
            if order_only and not show_alert:
                continue
            lines.append(line_vals)

        return {
            "company_name": comp.name,
            "date": date,
            "lines": lines,
            "show_shelf_life": params.get("show_shelf_life"),
            "order_only": params.get("order_only"),
        }

ReportForecastSummary.register()
