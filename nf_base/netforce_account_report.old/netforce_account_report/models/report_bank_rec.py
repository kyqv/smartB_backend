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
import time
from netforce.access import get_active_company


class ReportBankRec(Model):
    _name = "report.bank.rec"
    _transient = True
    _fields = {
        "account_id": fields.Many2One("account.account", "Account", condition=[["type", "in", ("bank", "cash", "cheque")]], required=True, on_delete="cascade"),
        "date": fields.Date("Date", required=True),
    }

    def default_get(self, field_names=None, context={}, **kw):
        account_id = context.get("account_id")
        if account_id:
            account_id = int(account_id)
        date = context.get("date")
        if not date:
            date = time.strftime("%Y-%m-%d")
        return {
            "account_id": account_id,
            "date": date,
        }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        db = database.get_connection()
        if not params.get("account_id"):
            return
        account_id = int(params.get("account_id"))
        date = params.get("date")
        if not date:
            date = time.strftime("%Y-%m-%d")
        ctx = {
            "date_to": date,
        }
        acc = get_model("account.account").browse([account_id], context=ctx)[0]
        payments = []
        for obj in get_model("account.move.line").search_browse([["account_id", "=", account_id], ["state", "!=", "reconciled"], ["move_id.state", "=", "posted"], ["move_id.date", "<=", date]], order="move_id.date"):
            vals = {
                "date": obj.move_id.date,
                "description": obj.description,
                "ref": obj.move_id.number,
                "amount": obj.credit - obj.debit,
            }
            payments.append(vals)
        st_lines = []
        for obj in get_model("account.statement.line").search_browse([["statement_id.account_id", "=", account_id], ["state", "!=", "reconciled"], ["date", "<=", date]], order="date"):
            vals = {
                "date": obj.date,
                "description": obj.description,
                "ref": "",  # XXX
                "amount": obj.received - obj.spent,
            }
            st_lines.append(vals)
        data = {
            "company_name": comp.name,
            "date": date,
            "account_name": acc.name,
            "account_balance": acc.balance,
            "move_lines": payments,
            "total_move_lines": sum([p["amount"] for p in payments]),
            "statement_lines": st_lines,
            "total_statement_lines": sum([l["amount"] for l in st_lines]),
        }
        data["statement_balance"] = data["account_balance"] + data["total_move_lines"] + data["total_statement_lines"]
        return data

ReportBankRec.register()
