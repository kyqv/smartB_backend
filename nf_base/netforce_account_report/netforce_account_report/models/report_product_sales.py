# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

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
