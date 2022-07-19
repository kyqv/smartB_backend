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
from netforce import database
from netforce.access import get_active_company


class ReportSaleProfit(Model):
    _name = "report.sale.profit"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return {
            "date_from": date_from,
            "date_to": date_to,
        }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        lines = []
        cond = [["date", ">=", date_from], ["date", "<=", date_to]]
        for sale in get_model("sale.order").search_browse(cond, order="date"):
            line = {
                "id": sale.id,
                "date": sale.date,
                "number": sale.number,
                "customer": sale.contact_id.name,
                "sale": sale.number,
                "amount_subtotal": sale.amount_subtotal,
                "est_cost_total": sale.est_cost_total,
                "est_profit": sale.est_profit,
                "est_profit_percent": sale.est_profit_percent,
                "act_cost_total": sale.act_cost_total,
                "act_profit": sale.act_profit,
                "act_profit_percent": sale.act_profit_percent,
            }
            lines.append(line)
        totals = {}
        totals["amount_subtotal"] = sum(l["amount_subtotal"] or 0 for l in lines)
        totals["est_cost_total"] = sum(l["est_cost_total"] or 0 for l in lines)
        totals["est_profit"] = sum(l["est_profit"] or 0 for l in lines)
        totals["est_profit_percent"] = totals["est_profit"] * 100 / \
            totals["amount_subtotal"] if totals["amount_subtotal"] else None
        totals["act_cost_total"] = sum(l["act_cost_total"] or 0 for l in lines)
        totals["act_profit"] = sum(l["act_profit"] or 0 for l in lines)
        totals["act_profit_percent"] = totals["act_profit"] * 100 / \
            totals["amount_subtotal"] if totals["amount_subtotal"] else None
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
            "totals": totals,
        }
        return data

ReportSaleProfit.register()
