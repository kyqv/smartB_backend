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
from dateutil.relativedelta import *
from netforce import access


class ReportCurrency(Model):
    _name = "report.currency"
    _transient = True
    _fields = {
        "date_from": fields.Date("From Date"),
        "date_to": fields.Date("To Date"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        if not date_from and not date_to:
            date_from = datetime.date.today().strftime("%Y-%m-01")
            date_to = (datetime.date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return {
            "date_from": date_from,
            "date_to": date_to,
        }

    def get_report_data(self, ids, context={}):
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        receivable_accounts = []
        payable_accounts = []
        bank_accounts = []
        deposit_accounts = []
        ctx = {
            #"date_from": date_from, # TODO: double-check that don't need date from
            "date_to": date_to,
            "currency_date": date_to,
        }
        for acc in get_model("account.account").search_browse([["type", "=", "receivable"]], context=ctx):
            bal_reval = get_model("currency").convert(
                acc.balance_cur, acc.currency_id.id, acc.company_currency_id.id, date=date_to, rate_type="sell")
            vals = {
                "code": acc.code,
                "name": acc.name,
                "balance_cur": acc.balance_cur,
                "account_currency_code": acc.currency_id.code,
                "company_currency_code": acc.company_currency_id.code,
                "balance": acc.balance,
                "balance_reval": bal_reval,
                "unreal_gain": get_model("currency").convert(bal_reval - acc.balance, acc.company_currency_id.id, settings.currency_id.id, date=date_to, rate_type="sell"),
            }
            receivable_accounts.append(vals)
        for acc in get_model("account.account").search_browse([["type", "=", "payable"]], context=ctx):
            bal_reval = get_model("currency").convert(
                acc.balance_cur, acc.currency_id.id, acc.company_currency_id.id, date=date_to, rate_type="buy")
            vals = {
                "code": acc.code,
                "name": acc.name,
                "balance_cur": acc.balance_cur,
                "account_currency_code": acc.currency_id.code,
                "company_currency_code": acc.company_currency_id.code,
                "balance": acc.balance,
                "balance_reval": bal_reval,
                "unreal_gain": get_model("currency").convert(bal_reval - acc.balance, acc.company_currency_id.id, settings.currency_id.id, date=date_to, rate_type="buy"),
            }
            payable_accounts.append(vals)
        for acc in get_model("account.account").search_browse([["type", "=", "bank"]], context=ctx):
            bal_reval = get_model("currency").convert(
                acc.balance_cur, acc.currency_id.id, acc.company_currency_id.id, date=date_to, rate_type="sell")
            vals = {
                "code": acc.code,
                "name": acc.name,
                "balance_cur": acc.balance_cur,
                "account_currency_code": acc.currency_id.code,
                "company_currency_code": acc.company_currency_id.code,
                "balance": acc.balance,
                "balance_reval": bal_reval,
                "unreal_gain": get_model("currency").convert(bal_reval - acc.balance, acc.company_currency_id.id, settings.currency_id.id, date=date_to, rate_type="sell"),
            }
            bank_accounts.append(vals)
        for acc in get_model("account.account").search_browse([["type", "=", "cur_liability"]], context=ctx):
            bal_reval = get_model("currency").convert(
                acc.balance_cur, acc.currency_id.id, acc.company_currency_id.id, date=date_to, rate_type="sell")
            vals = {
                "code": acc.code,
                "name": acc.name,
                "balance_cur": acc.balance_cur,
                "account_currency_code": acc.currency_id.code,
                "company_currency_code": acc.company_currency_id.code,
                "balance": acc.balance,
                "balance_reval": bal_reval,
                "unreal_gain": get_model("currency").convert(bal_reval - acc.balance, acc.company_currency_id.id, settings.currency_id.id, date=date_to, rate_type="sell"),
            }
            deposit_accounts.append(vals)
        data = {
            "date_from": date_from,
            "date_to": date_to,
            "company_name": comp.name,
            "company_currency": settings.currency_id.code,
            "receivable_accounts": receivable_accounts,
            "payable_accounts": payable_accounts,
            "bank_accounts": bank_accounts,
            "deposit_accounts": deposit_accounts,
            "totals_receivable": {
                "unreal_gain": sum(a["unreal_gain"] for a in receivable_accounts),
            },
            "totals_payable": {
                "unreal_gain": sum(a["unreal_gain"] for a in payable_accounts),
            },
            "totals_bank": {
                "unreal_gain": sum(a["unreal_gain"] for a in bank_accounts),
            },
            "totals_deposit": {
                "unreal_gain": sum(a["unreal_gain"] for a in deposit_accounts),
            },
            "total_exposure":
                sum(a["unreal_gain"] for a in receivable_accounts) +
                sum(a["unreal_gain"] for a in payable_accounts) +
                sum(a["unreal_gain"] for a in bank_accounts) +
                sum(a["unreal_gain"] for a in deposit_accounts),
        }
        return data

    def get_fx_exposure(self, date_from, date_to, track_id=None, track2_id=None, context={}):
        ctx = {
            "defaults": {
                "date_from": date_from,
                "date_to": date_to,
                "track_id": track_id,
                "track2_id": track2_id,
            }
        }
        data = self.get_report_data(None, ctx)
        return data["total_exposure"]

ReportCurrency.register()
