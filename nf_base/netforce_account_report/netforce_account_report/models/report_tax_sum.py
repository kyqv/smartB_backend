# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *
from netforce import database
from netforce.access import get_active_company


class ReportTaxSum(Model):
    _name = "report.tax.sum"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "by_rate": fields.Boolean("Show by Tax Rate"),
        "by_comp": fields.Boolean("Show by Tax Component"),
    }

    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
        "by_comp": True,
    }

    def get_report_data(self, ids=None, context={}):
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        date_to = params.get("date_to")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "by_rate": params.get("by_rate"),
            "by_comp": params.get("by_comp"),
        }
        db = database.get_connection()
        if params.get("by_comp"):
            res = db.query("SELECT c.id AS comp_id,c.name AS comp_name,c.rate AS comp_rate,r.name AS rate_name,SUM(l.credit-l.debit) AS tax_total,SUM(l.tax_base*sign(l.credit-l.debit)) AS base_total FROM account_move_line l,account_move m,account_tax_component c,account_tax_rate r WHERE m.id=l.move_id AND m.state='posted' AND m.date>=%s AND m.date<=%s AND c.id=l.tax_comp_id AND r.id=c.tax_rate_id AND m.company_id IN %s GROUP BY comp_id,comp_name,comp_rate,rate_name ORDER BY comp_name,rate_name",
                           date_from, date_to, tuple(company_ids))
            data["comp_taxes"] = [dict(r) for r in res]
        if params.get("by_rate"):
            res = db.query("SELECT c.id AS comp_id,c.name AS comp_name,c.rate AS comp_rate,r.name AS rate_name,SUM(l.credit-l.debit) AS tax_total,SUM(l.tax_base*sign(l.credit-l.debit)) AS base_total FROM account_move_line l,account_move m,account_tax_component c,account_tax_rate r WHERE m.id=l.move_id AND m.state='posted' AND m.date>=%s AND m.date<=%s AND c.id=l.tax_comp_id AND r.id=c.tax_rate_id AND m.company_id IN %s GROUP BY comp_id,comp_name,comp_rate,rate_name ORDER BY rate_name,comp_name",
                           date_from, date_to, tuple(company_ids))
            data["rate_taxes"] = [dict(r) for r in res]
        return data

ReportTaxSum.register()
