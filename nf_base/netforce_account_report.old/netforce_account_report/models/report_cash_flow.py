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


class ReportCashFlow(Model):
    _name = "report.cash.flow"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        elif not date_from and date_to:
            date_from = get_model("settings").get_fiscal_year_start(date=date_to)
        return {
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
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        accounts = {}
        ctx = {
            "date_to": date_from,
            "excl_date_to": True,
        }
        for acc in get_model("account.account").search_browse([["type", "!=", "view"]], context=ctx):
            accounts[acc.id] = {
                "id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "type": acc.type,
                "begin_balance": acc.balance,
            }
        ctx = {
            "date_from": date_from,
            "date_to": date_to,
        }
        for acc in get_model("account.account").search_browse([["type", "!=", "view"]], context=ctx):
            accounts[acc.id].update({
                "period_balance": acc.balance,
            })
        ctx = {
            "date_to": date_to,
        }
        for acc in get_model("account.account").search_browse([["type", "!=", "view"]], context=ctx):
            accounts[acc.id].update({
                "end_balance": acc.balance,
            })
        accounts = sorted(accounts.values(), key=lambda acc: acc["code"])
        net_income = 0
        pl_types = ["revenue", "cost_sales", "other_income", "expense", "other_expense"]
        invest_types = ["fixed_asset", "noncur_asset"]
        finance_types = ["equity"]
        cash_types = ["cash", "cheque", "bank"]
        for acc in accounts:
            if acc["type"] in pl_types:
                net_income -= acc["period_balance"]
        lines = []
        line = {
            "string": "Net Income",
            "amount": net_income,
        }
        lines.append(line)
        cash_flow = net_income
        line = {
            "string": "Operating activities",
        }
        lines.append(line)
        for acc in accounts:
            if acc["type"] not in pl_types and acc["type"] not in cash_types and acc["type"] not in invest_types and acc["type"] not in finance_types and abs(acc["period_balance"]) > 0.001:
                line = {
                    "string": "[%s] %s" % (acc["code"], acc["name"]),
                    "amount": -acc["period_balance"],
                }
                lines.append(line)
                cash_flow -= acc["period_balance"]
        line = {
            "string": "Investing activities",
        }
        lines.append(line)
        for acc in accounts:
            if acc["type"] not in pl_types and acc["type"] not in cash_types and acc["type"] in invest_types and abs(acc["period_balance"]) > 0.001:
                line = {
                    "string": "[%s] %s" % (acc["code"], acc["name"]),
                    "amount": -acc["period_balance"],
                }
                lines.append(line)
                cash_flow -= acc["period_balance"]
        line = {
            "string": "Financing activities",
        }
        lines.append(line)
        for acc in accounts:
            if acc["type"] not in pl_types and acc["type"] not in cash_types and acc["type"] in finance_types and abs(acc["period_balance"]) > 0.001:
                line = {
                    "string": "[%s] %s" % (acc["code"], acc["name"]),
                    "amount": -acc["period_balance"],
                }
                lines.append(line)
                cash_flow -= acc["period_balance"]
        cash_begin = 0
        cash_end = 0
        for acc in accounts:
            if acc["type"] in cash_types:
                cash_begin += acc["begin_balance"]
                cash_end += acc["end_balance"]
        line = {
            "string": "Net cash flow for period",
            "amount": cash_flow,
        }
        lines.append(line)
        line = {
            "string": "Cash at beginning of period",
            "amount": cash_begin,
        }
        lines.append(line)
        line = {
            "string": "Cash at end of period",
            "amount": cash_end,
        }
        lines.append(line)
        data = {
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
            "company_name": comp.name,
        }
        return data

ReportCashFlow.register()
