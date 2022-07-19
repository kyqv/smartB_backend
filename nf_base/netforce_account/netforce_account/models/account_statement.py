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
from netforce.access import get_active_company
from datetime import *
from dateutil.relativedelta import *
import time


class Statement(Model):
    _name = "account.statement"
    _string = "Statement"
    _name_field = "date_start"
    _multi_company = True
    _audit_log = True
    _fields = {
        "state": fields.Selection([["not_reconciled", "Not Reconciled"], ["reconciled", "Reconciled"]], "Status", function="get_state"),
        "date_imported": fields.Date("Imported Date", search=True),
        "date_start": fields.Date("Start Date",required=True),
        "date_end": fields.Date("End Date",required=True),
        "balance_start": fields.Decimal("Start Balance",required=True),
        "balance_end": fields.Decimal("End Balance", function="get_end_balance"),
        "account_id": fields.Many2One("account.account", "Account", required=True, search=True),
        "lines": fields.One2Many("account.statement.line", "statement_id", "Lines"),
        "company_id": fields.Many2One("company", "Company"),
    }
    _defaults = {
        "date_imported": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
    }
    _order = "date_start desc"

    def get_state(self, ids, context={}):
        vals = {}
        for st in self.browse(ids):
            rec = True
            for line in st.lines:
                if line.state != "reconciled":
                    rec = False
                    break
            vals[st.id] = rec and "reconciled" or "not_reconciled"
        return vals

    def get_end_balance(self, ids, context={}):
        vals = {}
        for st in self.browse(ids):
            bal = st.balance_start or 0
            for line in st.lines:
                bal += (line.received or 0) - (line.spent or 0)
            vals[st.id] = bal
        return vals

    def create(self, vals, **kw):
        new_id = super().create(vals, **kw)
        obj = self.browse(new_id)
        obj.account_id.auto_bank_reconcile()
        return new_id

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        account_ids = []
        for obj in self.browse(ids):
            account_ids.append(obj.account_id.id)
        account_ids = list(set(account_ids))
        get_model("account.account").auto_bank_reconcile(account_ids)

    def delete(self, ids, **kw):
        st_line_ids = []
        for obj in self.browse(ids):
            for st_line in obj.lines:
                st_line_ids.append(st_line.id)
        st_line_ids = list(set(st_line_ids))
        get_model("account.statement.line").unreconcile(st_line_ids)
        super().delete(ids, **kw)

    def onchange_account(self, context={}):
        data = context["data"]
        account_id = data["account_id"]
        acc = get_model("account.account").browse(account_id)
        if acc.statements:
            st = acc.statements[0]
            d = datetime.strptime(st.date_end, "%Y-%m-%d") + timedelta(days=1)
            data["date_start"] = d.strftime("%Y-%m-%d")
            data["date_end"] = (d + relativedelta(day=31)).strftime("%Y-%m-%d")
            data["balance_start"] = st.balance_end
        else:
            data["date_start"] = (datetime.today() - relativedelta(day=1)).strftime("%Y-%m-%d")
            data["date_end"] = (datetime.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return data

    def update_balance(self, context={}):
        data = context["data"]
        if not data.get("balance_start"):
            data["balance_start"]=0
        bal = data["balance_start"]
        for line in data["lines"]:
            if not line.get("received"):
                line["received"] = 0
            if not line.get("spent"):
                line["spent"] = 0
            bal += line["received"] - line["spent"]
            line["balance"] = bal
        data["balance_end"] = bal
        return data

Statement.register()
