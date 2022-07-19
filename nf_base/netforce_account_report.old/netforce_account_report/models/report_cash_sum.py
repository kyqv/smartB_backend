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


class ReportCashSum(Model):
    _name = "report.cash.sum"
    _transient = True
    _fields = {
        "date_from": fields.Date("Date From"),
        "date_to": fields.Date("Date To"),
        "report_action": fields.Json("Report Action", function="get_action"),
    }

    def get_default_action(self, context={}):
        return {
            "name": "report_cash_sum",
        }

    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
        "report_action": get_default_action,
    }

    def get_action(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {}
        vals[obj.id] = {
            "name": "report_cash_sum",
            "context": {
                "date_from": obj.date_from,
                "date_to": obj.date_to,
            }
        }
        return vals

    def run_report(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "report_cash_sum_page",
                "active_id": obj.id,
            }
        }

    def export_cash_sum(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "report_cash_sum_xls",
                "date_from": obj.date_from,
                "date_to": obj.date_to,
            }
        }

    def get_data(self, context={}):
        date_from = context.get("date_from")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        date_from_min1 = (datetime.strptime(date_from, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = context.get("date_to")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        bank_ids = get_model("account.account").search([["type", "=", "bank"]])
        cash_open = 0
        for obj in get_model("account.account").read(bank_ids, ["balance"], context={"date_to": date_from_min1}):
            cash_open += obj["balance"]
        cash_close = 0
        for obj in get_model("account.account").read(bank_ids, ["balance"], context={"date_to": date_to}):
            cash_close += obj["balance"]
        db = database.get_connection()
        res = db.query(
            "SELECT a.id,a.name,sum(l.debit-l.credit) AS amount FROM account_move_line l,account_account a WHERE l.move_id IN (SELECT DISTINCT m.id FROM account_move_line l,account_move m,account_account a WHERE m.state='posted' AND m.date>=%s AND m.date<=%s AND m.id=l.move_id AND a.id=l.account_id AND a.type='bank') AND a.id=l.account_id AND a.type!='bank' AND l.reconcile_id IS NULL GROUP BY a.id ORDER BY a.name", date_from, date_to)
        accounts = {}
        for r in res:
            accounts[r.id] = {
                "id": r.id,
                "name": r.name,
                "amount": r.amount,
            }
        res = db.query(
            "SELECT a4.id as account_id,a4.name,SUM(l2.debit*(l4.credit-l4.debit)/(l3.debit-l3.credit)) as debit,SUM(l2.credit*(l4.credit-l4.debit)/(l3.debit-l3.credit)) as credit FROM account_move_line l2,account_account a2,account_move_line l3,account_move_line l4,account_account a4 WHERE l2.move_id IN (SELECT DISTINCT m1.id FROM account_move_line l1,account_move m1,account_account a1 WHERE m1.state='posted' AND m1.date>=%s AND m1.date<=%s AND m1.id=l1.move_id AND a1.id=l1.account_id AND a1.type='bank') AND a2.id=l2.account_id AND a2.type!='bank' AND l2.reconcile_id=l3.reconcile_id AND l3.id!=l2.id AND l4.move_id=l3.move_id AND l4.id!=l3.id AND a4.id=l4.account_id AND a4.type!='bank' GROUP BY a4.id", date_from, date_to)
        for r in res:
            acc = accounts.setdefault(r.account_id, {
                "id": r.account_id,
                "name": r.name,
                "amount": 0,
            })
            acc["amount"] += r.debit - r.credit
        lines = []
        total = 0
        for acc in sorted(accounts.values(), key=lambda a: a["name"]):
            line = {
                "type": "account",
                "id": acc["id"],
                "string": acc["name"],
                "amount": -acc["amount"],
                "padding": 10,
            }
            lines.append(line)
            total -= acc["amount"]
        line = {
            "type": "group_footer",
            "string": "Net Cash Movement",
            "amount": total,
            "separator": "double",
        }
        lines.append(line)
        data = {
            "date_from": date_from,
            "date_to": date_to,
            "col0": date_to,
            "company_name": context["company_name"],
            "cash_open": cash_open,
            "cash_move": cash_close - cash_open,
            "cash_close": cash_close,
            "lines": lines,
        }
        return data

ReportCashSum.register()
