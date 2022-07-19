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
from netforce.access import get_active_company


class ReportJournal(Model):
    _name = "report.journal"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "journal_id": fields.Many2One("account.journal", "Journal"),
        "ref": fields.Char("Reference"),
        "filter_by": fields.Selection([["date", "Journal date"], ["date_posted", "Journal posted date"]], "Filter By"),
        "order_by": fields.Selection([["number", "Journal number"], ["date", "Journal date"], ["date_posted", "Journal posted date"]], "Order By"),
        "hide_zero": fields.Boolean("Hide zero lines"),
    }

    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-%d"),
        "date_to": lambda *a: date.today().strftime("%Y-%m-%d"),
        "filter_by": "date",
        "order_by": "number",
    }

    def get_report_data(self, ids=None, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        if not date_from:
            # date_from=date.today().strftime("%Y-%m-01")
            date_from = date.today().strftime("%Y-%m-%d")
        date_to = params.get("date_to")
        if not date_to:
            # date_to=(date.today()+relativedelta(day=31)).strftime("%Y-%m-%d")
            date_to = date.today().strftime("%Y-%m-%d")
        journal_id = params.get("journal_id")
        if journal_id:
            journal_id = int(journal_id)
            journal = get_model("account.journal").browse(journal_id)
        else:
            journal = None
        ref = params.get("ref")
        filter_by = params.get("filter_by")
        order_by = params.get("order_by")
        hide_zero = params.get("hide_zero")
        condition = [["state", "=", "posted"]]
        if filter_by == "date_posted":
            condition += [["date_posted", ">=", date_from], ["date_posted", "<=", date_to]]
        else:
            condition += [["date", ">=", date_from], ["date", "<=", date_to]]
        if journal_id:
            condition.append(["journal_id", "=", journal_id])
        if ref:
            condition.append(["narration", "ilike", "%" + ref + "%"])
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "moves": [],
        }
        if journal:
            data["journal_name"] = journal.name
        if order_by == "date":
            order = "date,id"
        elif order_by == "date_posted":
            order = "date_posted,id"
        else:
            order = "number,id"
        moves = get_model("account.move").search_browse(condition, order=order)
        for move in moves:
            move_vals = {
                "id": move.id,
                "number": move.number,
                "narration": move.narration,
                "ref": move.ref,
                "date": move.date,
                "date_posted": move.date_posted,
                "lines": [],
                "total_debit": 0,
                "total_credit": 0,
            }
            for line in move.lines:
                if hide_zero and not line["debit"] and not line["credit"]:
                    continue
                line_vals = {
                    "contact_name": line.contact_id.name,
                    "description": line.description,
                    "account_id": line.account_id.id,
                    "account_name": line.account_id.name,
                    "account_code": line.account_id.code,
                    "debit": line.debit,
                    "credit": line.credit,
                    "track_name": line.track_id.name,
                }
                move_vals["lines"].append(line_vals)
                move_vals["total_debit"] += line_vals["debit"]
                move_vals["total_credit"] += line_vals["credit"]
            move_vals["lines"].sort(key=lambda l: (l["debit"],l["credit"]),reverse=True)
            data["moves"].append(move_vals)
        return data

ReportJournal.register()
