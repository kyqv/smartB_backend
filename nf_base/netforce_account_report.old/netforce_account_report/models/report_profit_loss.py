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
from pprint import pprint
from netforce.access import get_active_company


def deduct_period(date, num, period):
    d = datetime.strptime(date, "%Y-%m-%d")
    if period == "month":
        if (d + timedelta(days=1)).month != d.month:
            d -= relativedelta(months=num, day=31)
        else:
            d -= relativedelta(months=num)
    elif period == "year":
        d -= relativedelta(years=num)
    else:
        raise Exception("Invalid period")
    return d.strftime("%Y-%m-%d")


class ReportProfitLoss(Model):
    _name = "report.profit.loss"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "compare_with": fields.Selection([["month", "Previous Month"], ["year", "Previous Year"]], "Compare With"),
        "compare_periods": fields.Selection([["1", "Previous 1 Period"], ["2", "Previous 2 Periods"], ["3", "Previous 3 Periods"], ["4", "Previous 4 Periods"], ["5", "Previous 5 Periods"], ["6", "Previous 6 Periods"], ["7", "Previous 7 Periods"], ["8", "Previous 8 Periods"], ["9", "Previous 9 Periods"], ["10", "Previous 10 Periods"], ["11", "Previous 11 Periods"]], "Compare Periods"),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
        "track2_id": fields.Many2One("account.track.categ", "Tracking-2"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "currency_id": fields.Many2One("currency", "Currency"),
        "show_ytd": fields.Boolean("Show YTD"),
        "convert_currency": fields.Boolean("Convert Currency"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        track_id = defaults.get("track_id")
        track2_id = defaults.get("track2_id")
        contact_id = defaults.get("contact_id")
        convert_currency = defaults.get("convert_currency")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        elif not date_from and date_to:
            date_from = get_model("settings").get_fiscal_year_start(date=date_to)
        return {
            "date_from": date_from,
            "date_to": date_to,
            "track_id": track_id,
            "track2_id": track2_id,
            "show_ytd": True,
            "convert_currency": convert_currency,
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
        date_to = params.get("date_to")
        compare_with = params.get("compare_with")
        compare_periods = params.get("compare_periods")
        if compare_periods:
            compare_periods = int(compare_periods)
        else:
            compare_periods = 0
        if not compare_with:
            compare_periods = 0
        track_id = params.get("track_id")
        if track_id:
            track_id = int(track_id)
        track2_id = params.get("track2_id")
        if track2_id:
            track2_id = int(track2_id)
        contact_id = params.get("contact_id")
        if contact_id:
            contact_id = int(contact_id)
        currency_id = params.get("currency_id")
        if currency_id:
            currency_id = int(currency_id)
        else:
            currency_id = settings.currency_id.id
        show_ytd = params.get("show_ytd")
        convert_currency = params.get("convert_currency")

        pl_types = ["revenue", "cost_sales", "other_income", "expense", "other_expense"]
        ctx = {
            "date_from": date_from,
            "date_to": date_to,
            "track_id": track_id,
            "track2_id": track2_id,
            "contact_id": contact_id,
            "active_test": False,
            "currency_id": currency_id,
            "no_close": True,
        }
        res = get_model("account.account").search_read(
            ["type", "in", pl_types], ["code", "name", "balance", "parent_id", "type"], order="code", context=ctx)
        accounts = {}
        parent_ids = []
        for r in res:
            accounts[r["id"]] = r
            if r["parent_id"]:
                parent_ids.append(r["parent_id"][0])

        compare = {}
        for i in range(1, compare_periods + 1):
            date_from_c = deduct_period(date_from, i, compare_with)
            date_to_c = deduct_period(date_to, i, compare_with)
            compare[i] = {
                "date_from": date_from_c,
                "date_to": date_to_c,
            }
            ctx["date_from"] = date_from_c
            ctx["date_to"] = date_to_c
            res = get_model("account.account").search_read(["type", "in", pl_types], ["balance"], context=ctx)
            for r in res:
                accounts[r["id"]]["balance%d" % i] = r["balance"]

        date_from_ytd = get_model("settings").get_fiscal_year_start(date_to)
        if show_ytd:
            ctx["date_from"] = date_from_ytd
            ctx["date_to"] = date_to
            res = get_model("account.account").search_read(["type", "in", pl_types], ["balance"], context=ctx)
            for r in res:
                accounts[r["id"]]["balance_ytd"] = r["balance"]

        i = 0
        while parent_ids:
            i += 1
            if i > 100:
                raise Exception("Cycle detected!")
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
        income = {
            "name": "Income",
            "types": ["revenue"],
        }
        cost_sales = {
            "name": "Cost of Sales",
            "types": ["cost_sales"],
        }
        gross_profit = {
            "summary": "Gross Profit",
            "children": [income, cost_sales],
            "separator": "single",
        }
        other_income = {
            "name": "Other Income",
            "types": ["other_income"],
        }
        expenses = {
            "name": "Expenses",
            "types": ["expense", "other_expense"],
        }
        net_profit = {
            "summary": "Net Income",
            "children": [gross_profit, other_income, expenses],
            "separator": "double",
        }

        def _make_groups(accs, types):
            groups = []
            for acc in accs:
                if acc["type"] == "view":
                    children = _make_groups(acc["children"], types)
                    if children:
                        group = {
                            "code": acc.get("code", ""),
                            "name": acc["name"],
                            "children": children,
                            "id": acc["id"],
                        }
                        groups.append(group)
                elif acc["type"] in types:
                    if acc.get("balance") or any(acc.get("balance%d" % i) for i in range(1, compare_periods + 1)) or acc.get("balance_ytd"):
                        group = {
                            "code": acc.get("code", ""),
                            "name": acc["name"],
                            "balance": acc["balance"],
                            "id": acc["id"],
                        }
                        for i in range(1, compare_periods + 1):
                            group["balance%d" % i] = acc["balance%d" % i]
                        if show_ytd:
                            group["balance_ytd"] = acc["balance_ytd"]
                        groups.append(group)
            return groups
        for group in [income, cost_sales, other_income, expenses]:
            types = group["types"]
            group["children"] = _make_groups(root_accounts, types)
        if convert_currency:
            unreal_gain = {
                "code": "",
                "name": "Unrealized Currency Gain/Loss",
                "balance": -get_model("report.currency").get_fx_exposure(date_from, date_to, track_id=track_id, track2_id=track2_id, context=context),
            }
            for i in range(1, compare_periods + 1):
                date_from_c = compare[i]["date_from"]
                date_to_c = compare[i]["date_to"]
                unreal_gain["balance%d" % i] = -get_model("report.currency").get_fx_exposure(
                    date_from_c, date_to_c, track_id=track_id, track2_id=track2_id, context=context)
            if show_ytd:
                unreal_gain["balance_ytd"] = -get_model("report.currency").get_fx_exposure(
                    date_from_ytd, date_to, track_id=track_id, track2_id=track2_id, context=context)
            other_income["children"].append(unreal_gain)

        def _set_totals(acc):
            children = acc.get("children")
            if not children:
                return
            total = 0
            comp_totals = {i: 0 for i in range(1, compare_periods + 1)}
            ytd_total = 0
            for child in children:
                _set_totals(child)
                total += child.get("balance", 0)
                for i in range(1, compare_periods + 1):
                    comp_totals[i] += child.get("balance%d" % i, 0)
                ytd_total += child.get("balance_ytd", 0)
            acc["balance"] = total
            for i in range(1, compare_periods + 1):
                acc["balance%d" % i] = comp_totals[i]
            acc["balance_ytd"] = ytd_total
        _set_totals(net_profit)

        def _remove_dup_parents(group):
            if not group.get("children"):
                return
            children = []
            for c in group["children"]:
                _remove_dup_parents(c)
                if c["name"] == group["name"]:
                    if c.get("children"):
                        children += c["children"]
                else:
                    children.append(c)
            group["children"] = children
        _remove_dup_parents(income)
        _remove_dup_parents(cost_sales)
        _remove_dup_parents(other_income)
        _remove_dup_parents(expenses)

        def _join_groups(group):
            if not group.get("children"):
                return
            child_names = {}
            for c in group["children"]:
                k = (c.get("code"), c["name"])
                if k in child_names:
                    c2 = child_names[k]
                    if c2.get("children") and c.get("children"):
                        c2["children"] += c["children"]
                    c2["balance"] += c["balance"]
                    for i in range(1, compare_periods + 1):
                        c2["balance%d" % i] += c["balance%d" % i]
                    c2["balance_ytd"] += c["balance_ytd"]
                else:
                    child_names[k] = c
            group["children"] = []
            for k in sorted(child_names):
                c = child_names[k]
                group["children"].append(c)
            for c in group["children"]:
                _join_groups(c)
        _join_groups(income)
        _join_groups(cost_sales)
        _join_groups(other_income)
        _join_groups(expenses)
        lines = []

        def _add_lines(group, depth=0, max_depth=None, sign=1):
            if max_depth is not None and depth > max_depth:
                return
            children = group.get("children")
            if children is None:
                line_vals = {
                    "type": "account",
                    "string": "[%s] %s" % (group["code"], group["name"]) if group.get("code") else group["name"],
                    "amount": group.get("balance", 0) * sign,
                    "padding": 20 * depth,
                    "id": group.get("id"),
                }
                for i in range(1, compare_periods + 1):
                    line_vals["amount%d" % i] = group.get("balance%d" % i, 0) * sign
                if show_ytd:
                    line_vals["amount_ytd"] = group.get("balance_ytd", 0) * sign
                lines.append(line_vals)
                return
            name = group.get("name")
            if name:
                lines.append({
                    "type": "group_header",
                    "string": "[%s] %s" % (group["code"], group["name"]) if group.get("code") else group["name"],
                    "padding": 20 * depth,
                })
            for child in children:
                _add_lines(child, depth + 1, max_depth=max_depth, sign=sign)
            summary = group.get("summary")
            if not summary:
                summary = "Total " + name
            line_vals = {
                "type": "group_footer",
                "string": summary,
                "padding": 20 * (depth + 1),
                "amount": group.get("balance", 0) * sign,
                "separator": group.get("separator"),
            }
            for i in range(1, compare_periods + 1):
                line_vals["amount%d" % i] = group.get("balance%d" % i, 0) * sign
            if show_ytd:
                line_vals["amount_ytd"] = group.get("balance_ytd", 0) * sign
            lines.append(line_vals)
        _add_lines(income, sign=-1)
        _add_lines(cost_sales)
        _add_lines(gross_profit, depth=-1, max_depth=-1, sign=-1)
        _add_lines(other_income, sign=-1)
        _add_lines(expenses)
        _add_lines(net_profit, depth=-1, max_depth=-1, sign=-1)
        #pprint(lines)
        data = {
            "date_from": date_from,
            "date_to": date_to,
            "date_from_ytd": date_from_ytd,
            "track_id": track_id,
            "track2_id": track2_id,
            "contact_id": contact_id,
            "col0": date_to,
            "lines": lines,
            "company_name": comp.name,
            "show_ytd": show_ytd,
        }
        for i, comp in compare.items():
            data["date_from%d" % i] = comp["date_from"]
            data["date_to%d" % i] = comp["date_to"]
            data["col%d" % i] = comp["date_to"]

        return data

    def get_net_profit(self, date_to, track_id=None, track2_id=None, convert_currency=False, context={}):
        ctx = {
            "defaults": {
                "date_from": get_model("settings").get_fiscal_year_start(date_to),
                "date_to": date_to,
                "track_id": track_id,
                "track2_id": track2_id,
                "convert_currency": convert_currency,
                "company_name": context.get("company_name", ''),
            }
        }
        data = self.get_report_data(None, ctx)
        return data["lines"][-1]["amount"]

    def get_report_data_custom(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        d0 = datetime.strptime(date_from, "%Y-%m-%d")
        year_date_from = d0.strftime("%Y-01-01")  # XXX: get company fiscal year
        prev_date_from = (d0 - timedelta(days=1) - relativedelta(day=1)).strftime("%Y-%m-%d")
        prev_date_to = (d0 - timedelta(days=1) + relativedelta(day=31)).strftime("%Y-%m-%d")

        year_date_from_prev_year = (
            datetime.strptime(year_date_from, "%Y-%m-%d") - relativedelta(years=1)).strftime("%Y-%m-%d")
        date_from_prev_year = (datetime.strptime(date_from, "%Y-%m-%d") - relativedelta(years=1)).strftime("%Y-%m-%d")
        date_to_prev_year = (datetime.strptime(date_to, "%Y-%m-%d") - relativedelta(years=1)).strftime("%Y-%m-%d")

        data = {
            "date_from": date_from,
            "date_to": date_to,
            "year_date_from": year_date_from,
            "prev_date_from": prev_date_from,
            "prev_date_to": prev_date_to,
            "company_name": comp.name,
            "year_date_from_prev_year": year_date_from_prev_year,
            "date_from_prev_year": date_from_prev_year,
            "date_to_prev_year": date_to_prev_year,
        }
        print("data", data)
        return data

ReportProfitLoss.register()
