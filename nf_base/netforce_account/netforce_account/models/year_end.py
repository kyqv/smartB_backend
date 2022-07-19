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
import datetime


class YearEnd(Model):
    _name = "year.end"
    _transient = True
    _fields = {
        "date": fields.Date("Year End Date", required=True),
        "journal_id": fields.Many2One("account.journal", "Journal", required=True),
    }

    def _get_date(self, context):
        settings = get_model("settings").browse(1)
        y = datetime.date.today().year
        m = int(settings.year_end_month)
        d = int(settings.year_end_day)
        d_end = datetime.date(y, m, d)
        return d_end.strftime("%Y-%m-%d")

    _defaults = {
        "date": _get_date,
    }

    def create_entry(self, ids, context={}):
        obj = self.browse(ids[0])
        d_end = obj.date
        d_open = (datetime.datetime.strptime(d_end, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        d_from = (datetime.datetime.strptime(d_open, "%Y-%m-%d") - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        acc_ids = get_model("account.account").search(
            [["type", "in", ("revenue", "other_income", "cost_sales", "expense", "other_expense")]])
        settings = get_model("settings").browse(1)
        journal_id = obj.journal_id.id
        desc = "Year-end closing entry for %s" % d_end[:4]
        number = get_model("account.move")._get_number(context={"journal_id": journal_id, "date": d_end})
        if not number:
            raise Exception("Failed to generate journal number")
        move_vals = {
            "journal_id": journal_id,
            "number": number,
            "date": d_open,
            "narration": desc,
            "lines": [],
        }
        total = 0
        for acc in get_model("account.account").browse(acc_ids, context={"date_from": d_from, "date_to": d_end, "no_close": True}):
            if acc.balance == 0:
                continue
            amt = -acc.balance
            line_vals = {
                "description": desc,
                "account_id": acc.id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0
            }
            move_vals["lines"].append(("create", line_vals))
            total += amt
        if total:
            acc_id = settings.retained_earnings_account_id.id
            if not acc_id:
                raise Exception("Retained earnings account not found")
            amt = -total
            line_vals = {
                "description": desc,
                "account_id": acc_id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0
            }
            move_vals["lines"].append(("create", line_vals))
        res=get_model("account.move").search([["journal_id","=",move_vals["journal_id"]],["date","=",move_vals["date"]],["state","=","posted"]])
        if res:
            old_move_id=res[0]
            get_model("account.move").void([old_move_id])
        move_id = get_model("account.move").create(move_vals)
        get_model("account.move").post([move_id])
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": move_id,
            },
            "flash": "Year-end closing entry created successfully",
        }

YearEnd.register()
