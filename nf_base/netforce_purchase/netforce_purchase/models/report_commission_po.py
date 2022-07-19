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


class ReportCommissionPO(Model):
    _name = "report.commission.po"
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
        cond = [["date", ">=", date_from], ["date", "<=", date_to], ["purchase_type_id.commission_po", "=", True]]
        groups = {}
        for purch in get_model("purchase.order").search_browse(cond, order="date"):
            group = groups.get(purch.customer_id.id)
            if group is None:
                group = {
                    "customer": purch.customer_id.name or "N/A",
                    "lines": [],
                }
                groups[purch.customer_id.id] = group
            line = {
                "id": purch.id,
                "date": purch.date,
                "number": purch.number,
                "supplier": purch.contact_id.name,
                "number": purch.number,
                "amount_subtotal": purch.amount_subtotal,
                "commission_percent": purch.customer_id.commission_po_percent,  # XXX
                "commission_amount": purch.amount_subtotal * (purch.customer_id.commission_po_percent or 0) / 100,
            }
            group["lines"].append(line)
        groups = sorted(groups.values(), key=lambda g: g["customer"])
        for group in groups:
            totals = {}
            totals["amount_subtotal"] = sum(l["amount_subtotal"] or 0 for l in group["lines"])
            totals["commission_amount"] = sum(l["commission_amount"] or 0 for l in group["lines"])
            group["totals"] = totals
        totals = {}
        totals["amount_subtotal"] = sum(g["totals"]["amount_subtotal"] for g in groups)
        totals["commission_amount"] = sum(g["totals"]["commission_amount"] for g in groups)
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "groups": groups,
            "totals": totals,
        }
        return data

ReportCommissionPO.register()
