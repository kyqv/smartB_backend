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


class ReportGL(Model):
    _name = "report.gl"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "select_type": fields.Selection([["all", "All"], ["range", "Account Range"], ["list", "Account List"]], "Select Accounts"),
        "account_from_id": fields.Many2One("account.account", "From Account"),
        "account_to_id": fields.Many2One("account.account", "To Account"),
        "accounts": fields.Text("Account List"),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
        "journal_id": fields.Many2One("account.journal", "Journal"),
    }

    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
        "select_type": "all",
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
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        track_id = params.get("track_id") or None
        journal_id = params.get("journal_id") or None
        if track_id:
            track_id = int(track_id)
        select_type = params.get("select_type")
        condition = [["type", "!=", "view"]]
        if select_type == "range":
            account_from_id = params.get("account_from_id")
            if account_from_id:
                account_from_id = int(account_from_id)
                account_from = get_model("account.account").browse(account_from_id)
                condition.append(["code", ">=", account_from.code])
            account_to_id = params.get("account_to_id")
            if account_to_id:
                account_to_id = int(account_to_id)
                account_to = get_model("account.account").browse(account_to_id)
                condition.append(["code", "<=", account_to.code])
        elif select_type == "list":
            codes = params.get("accounts") or ""
            acc_ids = []
            for code in codes.split(","):
                code = code.strip()
                if not code:
                    continue
                res = get_model("account.account").search([["code", "=", code]])
                if not res:
                    raise Exception("Account code not found: %s" % code)
                acc_id = res[0]
                acc_ids.append(acc_id)
            if acc_ids:
                condition.append(["id", "in", acc_ids])
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
        }
        ctx = {
            "date_from": date_from,
            "date_to": date_to,
            "active_test": False,
            "track_id": track_id,
            "journal_id": journal_id,
        }
        accounts = get_model("account.account").search_read(
            condition, ["name", "code", "debit", "credit", "balance"], order="code", context=ctx)
        accounts = [acc for acc in accounts if acc["debit"] or acc["credit"]]
        data["lines"] = accounts
        data["total_debit"] = sum(acc["debit"] for acc in accounts)
        data["total_credit"] = sum(acc["credit"] for acc in accounts)
        data["total_balance"] = sum(acc["balance"] for acc in accounts)
        pprint(data)
        return data

    def export_detail_xls(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "report_gl_detail_xls",
                "date_from": obj.date_from,
                "date_to": obj.date_to,
                "select_type": obj.select_type or "",
                "account_from_id": obj.account_from_id.id or "",
                "account_to_id": obj.account_to_id.id or "",
                "accounts": obj.accounts or "",
            }
        }

    def get_report_data_details(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        track_id = params.get("track_id") or None
        if track_id:
            track_id = int(track_id)
        select_type = params.get("select_type")
        condition = [["type", "!=", "view"]]
        if select_type == "range":
            account_from_id = params.get("account_from_id")
            if account_from_id:
                account_from_id = int(account_from_id)
                account_from = get_model("account.account").browse(account_from_id)
                condition.append(["code", ">=", account_from.code])
            account_to_id = params.get("account_to_id")
            if account_to_id:
                account_to_id = int(account_to_id)
                account_to = get_model("account.account").browse(account_to_id)
                condition.append(["code", "<=", account_to.code])
        elif select_type == "list":
            codes = params.get("accounts") or ""
            acc_ids = []
            for code in codes.split(","):
                code = code.strip()
                if not code:
                    continue
                res = get_model("account.account").search([["code", "=", code]])
                if not res:
                    raise Exception("Account code not found: %s" % code)
                acc_id = res[0]
                acc_ids.append(acc_id)
            if acc_ids:
                condition.append(["id", "in", acc_ids])

        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_from,
            "accounts": [],
        }

        ctx = {
            "date_to": datetime.strptime(date_from, '%Y-%m-%d').strftime('%Y-%m-%d'),
            "excl_date_to": True,
            "track_id": track_id,
        }
        accs = get_model("account.account").search_browse(condition, context=ctx)
        for acc in accs:
            debit_total = 0.00
            credit_total = 0.00
            bg_bal = acc.balance or 0.00
            acc_vals = {
                "code_name": (acc.code or '') + ' ' + (acc.name or ''),
                "bg_bal": acc.balance or 0.00,
                "lines": [],
                "debit_total": 0.00,
                "credit_total": 0.00,
            }
            cond = [["account_id", "=", acc.id], ["move_id.date", ">=", date_from],
                   ["move_id.date", "<=", date_to], ["move_id.state", "=", "posted"]]
            if track_id:
                cond.append(["track_id", "=", track_id])
            lines = get_model("account.move.line").search_browse(cond, order="move_date")
            for line in lines:
                bg_bal += (line.debit - line.credit)
                line_vals = {
                    "date": line.move_date,
                    "number": line.move_number,
                    "description": line.description,
                    "debit": line.debit,
                    "credit": line.credit,
                    "balance": bg_bal,
                    "contact": line.contact_id.name,
                }
                debit_total += line.debit or 0.00
                credit_total += line.credit or 0.00
                acc_vals["lines"].append(line_vals)
            acc_vals["debit_total"] = debit_total
            acc_vals["credit_total"] = credit_total
            if acc_vals["lines"]:
                data["accounts"].append(acc_vals)
        return data

ReportGL.register()
