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
import time
from datetime import *
from netforce.access import get_active_company


def get_months(num_months):
    months = []
    d = date.today()
    m = d.month
    y = d.year
    months.append((y, m))
    for i in range(num_months - 1):
        if (m > 1):
            m -= 1
        else:
            m = 12
            y -= 1
        months.append((y, m))
    months.reverse()
    return months


class ReportReceivable(Model):
    _name = "report.receivable"
    _store = False

    def money_in(self, context={}):
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        db = get_connection()
        res = db.query(
            "SELECT to_char(COALESCE(l.due_date,l.move_date),'YYYY-MM') AS month,SUM(l.debit-l.credit) as amount FROM account_move_line l JOIN account_account a ON a.id=l.account_id LEFT JOIN account_reconcile r ON r.id=l.reconcile_id WHERE l.move_state='posted' AND a.type='receivable' AND l.reconcile_id IS NULL AND a.company_id IN %s GROUP BY month", tuple(company_ids))
        amounts = {}
        for r in res:
            amounts[r.month] = r.amount
        months = get_months(4)
        month_start = "%d-%.2d" % (months[0][0], months[0][1])
        month_stop = "%d-%.2d" % (months[-1][0], months[-1][1])
        amt_older = 0
        amt_future = 0
        chart_data=[]
        for month, amt in amounts.items():
            if month < month_start:
                amt_older += amt
            elif month > month_stop:
                amt_future += amt
        chart_data.append(("Older",amt_older))
        for y, m in months:
            d = date(year=y, month=m, day=1)
            amt = amounts.get("%d-%.2d" % (y, m), 0)
            chart_data.append((d.strftime("%B"),amt))
        chart_data.append(("Future",amt_future))
        data = {
            "chart_data": chart_data,
        }
        res = db.get(
            "SELECT count(*) AS count,SUM(amount_total_cur) AS amount FROM account_invoice WHERE type='out' AND inv_type='invoice' AND state='draft' AND company_id IN %s", tuple(company_ids))
        if res:
            data["draft_count"] = res.count
            data["draft_amount"] = res.amount or 0
        res = db.get(
            "SELECT count(*) AS count,SUM(amount_due_cur) AS amount FROM account_invoice WHERE type='out' AND inv_type='invoice' AND state='waiting_payment' AND due_date<now() AND company_id IN %s", tuple(company_ids))
        if res:
            data["overdue_count"] = res.count
            data["overdue_amount"] = res.amount or 0
        return data

    def receivable_status(self, context={}):
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
            "SELECT state,COUNT(*) as count,SUM(amount_due_cur) AS amount FROM account_invoice WHERE type='out' AND inv_type='invoice' AND company_id IN %s GROUP BY state", tuple(company_ids))
        for r in res:
            data[r["state"]] = {
                "count": r["count"],
                "amount": r["amount"],
            }
        return data

    def top_debtors(self, context={}):
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        db = get_connection()
        res = db.query(
            "SELECT p.id AS contact_id,p.name AS contact_name,SUM(amount_due_cur) AS amount_due,SUM(CASE WHEN i.due_date<now()::date THEN amount_due_cur ELSE 0 END) AS amount_overdue FROM account_invoice i JOIN contact p ON p.id=i.contact_id WHERE i.type='out' AND i.inv_type='invoice' AND i.state='waiting_payment' AND i.company_id IN %s GROUP BY p.id,p.name ORDER BY amount_due DESC LIMIT 10", tuple(company_ids))
        data = [dict(r) for r in res]
        return data

    def debtor_exposure(self, context={}):
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        db = get_connection()
        res = db.query(
            "SELECT p.id AS contact_id,p.name AS contact_name,SUM(amount_due_cur) AS amount_due FROM account_invoice i JOIN contact p ON p.id=i.contact_id WHERE i.type='out' AND i.inv_type='invoice' AND i.state='waiting_payment' AND i.company_id IN %s GROUP BY p.id,p.name ORDER BY amount_due DESC LIMIT 10", tuple(company_ids))
        data = [(r.contact_name, r.amount_due) for r in res]
        return data

ReportReceivable.register()
