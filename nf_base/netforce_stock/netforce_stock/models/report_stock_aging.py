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
from datetime import *
from dateutil.relativedelta import *
from netforce.access import get_active_company
from netforce.database import get_connection


def get_periods(date, period_days, num_periods):
    periods = []
    d0 = datetime.strptime(date, "%Y-%m-%d")
    date_from = d0 - timedelta(days=period_days - 1)
    date_to = d0 - timedelta(days=0)
    periods.append({
        "date_from": date_from.strftime("%Y-%m-%d"),
        "date_to": date_to.strftime("%Y-%m-%d"),
        "period_name": "%d-%d days" % ((d0 - date_to).days, (d0 - date_from).days),
    })
    for i in range(num_periods - 1):
        date_from = date_from - timedelta(days=period_days)
        date_to = date_to - timedelta(days=period_days)
        periods.append({
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
            "period_name": "%d-%d days" % ((d0 - date_to).days, (d0 - date_from).days),
        })
    return periods


def get_total_qtys(prod_id, loc_id, date_from, date_to, categ_id):
    print(">>> get_total_qtys",prod_id,loc_id,date_from,date_to,categ_id)
    db = get_connection()
    q = " SELECT " \
        " m.product_id,p.uom_id AS prod_uom_id,m.location_from_id,m.location_to_id,m.uom_id,SUM(m.qty) AS total_qty " \
        " FROM stock_move m " \
        " LEFT JOIN product p on m.product_id=p.id " \
        " WHERE m.state='done'"
    q_args = []
    if date_from:
        q += " AND m.date>=%s"
        q_args.append(date_from + " 00:00:00")
    if date_to:
        q += " AND m.date<=%s"
        q_args.append(date_to + " 23:59:59")
    if prod_id:
        q += " AND m.product_id=%s"
        q_args.append(prod_id)
    if loc_id:
        q += " AND (m.location_from_id=%s OR m.location_to_id=%s)"
        q_args += [loc_id, loc_id]
    if categ_id:
        q += " AND p.categ_id=%s"
        q_args.append(categ_id)
    company_id = get_active_company()
    if company_id:
        q += " AND m.company_id=%s"
        q_args.append(company_id)
    q += " GROUP BY m.product_id,p.uom_id,m.location_from_id,m.location_to_id,m.uom_id"
    res = db.query(q, *q_args)
    print("<<< get_total_qtys query done",prod_id,loc_id,date_from,date_to,categ_id)
    totals = {}
    for r in res:
        qty = get_model("uom").convert(r.total_qty,r.uom_id,r.prod_uom_id)
        k = (r.product_id, r.location_from_id, r.location_to_id)
        totals.setdefault(k, 0)
        totals[k] += qty
    print("<<< get_total_qtys all done",prod_id,loc_id,date_from,date_to,categ_id)
    return totals


class ReportStockAging(Model):
    _name = "report.stock.aging"
    _string="Stock Aging Report"
    _transient = True
    _fields = {
        "date": fields.Date("Date", required=True),
        "location_id": fields.Many2One("stock.location", "Location", on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product", on_delete="cascade"),
        "categ_id": fields.Many2One("product.categ", "Product Category", on_delete="cascade"),
        "period_days": fields.Integer("Period Days", required=True),
        "num_periods": fields.Integer("Number of Periods", required=True),
    }
    _defaults = {
        "date": lambda *a: date.today().strftime("%Y-%m-%d"),
        "period_days": 30,
        "num_periods": 3,
    }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date = params.get("date")
        if not date:
            return
        location_id = params.get("location_id")
        if location_id:
            location = get_model("stock.location").browse(location_id)
        else:
            location = None
        product_id = params.get("product_id")
        if product_id:
            product = get_model("product").browse(product_id)
        else:
            product = None
        categ_id = params.get("categ_id")
        period_days = params.get("period_days")
        if not period_days:
            return
        period_days = int(period_days)
        num_periods = params.get("num_periods")
        if not num_periods:
            return
        num_periods = int(num_periods)
        periods = get_periods(date, period_days, num_periods)
        older_date_to = (
            datetime.strptime(periods[-1]["date_from"], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        cur_qtys = get_total_qtys(product_id, location_id, None, date, categ_id)
        cur_prod_qtys={}
        for (prod_id, loc_from_id, loc_to_id), qty in cur_qtys.items():
            cur_prod_qtys.setdefault(prod_id,{})
            cur_prod_qtys[prod_id][(loc_from_id,loc_to_id)]=qty
        prod_locs = set([])
        for prod_id, loc_from_id, loc_to_id in cur_qtys:
            prod_locs.add((prod_id, loc_from_id))
            prod_locs.add((prod_id, loc_to_id))
        for period in periods:
            qtys = get_total_qtys(product_id, location_id, period["date_from"], period["date_to"], categ_id)
            prod_qtys={}
            for (prod_id, loc_from_id, loc_to_id), qty in qtys.items():
                prod_qtys.setdefault(prod_id,{})
                prod_qtys[prod_id][(loc_from_id,loc_to_id)]=qty
            period["prod_qtys"]=prod_qtys
        def get_balance_qty(prod_id, loc_id, prod_qtys, in_only=False):
            bal = 0
            qtys=prod_qtys.get(prod_id,{})
            for (loc_from_id, loc_to_id), qty in qtys.items():
                if loc_to_id == loc_id and loc_from_id != loc_id:
                    bal += qty
                elif not in_only and loc_from_id == loc_id and loc_to_id != loc_id:
                    bal -= qty
            return bal
        lines = []
        print("got qtys")
        loc_ids=[]
        prod_ids=[]
        for prod_id,loc_id in prod_locs:
            loc_ids.append(loc_id)
            prod_ids.append(prod_id)
        loc_ids=list(set(loc_ids))
        prod_ids=list(set(prod_ids))
        locs={}
        for loc in get_model("stock.location").browse(loc_ids):
            locs[loc.id]=loc
        prods={}
        for prod in get_model("product").browse(prod_ids):
            prods[prod.id]=prod
        for i,(prod_id, loc_id) in enumerate(prod_locs):
            #print("%d/%d"%(i,len(prod_locs)))
            if location_id and loc_id!=location_id:
                continue
            loc=locs[loc_id]
            if loc.type != "internal":
                continue
            prod = prods[prod_id]
            cur_qty = get_balance_qty(prod_id, loc_id, cur_prod_qtys)
            line = {
                "product_id": prod.id,
                "product_name": prod.name,
                "location_id": loc.id,
                "location_name": loc.name,
                "cur_qty": cur_qty,
                "periods": [],
            }
            remain_qty = cur_qty
            for period in periods:
                if remain_qty > 0:
                    in_qty = get_balance_qty(prod_id, loc_id, period["prod_qtys"], in_only=True)
                    qty = min(in_qty, remain_qty)
                    remain_qty -= qty
                else:
                    qty = 0
                line["periods"].append({
                    "date_from": period["date_from"],
                    "date_to": period["date_to"],
                    "qty": qty,
                })
            line["older_qty"] = max(0, remain_qty)
            lines.append(line)
        lines.sort(key=lambda l: (l["product_name"], l["location_name"]))
        for period in periods:
            del period["prod_qtys"]
        data = {
            "company_name": comp.name,
            "location_name": location and location.name or None,
            "product_name": product and product.name or None,
            "date": date,
            "periods": periods,
            "lines": lines,
            "older_date_to": older_date_to,
            "current_date_from": "2000-01-01",  # XXX
        }
        return data

ReportStockAging.register()
