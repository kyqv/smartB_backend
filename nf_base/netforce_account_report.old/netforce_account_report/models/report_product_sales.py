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
from pprint import pprint
from netforce.access import get_active_company


class ReportProductSales(Model):
    _name = "report.product.sales"
    _store = False
    _fields = {
        "product_id": fields.Many2One("product", "Product"),
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def default_get(self, field_names, context={}):
        defaults = {}
        if context.get("product_id"):
            defaults["product_id"] = int(context["product_id"])
        if context.get("date_from"):
            defaults["date_from"] = context["date_from"]
        if context.get("date_to"):
            defaults["date_to"] = context["date_to"]
        context["defaults"] = defaults
        vals = super(ReportProductSales, self).default_get(field_names, context)
        return vals

    def get_report_data(self, ids=None, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        product_id = int(params.get("product_id"))
        if not product_id:
            return
        product = get_model("product").browse(product_id)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        data = {
            "company_name": comp.name,
            "product_name": product.name,
            "date_from": date_from,
            "date_to": date_to,
            "total_qty": 0,
            "total_amount": 0,
        }
        condition = [["product_id", "=", product_id], [
            "invoice_id.date", ">=", date_from], ["invoice_id.date", "<=", date_to]]
        lines = get_model("account.invoice.line").search_read(
            condition, ["invoice_id", "invoice_date", "invoice_contact_id", "description", "qty", "unit_price", "amount"])
        data["lines"] = lines
        for line in lines:
            data["total_qty"] += line["qty"]
            data["total_amount"] += line["amount"]
        pprint(data)
        return data

ReportProductSales.register()
