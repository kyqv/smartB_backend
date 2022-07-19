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


class ReportAccountPurchase(Model):
    _name = "report.account.purchase"
    _transient = True
    _fields = {
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
        "contact_id": fields.Many2One("contact", "Contact"),
        "account_id": fields.Many2One("account.account", "Account", condition=[["type", "in", ["cost_sales", "expense", "other_expense"]]]),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
        "group_by": "contact",
    }

    def get_report_data(self, ids, context={}):
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        settings = get_model("settings").browse(1)
        date_from = params["date_from"]
        date_to = params["date_to"]
        contact_id = params.get("contact_id")
        account_id = params.get("account_id")
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
        }
        cond = [["account_id.type", "in", ["cost_sales", "expense", "other_expense"]],
               ["move_id.date", ">=", date_from], ["move_id.date", "<=", date_to]]
        if contact_id:
            cond.append(["contact_id", "=", contact_id])
        if account_id:
            cond.append(["account_id", "=", account_id])
        groups = {}
        for obj in get_model("account.move.line").search_browse(cond, order="move_id.date"):
            line_vals = {
                "id": obj.id,
                "date": obj.move_id.date,
                "number": obj.move_id.number,
                "description": obj.description,
                "account_id": obj.account_id.id,
                "account_code": obj.account_id.code,
                "account_name": obj.account_id.name,
                "amount": obj.debit - obj.credit,
            }
            contact_id = obj.contact_id.id
            if contact_id in groups:
                group = groups[contact_id]
            else:
                group = {
                    "contact_id": contact_id,
                    "contact_name": obj.contact_id.name,
                    "lines": [],
                }
                groups[contact_id] = group
            group["lines"].append(line_vals)
        data["groups"] = sorted(groups.values(), key=lambda g: g["contact_name"] or "")
        for group in data["groups"]:
            group["total"] = sum([l["amount"] for l in group["lines"]])
        pprint(data)
        return data

ReportAccountPurchase.register()
