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
from netforce import database
from netforce.database import get_connection
from netforce.utils import get_file_path
import time
from datetime import *
from pprint import pprint
from netforce.access import get_active_company
from . import utils


def get_past_months(num_months):
    months = []
    d = date.today()
    m = d.month
    y = d.year
    months.append((y, m))
    for i in range(num_months - 1):
        if (m > 1):
            m -= 1
        else:
            m = 12
            y -= 1
        months.append((y, m))
    return reversed(months)


def get_future_months(num_months):
    months = []
    d = date.today()
    m = d.month
    y = d.year
    months.append((y, m))
    for i in range(num_months - 1):
        if (m < 12):
            m += 1
        else:
            m = 1
            y += 1
        months.append((y, m))
    return months


class ReportSale(Model):
    _name = "report.sale"
    _store = False

    def sales_per_month(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT to_char(date,'YYYY-MM') AS month,SUM(amount_total_cur) as amount FROM sale_order WHERE state in ('confirmed','done') GROUP BY month")
        amounts = {}
        for r in res:
            amounts[r.month] = r.amount
        data = []
        months = get_past_months(6)
        for y, m in months:
            amt = amounts.get("%d-%.2d" % (y, m), 0)
            d = date(year=y, month=m, day=1)
            data.append((d.strftime("%B"), amt))
        return data

    def sales_per_product(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT p.name,SUM(l.amount_cur) as amount FROM sale_order_line l,sale_order o,product p WHERE p.id=l.product_id AND o.id=l.order_id AND o.state in ('confirmed','done') GROUP BY p.name ORDER BY amount DESC")
        data = []
        for r in res[:5]:
            data.append((r.name, r.amount))
        amt = 0
        for r in res[5:]:
            amt += r.amount or 0
        if amt > 0:
            data.append(("Other", amt))
        return data

    def sales_per_product_categ(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT c.name,SUM(l.amount_cur) as amount FROM sale_order_line l,sale_order o,product p,product_categ c WHERE c.id=p.categ_id AND p.id=l.product_id AND o.id=l.order_id AND o.state in ('confirmed','done') GROUP BY c.name ORDER BY amount DESC")
        data = []
        for r in res[:5]:
            data.append((r.name, r.amount))
        amt = 0
        for r in res[5:]:
            amt += r.amount or 0
        if amt > 0:
            data.append(("Other", amt))
        return data

    def sales_per_customer(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT c.name,SUM(o.amount_total) as amount FROM sale_order o,contact c WHERE c.id=o.contact_id AND o.state in ('confirmed','done') GROUP BY c.name ORDER BY amount DESC")
        data = []
        for r in res[:5]:
            data.append((r.name, r.amount))
        amt = 0
        for r in res[5:]:
            amt += r.amount or 0
        if amt > 0:
            data.append(("Other", amt))
        return data

    def opport_stage(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT s.name,SUM(o.amount*o.probability/100) AS amount,COUNT(*) AS num FROM sale_opportunity o,sale_stage s WHERE s.id=o.stage_id AND o.state in ('open','won') GROUP BY s.name")
        amounts = {}
        counts = {}
        for r in res:
            amounts[r.name] = r.amount or 0
            counts[r.name] = r.num
        data = []
        for stage in get_model("sale.stage").search_browse([]):
            amt = amounts.get(stage.name, 0)
            count = counts.get(stage.name, 0)
            #label="%s (%d)"%(stage.name,count)
            label = stage.name
            data.append((label, amt))
        return data

    def expected_revenue(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT date_trunc('month',o.date_close) AS month,SUM(o.amount*o.probability/100),COUNT(*) FROM sale_opportunity o WHERE o.state in ('open','won') GROUP BY month")
        amounts = {}
        months = get_future_months(6)
        last_month = "%d-%.2d" % months[-1]
        for r in res:
            if not r.month:
                continue
            m = r.month[:7]
            if m > last_month:
                amounts["future"] = r.sum
            else:
                amounts[m] = r.sum
        data = []
        for y, m in months:
            amt = amounts.get("%d-%.2d" % (y, m), 0)
            d = date(year=y, month=m, day=1)
            data.append((d.strftime("%b"), amt))
        data.append(("Future", amounts.get("future", 0)))
        return data

    def get_sales_per_day(self, context={}):
        db=database.get_connection()
        min_d=datetime.today().strftime("%Y-%m-01")
        q="SELECT date_trunc('day',date) AS day,SUM(amount_total) AS amount FROM sale_order WHERE date>=%s AND state IN ('confirmed','done')"
        args=[min_d]
        q+=" GROUP BY day ORDER BY day"
        res=db.query(q,*args)
        data_cur = []
        total=0
        for r in res:
            d=datetime.strptime(r.day[:10],"%Y-%m-%d")
            total+=r.amount
            data_cur.append([d.day, total])
        d=datetime.strptime(date.today().strftime("%Y-%m-01"),"%Y-%m-%d")-timedelta(days=1)
        d_to=d.strftime("%Y-%m-%d")
        d_from=d.strftime("%Y-%m-01")
        q="SELECT date_trunc('day',date) AS day,SUM(amount_total) AS amount FROM sale_order WHERE date>=%s AND date<=%s AND state IN ('confirmed','done')"
        args=[d_from,d_to]
        q+=" GROUP BY day ORDER BY day"
        res=db.query(q,*args)
        data_prev = []
        total=0
        for r in res:
            d=datetime.strptime(r.day[:10],"%Y-%m-%d")
            total+=r.amount
            data_prev.append([d.day, total])
        return [{
            "name": "This Month",
            "data": data_cur,
            "color": "blue",
        },{
            "name": "Previous Month",
            "data": data_prev,
            "color": "orange",
        }]

ReportSale.register()
