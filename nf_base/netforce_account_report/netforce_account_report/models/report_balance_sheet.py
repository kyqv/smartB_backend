# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

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


class ReportBalanceSheet(Model):
    _name = "report.balance.sheet"
    _transient = True
    _fields = {
        "date": fields.Date("Balance Date"),
        "compare_with": fields.Selection([["month", "Previous Month"], ["year", "Previous Year"]], "Compare With"),
        "compare_periods": fields.Selection([["1", "Previous 1 Period"], ["2", "Previous 2 Periods"], ["3", "Previous 3 Periods"], ["4", "Previous 4 Periods"], ["5", "Previous 5 Periods"], ["6", "Previous 6 Periods"], ["7", "Previous 7 Periods"], ["8", "Previous 8 Periods"], ["9", "Previous 9 Periods"], ["10", "Previous 10 Periods"], ["11", "Previous 11 Periods"]], "Compare Periods"),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
        "track2_id": fields.Many2One("account.track.categ", "Tracking"),
        "convert_currency": fields.Boolean("Convert Currency"),
    }

    _defaults = {
        "date": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_report_data(self, ids=None, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_to = params.get("date")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
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
        convert_currency = params.get("convert_currency")
        bs_types = ["bank", "cash", "cheque", "receivable", "cur_asset", "noncur_asset", "sup_deposit",
                    "fixed_asset", "payable", "cust_deposit", "cur_liability", "noncur_liability", "equity"]
        ctx = {
            "date_to": date_to,
            "track_id": track_id,
            "track2_id": track2_id,
            "active_test": False,
        }
        if convert_currency:
            ctx["currency_id"]=settings.currency_id.id
        res = get_model("account.account").search_read(
            ["type", "in", bs_types], ["code", "name", "balance", "balance_cur", "parent_id", "type"], order="code", context=ctx)
        accounts = {}
        parent_ids = []
        for r in res:
            r["balance"] = r["balance_cur"] if convert_currency else r["balance"]
            accounts[r["id"]] = r
            if r["parent_id"]:
                parent_ids.append(r["parent_id"][0])
        compare = {}
        for i in range(1, compare_periods + 1):
            date_to_c = deduct_period(date_to, i, compare_with)
            compare[i] = {
                "date_to": date_to_c,
            }
            ctx["date_to"] = date_to_c
            res = get_model("account.account").search_read(["type", "in", bs_types], ["balance", "balance_cur"], context=ctx)
            for r in res:
                accounts[r["id"]]["balance%d" % i] = r["balance_cur"] if convert_currency else r["balance"]
        i = 0
        while parent_ids:
            i += 1
            if i > 100:
                raise Exception("Cycle detected!")
            parent_ids = list(set(parent_ids))
            res = get_model("account.account").read(parent_ids, ["name", "parent_id", "type", "code"])
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
        assets = {
            "name": "Assets",
            "types": ["bank", "cash", "cheque", "receivable", "cur_asset", "noncur_asset", "fixed_asset", "sup_deposit"],
        }
        liabilities = {
            "name": "Liabilities",
            "types": ["payable", "cust_deposit", "cur_liability", "noncur_liability"],
        }
        net_assets = {
            "summary": "Net Assets",
            "children": [assets, liabilities],
            "separator": "single",
        }
        equity = {
            "name": "Equity",
            "types": ["equity"],
        }

        def _make_groups(accs, types):
            groups = []
            for acc in accs:
                if acc["type"] == "view":
                    children = _make_groups(acc["children"], types)
                    if children:
                        group = {
                            "code": acc["code"],
                            "name": acc["name"],
                            "children": children,
                            "id": acc["id"],
                        }
                        groups.append(group)
                elif acc["type"] in types:
                    if acc.get("balance") or any(acc.get("balance%d" % i) for i in range(1, compare_periods + 1)):
                        group = {
                            "code": acc["code"],
                            "name": acc["name"],
                            "balance": acc["balance"],
                            "id": acc["id"],
                        }
                        for i in range(1, compare_periods + 1):
                            group["balance%d" % i] = acc["balance%d" % i]
                        groups.append(group)
            return groups
        for group in [assets, liabilities, equity]:
            types = group["types"]
            group["children"] = _make_groups(root_accounts, types)
        net_profit = {
            "name": "Current Year Earnings",
            "balance": -get_model("report.profit.loss").get_net_profit(date_to, track_id=track_id, track2_id=track2_id, convert_currency=convert_currency, context=context),
        }
        for i in range(1, compare_periods + 1):
            date_to_c = compare[i]["date_to"]
            net_profit["balance%d" % i] = - \
                get_model("report.profit.loss").get_net_profit(
                    date_to_c, track_id=track_id, track2_id=track2_id, convert_currency=convert_currency, context=context)
        equity["children"].append(net_profit)

        def _set_totals(acc):
            children = acc.get("children")
            if not children:
                return
            total = 0
            comp_totals = {i: 0 for i in range(1, compare_periods + 1)}
            for child in children:
                _set_totals(child)
                total += child.get("balance", 0)
                for i in range(1, compare_periods + 1):
                    comp_totals[i] += child.get("balance%d" % i, 0)
            acc["balance"] = total
            for i in range(1, compare_periods + 1):
                acc["balance%d" % i] = comp_totals[i]
        _set_totals(net_assets)
        _set_totals(equity)

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
        _remove_dup_parents(assets)
        _remove_dup_parents(liabilities)
        _remove_dup_parents(equity)

        def _join_groups(group):
            if not group.get("children"):
                return
            child_names = {}
            for c in group["children"]:
                k = (c.get("code", ""), c["name"])
                if k in child_names:
                    c2 = child_names[k]
                    if c2.get("children") and c.get("children"):
                        c2["children"] += c["children"]
                    c2["balance"] += c["balance"]
                    for i in range(1, compare_periods + 1):
                        c2["balance%d" % i] += c["balance%d" % i]
                else:
                    child_names[k] = c
            group["children"] = []
            for k in sorted(child_names):
                c = child_names[k]
                group["children"].append(c)
            for c in group["children"]:
                _join_groups(c)
        _join_groups(assets)
        _join_groups(liabilities)
        _join_groups(equity)
        lines = []

        def _add_lines(group, depth=0, max_depth=None, sign=1):
            if max_depth is not None and depth > max_depth:
                return
            children = group.get("children")
            if children is None:
                line_vals = {
                    "type": "account",
                    "string": group.get("code") and "[%s] %s" % (group["code"], group["name"]) or group["name"],
                    "amount": group["balance"] * sign,
                    "padding": 20 * depth,
                    "id": group.get("id"),
                }
                for i in range(1, compare_periods + 1):
                    line_vals["amount%d" % i] = group.get("balance%d" % i, 0) * sign
                lines.append(line_vals)
                return
            name = group.get("name")
            if name:
                lines.append({
                    "type": "group_header",
                    "string": name,
                    "padding": 20 * depth,
                })
            for child in children:
                _add_lines(child, depth + 1, max_depth=max_depth, sign=sign)
            summary = group.get("summary")
            if not summary:
                summary = "Total " + name
            line_vals = ({
                "type": "group_footer",
                "string": summary,
                "padding": 20 * (depth + 1),
                "amount": group.get("balance", 0) * sign,
                "separator": group.get("separator"),
            })
            for i in range(1, compare_periods + 1):
                line_vals["amount%d" % i] = group.get("balance%d" % i, 0) * sign
            lines.append(line_vals)
        _add_lines(assets)
        _add_lines(liabilities, sign=-1)
        _add_lines(net_assets, depth=-1, max_depth=-1)
        _add_lines(equity, sign=-1)
        pprint(lines)
        data = {
            "date": date_to,
            "date_to": date_to, # XXX: jxls
            "track_id": track_id,
            "track2_id": track2_id,
            "col0": date_to,
            "lines": lines,
            "company_name": comp.name,
        }
        for i, comp in compare.items():
            data["date%d" % i] = comp["date_to"]
            data["col%d" % i] = comp["date_to"]
        return data

    def get_report_data_custom(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_to = params.get("date")
        d0 = datetime.strptime(date_to, "%Y-%m-%d")
        prev_month_date_to = (d0 - relativedelta(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        prev_year_date_to = (d0 - relativedelta(years=1)).strftime("%Y-%m-%d")
        data = {
            "date_to": date_to,
            "prev_month_date_to": prev_month_date_to,
            "prev_year_date_to": prev_year_date_to,
            "company_name": comp.name,
        }
        print("data", data)
        return data

ReportBalanceSheet.register()
