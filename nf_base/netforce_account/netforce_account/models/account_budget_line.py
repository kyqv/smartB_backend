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


class BudgetLine(Model):
    _name = "account.budget.line"
    _string = "Budget Line"
    _fields = {
        "sequence": fields.Integer("Sequence"),
        "budget_id": fields.Many2One("account.budget", "Budget", required=True, on_delete="cascade"),
        "account_id": fields.Many2One("account.account", "Account", required=True),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
        "contact_id": fields.Many2One("contact", "Supplier"),
        "budget_amount": fields.Decimal("Budget Amount", required=True),
        "actual_amount": fields.Decimal("Actual Amount", function="get_actual", function_multi=True),
        "variance": fields.Decimal("Variance", function="get_actual", function_multi=True),
        "variance_percent": fields.Decimal("Variance %", function="get_actual", function_multi=True),
        "paid_amount": fields.Decimal("Paid Amount", function="get_paid", function_multi=True),
        "unpaid_amount": fields.Decimal("Unpaid Amount", function="get_paid", function_multi=True),
    }
    _order = "sequence"

    def get_actual(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            ctx = {
                "date_from": obj.budget_id.date_from,
                "date_to": obj.budget_id.date_to,
            }
            if obj.contact_id:
                ctx["contact_id"]=obj.contact_id.id
            elif obj.track_id:
                ctx["track_id"]=obj.track_id.id
            acc = get_model("account.account").browse(obj.account_id.id, ctx)  # XXX: speed
            actual = acc.balance
            variance = actual - (obj.budget_amount or 0)
            variance_percent = variance * 100 / obj.budget_amount if obj.budget_amount else None
            vals[obj.id] = {
                "actual_amount": actual,
                "variance": variance,
                "variance_percent": variance_percent,
            }
        return vals

    def get_paid(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = {
                "paid_amount": 0,
                "unpaid_amount": obj.actual_amount, # FIXME
            }
        return vals

BudgetLine.register()
