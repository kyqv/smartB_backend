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
from datetime import *
from dateutil.relativedelta import *
from netforce.access import get_active_company


class ReportReconcile(Model):
    _name = "report.reconcile"
    _transient = True
    _fields = {
        "account_id": fields.Many2One("account.account", "Account", condition=[["type", "in", ("bank", "cash", "cheque")]], required=True, on_delete="cascade"),
        "date_from": fields.Date("From Date", required=True),
        "date_to": fields.Date("To Date", required=True),
    }

    def default_get(self, field_names=None, context={}, **kw):
        account_id = context.get("account_id")
        if account_id:
            account_id = int(account_id)
        date_from = context.get("date_from")
        date_to = context.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return {
            "account_id": account_id,
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
        if not params.get("account_id"):
            return
        account_id = int(params.get("account_id"))
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        acc = get_model("account.account").browse(account_id, context={"date_to": date_to})
        acc_balance = acc.balance
        acc_unrec = get_model("account.account").browse(
            account_id, context={"date_to": date_to, "bank_rec_state": "not_reconciled"})
        unrec_paid_amt = acc_unrec.credit
        unrec_received_amt = acc_unrec.debit
        rec_paid = []
        condition = [["account_id", "=", account_id], ["move_id.state", "=", "posted"], ["move_id.date", ">=", date_from], [
            "move_id.date", "<=", date_to], ["state", "=", "reconciled"], ["credit", ">", 0]]
        for line in get_model("account.move.line").search_browse(condition, order="move_id.date,id"):
            vals = {
                "date": line.move_id.date,
                "description": line.description,
                "ref": line.move_id.number,
                "amount": line.credit - line.debit,
            }
            rec_paid.append(vals)
        rec_received = []
        condition = [["account_id", "=", account_id], ["move_id.state", "=", "posted"], ["move_id.date", ">=", date_from], [
            "move_id.date", "<=", date_to], ["state", "=", "reconciled"], ["debit", ">", 0]]
        for line in get_model("account.move.line").search_browse(condition, order="move_id.date,id"):
            vals = {
                "date": line.move_id.date,
                "description": line.description,
                "ref": line.move_id.number,
                "amount": line.debit - line.credit,
            }
            rec_received.append(vals)
        db = database.get_connection()
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "account_name": acc.name,
            "rec_paid": rec_paid,
            "total_rec_paid": sum([l["amount"] for l in rec_paid]),
            "rec_received": rec_received,
            "total_rec_received": sum([l["amount"] for l in rec_received]),
            "acc_balance": acc_balance,
            "unrec_paid_amt": unrec_paid_amt,
            "unrec_received_amt": unrec_received_amt,
            "st_balance": acc_balance + unrec_paid_amt - unrec_received_amt,
        }
        return data

ReportReconcile.register()
