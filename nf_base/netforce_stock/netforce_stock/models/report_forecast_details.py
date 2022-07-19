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
import base64
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
except:
    print("WARNING: failed to import matplotlib")


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

def get_svg(date,product_id,forecast_days,show_shelf_life=False):
    product=get_model("product").browse(product_id)
    locations={}
    for loc in get_model("stock.location").search_browse([]):
        locations[loc.id]=loc

    totals=get_total_qtys(prod_ids=[product_id],date_to=date)
    lot_qtys={}
    for (prod_id, lot_id, loc_from_id, loc_to_id, state), qty in totals.items():
        lot_qtys.setdefault(lot_id,0)
        loc_from=locations[loc_from_id]
        loc_to=locations[loc_to_id]
        if loc_from.type!="internal" and loc_to.type=="internal":
            if state=="done":
                lot_qtys[lot_id]+=qty
        elif loc_from.type=="internal" and loc_to.type!="internal":
            if state=="done":
                lot_qtys[lot_id]-=qty
    print("lot_qtys",lot_qtys)
    global sorted_lot_ids
    sorted_lot_ids=[lot_id for lot_id in lot_qtys.keys() if lot_id]
    lots={}
    for lot in get_model("stock.lot").browse(sorted_lot_ids):
        lots[lot.id]=lot
    sorted_lot_ids.sort(key=lambda lot_id: lots[lot_id].expiry_date or "9999-12-31")
    print("sorted_lot_ids",sorted_lot_ids)

    def get_total_qty(date,min_shelf_life=None):
        print("get_total_qty",date,min_shelf_life)
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

    def add_qty(qty,lot):
        print("add_qty",qty,lot.id)
        lot_qtys.setdefault(lot.id,0)
        lot_qtys[lot.id]+=qty
        lots.setdefault(lot.id,lot)
        global sorted_lot_ids
        sorted_lot_ids=[lot_id for lot_id in lot_qtys.keys() if lot_id]
        sorted_lot_ids.sort(key=lambda lot_id: lots[lot_id].expiry_date or "9999-12-31")

    def remove_qty(date,qty,min_shelf_life=None):
        print("remove_qty",date,qty,min_shelf_life)
        remain_qty=qty
        if None in lot_qtys:
            other_qty=lot_qtys[None]
            used_qty=min(remain_qty,other_qty)
            lot_qtys[None]-=used_qty
            remain_qty-=used_qty
            if remain_qty<=0:
                return
        for lot_id in sorted_lot_ids:
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

    dates=[]
    qtys=[]
    qtys_50=[]
    qtys_75=[]

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
    print("date_sales",date_sales);

    d=datetime.strptime(date,"%Y-%m-%d")
    max_date=d+timedelta(days=forecast_days)
    while d<=max_date:
        ds=d.strftime("%Y-%m-%d")
        for move in date_moves.get(ds,[]):
            if move.location_from_id.type!="internal" and move.location_to_id.type=="internal":
                add_qty(move.qty,move.lot_id)
            #elif move.location_from_id.type=="internal" and move.location_to_id.type!="internal":
            #    remove_qty(ds,move.qty,move.min_shelf_life)
        for line in date_sales.get(ds,[]):
            remove_qty(ds,line.plan_qty,line.min_shelf_life)
        dates.append(d)
        qty=get_total_qty(ds)
        qtys.append(float(qty))
        qty_50=get_total_qty(ds,"50")
        qtys_50.append(float(qty_50))
        qty_75=get_total_qty(ds,"75")
        qtys_75.append(float(qty_75))
        d+=timedelta(days=1)

    print("dates",dates)
    print("qtys",qtys)
    print("qtys_50",qtys_50)
    print("qtys_75",qtys_75)

    if len(dates)>1:
        min_qty=float(product.min_qty or 0)
        min_qty_50=float(product.min_qty_50 or 0)
        min_qty_75=float(product.min_qty_75 or 0)
        max_qty=float(product.max_qty or 0)
        ymax=max(qtys)
        if max_qty and max_qty>ymax:
            ymax=max_qty
        min_qty_date=None
        for i in range(len(qtys)):
            qty=qtys[i]
            if qty<min_qty:
                min_qty_date=dates[i]
                break
            if min_qty_50:
                qty=qtys_50[i]
                if qty<min_qty_50:
                    min_qty_date=dates[i]
                    break
            if min_qty_75:
                qty=qtys_75[i]
                if qty<min_qty_75:
                    min_qty_date=dates[i]
                    break
        fig, ax = plt.subplots(figsize=(12,4))
        ax.plot_date(dates,qtys,"-",label="Forecast Qty",color="b")
        ax.fill_between(dates,qtys,facecolor="blue",alpha=0.1)
        if show_shelf_life:
            ax.plot_date(dates,qtys_50,"-",color="b")
            ax.plot_date(dates,qtys_75,"-",color="b")
            ax.fill_between(dates,qtys_50,facecolor="blue",alpha=0.2)
            ax.fill_between(dates,qtys_75,facecolor="blue",alpha=0.4)
            if min_qty_50:
                ax.axhline(y=min_qty_50,color="orange",label="Min Qty Life 50%")
            if min_qty_75:
                ax.axhline(y=min_qty_75,color="ywllow",label="Min Qty Life 75%")
        ax.fill_between(dates,qtys,min_qty,facecolor="red",alpha=0.3,where=[q<=min_qty for q in qtys],interpolate=True) # XXX
        ax.set_ylim(ymin=0,ymax=ymax*1.1)
        ax.grid(True)
        if not show_shelf_life:
            ax.axhline(y=min_qty,color="r",label="Min Qty")
        ax.axhline(y=max_qty,color="g",label="Max Qty")
        if min_qty_date:
            ax.axvline(x=min_qty_date,color="r")
            lead_days=product.purchase_lead_time
            if lead_days:
                order_date=min_qty_date-timedelta(days=lead_days)
                ax.axvline(x=order_date,color="orange",label="Order Date")
        fmt = mdates.DateFormatter('%a, %d %b')
        ax.xaxis.set_major_formatter(fmt)
        fig.autofmt_xdate(bottom=0.2, rotation=30, ha='right')
        ax.set_ylabel("Quantity")
        ax.legend()
        
        img_data = io.StringIO()
        fig.savefig(img_data,format="svg")
        svg_data=img_data.getvalue()
        open("/tmp/plot.svg","w").write(svg_data)
    else:
        svg_data=None
    return svg_data


class ReportForecastDetails(Model):
    _name = "report.forecast.details"
    _transient = True
    _fields = {
        "date": fields.Date("Date", required=True),
        "product_id": fields.Many2One("product", "Product", on_delete="cascade", required=True),
        "forecast_days": fields.Integer("Forecast Days",required=True),
        "show_shelf_life": fields.Boolean("Show Shelf Life"),
    }
    _defaults = {
        "date": lambda *a: date.today().strftime("%Y-%m-%d"),
        "forecast_days": 120,
        "show_shelf_life": True,
    }

    def get_report_data(self, ids, context={}):
        print("forecast_details.get_report_data")
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)

        date = params.get("date")
        if not date:
            return
        product_id = params.get("product_id")
        if not product_id:
            return
        product=get_model("product").browse(product_id)

        svg_data=get_svg(date,product_id,params.get("forecast_days") or 30,params.get("show_shelf_life"))

        return {
            "company_name": comp.name,
            "date": date,
            "product_code": product.code,
            "product_name": product.name,
            "svg_data": svg_data,
            "svg_data_base64": base64.b64encode(svg_data.encode("utf-8")).decode("utf-8"),
        }

ReportForecastDetails.register()
