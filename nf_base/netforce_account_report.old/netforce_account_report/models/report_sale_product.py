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
from datetime import *
from dateutil.relativedelta import *
from pprint import pprint
from netforce.access import get_active_company


class ReportSaleProduct(Model):
    _name = "report.sale.product"
    _transient = True
    _fields = {
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_report_data(self, ids, context={}):
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "total_qty": 0,
            "total_amount": 0,
        }
        db = get_connection()
        res = db.query(
            "SELECT l.product_id,p.name AS product_name,p.sale_price AS product_price,SUM(l.amount) AS amount,SUM(l.qty) AS qty FROM account_invoice_line l,account_invoice i,product p WHERE i.id=l.invoice_id AND p.id=l.product_id AND i.date>=%s AND i.date<=%s GROUP BY l.product_id,p.name,p.sale_price ORDER BY p.name", date_from, date_to)
        lines = []
        for r in res:
            line = r
            line["avg_price"] = line["amount"] / line["qty"] if line["qty"] else None
            lines.append(line)
            data["total_qty"] += line["qty"]
            data["total_amount"] += line["amount"]
        data["lines"] = lines
        data["total_avg_price"] = data["total_amount"] / data["total_qty"] if data["total_qty"] else None
        pprint(data)
        return data

ReportSaleProduct.register()
