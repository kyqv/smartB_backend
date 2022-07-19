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
from netforce.database import get_connection
from netforce.access import get_active_company


class ReportCustInv(Model):
    _name = "report.cust.inv"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Waiting Approval"), ("waiting_payment", "Waiting Payment"), ("paid", "Paid"), ("voided", "Voided")], "Status"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        contact_id = defaults.get("contact_id")
        state = defaults.get("state")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return {
            "date_from": date_from,
            "date_to": date_to,
            "contact_id": contact_id,
            "state": state,
        }

    def get_report_data(self, ids, context={}):
        settings = get_model("settings").browse(1)
        company_id = get_active_company()
        company = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        contact_id = params.get("contact_id")
        state = params.get("state")
        lines = []
        cond = [["type", "=", "out"]]
        if date_from:
            cond.append([["date", ">=", date_from]])
        if date_to:
            cond.append([["date", "<=", date_to]])
        if contact_id:
            cond.append([["contact_id", "=", contact_id]])
        if state:
            cond.append([["state", "=", state]])
        for inv in get_model("account.invoice").search_browse(cond, order="date"):
            line_vals = {
                "id": inv.id,
                "number": inv.number,
                "ref": inv.ref,
                "contact_name": inv.contact_id.name,
                "date": inv.date,
                "due_date": inv.due_date,
                "amount_total": inv.amount_total,
                "amount_paid": inv.amount_paid,
                "amount_due": inv.amount_due,
                "state": inv.state,  # XXX
            }
            lines.append(line_vals)
        data = {
            "company_name": company.name,
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
            "total_invoice": sum([l["amount_total"] for l in lines]),
            "total_paid": sum([l["amount_paid"] for l in lines]),
            "total_due": sum([l["amount_due"] for l in lines]),
        }
        return data

ReportCustInv.register()
