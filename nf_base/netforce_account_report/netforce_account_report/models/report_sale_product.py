# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

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
