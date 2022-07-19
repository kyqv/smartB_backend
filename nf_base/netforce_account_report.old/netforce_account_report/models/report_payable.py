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
import time
from netforce.access import get_active_company


def js_time(d):
    return time.mktime(d.timetuple()) * 1000


class ReportPayable(Model):
    _name = "report.payable"
    _store = False

    def money_out(self, context={}):
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        db = get_connection()
        res = db.query(
            "SELECT COALESCE(l.due_date,l.move_date) AS due_date,SUM(l.credit-l.debit) as amount FROM account_move_line l JOIN account_account a ON a.id=l.account_id LEFT JOIN account_reconcile r ON r.id=l.reconcile_id WHERE l.move_state='posted' AND a.type='payable' AND l.reconcile_id IS NULL AND a.company_id IN %s GROUP BY COALESCE(l.due_date,l.move_date)", tuple(company_ids))
        amounts = {}
        for r in res:
            amounts[r.due_date] = r.amount
        chart_data=[]
        d0 = date.today()
        d1 = d0 + timedelta(days=60)
        d = d0
        while d < d1:
            ds = d.strftime("%Y-%m-%d")
            chart_data.append((js_time(d), amounts.get(ds, 0)))
            d += timedelta(days=1)
        data = {
            "chart_data": chart_data,
        }
        res = db.get(
            "SELECT count(*) AS count,SUM(amount_total_cur) AS amount FROM account_invoice WHERE type='in' AND inv_type='invoice' AND state='draft' AND company_id IN %s", tuple(company_ids))
        if res:
            data["draft_count"] = res.count
            data["draft_amount"] = res.amount or 0
        res = db.get(
            "SELECT count(*) AS count,SUM(amount_total_cur) AS amount FROM account_invoice WHERE type='in' AND inv_type='invoice' AND state='waiting_payment' AND due_date<now() AND company_id IN %s", tuple(company_ids))
        if res:
            data["overdue_count"] = res.count
            data["overdue_amount"] = res.amount or 0
        return data

    def payable_status(self, context={}):
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        data = {}
        for st in ("draft", "waiting_approval", "waiting_payment"):
            data[st] = {
                "count": 0,
                "amount": 0,
            }
        db = get_connection()
        res = db.query(
            "SELECT state,COUNT(*) as count,SUM(amount_due_cur) as amount FROM account_invoice WHERE type='in' AND inv_type='invoice' AND company_id IN %s GROUP BY state", tuple(company_ids))
        for r in res:
            data[r["state"]] = {
                "count": r["count"],
                "amount": r["amount"],
            }
        return data

ReportPayable.register()
