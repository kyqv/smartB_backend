#, required=Trui Copyright (c) 2012-2015 Netforce Co. Ltd.
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
from pprint import pprint
from netforce.access import get_active_company


class ReportTB(Model):
    _name = "report.tb"
    _transient = True
    _fields = {
        "date": fields.Date("Date", required=True),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
        "track2_id": fields.Many2One("account.track.categ", "Tracking-2"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "show_period_totals": fields.Boolean("Show Period Totals"),
    }

    _defaults = {
        "date": lambda *a: date.today().strftime("%Y-%m-%d"),
    }

    def get_year_date_from(self,dt):
        settings = get_model("settings").browse(1)
        d0=datetime.strptime(dt,"%Y-%m-%d").date()
        y = d0.year
        m = int(settings.year_end_month)
        d = int(settings.year_end_day)
        d_end = date(y, m, d)
        if d_end<d0:
            d_end+=relativedelta(years=1)
        d_from=d_end-relativedelta(years=1)+timedelta(days=1)
        return d_from.strftime("%Y-%m-%d")

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_to = params.get("date")
        if not date_to:
            date_to = date.today().strftime("%Y-%m-%d")
        #date_from = datetime.strptime(date_to, "%Y-%m-%d").strftime("%Y-%m-01")
        date_from = self.get_year_date_from(date_to)
        print("#################")
        print("date_from",date_from)
        track_id = params.get("track_id") or None
        if track_id:
            track_id = int(track_id)
        track2_id = params.get("track2_id") or None
        if track2_id:
            track2_id = int(track2_id)
        contact_id = params.get("contact_id") or None
        if contact_id:
            contact_id = int(contact_id)
        show_period_totals = params.get("show_period_totals")
        ctx = {
            "date_to": date_to,
            "active_test": False,
            "track_id": track_id,
            "track2_id": track2_id,
            "contact_id": contact_id,
        }
        res = get_model("account.account").search_read(
            [["type", "!=", "view"]], ["code", "name", "balance", "parent_id", "type"], context=ctx)
        accounts = {}
        parent_ids = []
        for r in res:
            accounts[r["id"]] = r

        ctx["date_from"] = date_from
        res = get_model("account.account").search_read([["type", "!=", "view"]], ["debit", "credit"], context=ctx)
        for r in res:
            accounts[r["id"]]["debit_month"] = r["debit"]
            accounts[r["id"]]["credit_month"] = r["credit"]

        begin_date_to = (datetime.strptime(date_from, "%Y-%m-%d") - relativedelta(day=1)).strftime("%Y-%m-%d")
        ctx["date_from"] = None
        ctx["date_to"] = begin_date_to
        ctx["excl_date_to"] = True
        res = get_model("account.account").search_read([["type", "!=", "view"]], ["balance"], context=ctx)
        for r in res:
            accounts[r["id"]]["balance_begin"] = r["balance"]

        accounts = {acc_id: acc for acc_id, acc in accounts.items() if acc["balance"] or acc["debit_month"] or acc["credit_month"] or acc["balance_begin"]}
        parent_ids = [acc["parent_id"][0] for acc in accounts.values() if acc["parent_id"]]
        while parent_ids:
            parent_ids = list(set(parent_ids))
            res = get_model("account.account").read(parent_ids, ["code", "name", "parent_id", "type"])
            parent_ids = []
            for r in res:
                accounts[r["id"]] = r
                if r["parent_id"]:
                    parent_ids.append(r["parent_id"][0])
        root_accounts = []
        for acc in accounts.values():
            if not acc["parent_id"]:
                root_accounts.append(acc)
                continue
            parent_id = acc["parent_id"][0]
            parent = accounts[parent_id]
            parent.setdefault("children", []).append(acc)

        root_acc = {
            "type": "view",
            "summary": "Total",
            "children": root_accounts,
            "separator": "double",
        }

        def _get_totals(acc):
            if acc["type"] != "view":
                amt = acc.get("balance", 0)
                acc["debit"] = amt > 0 and amt or 0
                acc["credit"] = amt < 0 and -amt or 0
                if show_period_totals:
                    acc["debit_month"] = acc.get("debit_month", 0)
                    acc["credit_month"] = acc.get("credit_month", 0)
                else:
                    amt = acc.get("debit_month", 0) - acc.get("credit_month", 0)
                    acc["debit_month"] = amt > 0 and amt or 0
                    acc["credit_month"] = amt < 0 and -amt or 0
                amt = acc.get("balance_begin", 0)
                acc["debit_begin"] = amt > 0 and amt or 0
                acc["credit_begin"] = amt < 0 and -amt or 0
                return
            children = acc.get("children", [])
            for child in children:
                _get_totals(child)
            acc["debit"] = sum(c["debit"] for c in children)
            acc["credit"] = sum(c["credit"] for c in children)
            acc["debit_month"] = sum(c["debit_month"] for c in children)
            acc["credit_month"] = sum(c["credit_month"] for c in children)
            acc["debit_begin"] = sum(c["debit_begin"] for c in children)
            acc["credit_begin"] = sum(c["credit_begin"] for c in children)

        _get_totals(root_acc)

        def _join_accounts(acc):
            if not acc.get("children"):
                return
            child_names = {}
            for c in acc["children"]:
                k = (c.get("code", ""), c["name"])
                if k in child_names:
                    c2 = child_names[k]
                    if c2.get("children") and c.get("children"):
                        c2["children"] += c["children"]
                    c2["debit"] += c["debit"]
                    c2["credit"] += c["credit"]
                    c2["debit_month"] += c["debit_month"]
                    c2["credit_month"] += c["credit_month"]
                    c2["debit_begin"] += c["debit_begin"]
                    c2["credit_begin"] += c["credit_begin"]
                    c2["balance"] += c["balance"]
                    c2["balance_begin"] += c["balance_begin"]
                else:
                    child_names[k] = c
            acc["children"] = []
            for k in sorted(child_names):
                c = child_names[k]
                acc["children"].append(c)
            for c in acc["children"]:
                _join_accounts(c)

        _join_accounts(root_acc)

        lines = []

        def _add_lines(acc, depth=0, max_depth=None):
            if max_depth is not None and depth > max_depth:
                return
            if acc["type"] != "view":
                amt1d = acc.get("debit_month", 0)
                amt1c = acc.get("credit_month", 0)
                if not show_period_totals:
                    amt1 = amt1d - amt1c
                    amt1d = amt1 > 0 and amt1 or None
                    amt1c = amt1 < 0 and -amt1 or None
                amt2 = acc.get("balance", 0)
                amt3 = acc.get("balance_begin", 0)
                lines.append({
                    "type": "account",
                    "string": acc["code"] + " - " + acc["name"],
                    "account_code": acc["code"],
                    "account_name": acc["name"],
                    "debit_month": amt1d,
                    "credit_month": amt1c,
                    "debit_year": amt2 > 0 and amt2 or None,
                    "credit_year": amt2 < 0 and -amt2 or None,
                    "debit_begin": amt3 > 0 and amt3 or None,
                    "credit_begin": amt3 < 0 and -amt3 or None,
                    "padding": 20 * depth,
                    "id": acc.get("id"),
                })
                return
            #print("xxx", acc)
            children = acc["children"]
            if acc.get("name"):
                lines.append({
                    "type": "group_header",
                    "string": acc["code"] + " - " + acc["name"],
                    "account_code": acc["code"],
                    "account_name": acc["name"],
                    "padding": 20 * depth,
                })
            for child in children:
                _add_lines(child, depth + 1, max_depth=max_depth)
            if acc.get("name"):
                summary = "Total " + acc["name"]
            else:
                summary = acc.get("summary")
            lines.append({
                "type": "group_footer",
                "string": summary,
                "account_code": acc.get("code"),
                "account_name": acc.get("name"),
                "padding": 20 * (depth + 1),
                "debit_begin": acc["debit_begin"] or None,
                "credit_begin": acc["credit_begin"] or None,
                "debit_month": acc["debit_month"] or None,
                "credit_month": acc["credit_month"] or None,
                "debit_year": acc["debit"] or None,
                "credit_year": acc["credit"] or None,
                "separator": acc.get("separator"),
            })
        root_acc["children"].sort(key=lambda a: a["code"])
        for acc in root_acc["children"]:
            _add_lines(acc)
        _add_lines(root_acc, max_depth=0)
        #pprint(lines)
        data = {
            "date_from": date_from,
            "date_to": date_to,
            "date": date_to,
            "track_id": track_id,
            "month_date_from": date_from,
            "begin_date_to": begin_date_to,
            "lines": lines,
            "company_name": comp.name,
        }
        return data

ReportTB.register()
