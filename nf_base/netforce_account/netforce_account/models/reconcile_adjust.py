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
import time


class ReconcileAdjust(Model):
    _name = "reconcile.adjust"
    _transient = True
    _fields = {
        "line_id": fields.Many2One("account.statement.line", "Statement Line", required=True, on_delete="cascade"),
        "amount": fields.Decimal("Adjustment Amount", required=True, readonly=True),
        "account_id": fields.Many2One("account.account", "Adjustment Account", required=True, on_delete="cascade"),
        "date": fields.Date("Adjustment Date", required=True),
        "warning": fields.Boolean("Warning", readonly=True),
    }

    def default_get(self, field_names=None, context={}, **kw):
        if not field_names:
            return {}
        line_id = context.get("line_id")
        if not line_id:
            return {}
        line_id = int(line_id)
        st_line_ids, acc_line_ids = get_model("account.statement.line").get_reconcile_lines([line_id])
        total_st = 0
        for st_line in get_model("account.statement.line").browse(st_line_ids):
            total_st += st_line.received - st_line.spent
        total_acc = 0
        for acc_line in get_model("account.move.line").browse(acc_line_ids):
            total_acc += acc_line.debit - acc_line.credit
        amt = total_st - total_acc
        vals = {
            "line_id": line_id,
            "amount": amt,
            "warning": abs(amt) > 1,
            "date": time.strftime("%Y-%m-%d"),
        }
        return vals

    def do_adjust(self, ids, context={}):
        obj = self.browse(ids)[0]
        st_line = obj.line_id
        account_id = st_line.statement_id.account_id.id
        amt = obj.amount
        vals = {
            "type": amt > 0 and "in" or "out",
            "pay_type": "adjust",
            "date": obj.date,
            "account_id": account_id,
            "lines": [("create", {
                "type": "adjust",
                "description": "Adjustment",
                "amount": abs(amt),
                "account_id": obj.account_id.id,
            })],
        }
        pmt_id = get_model("account.payment").create(vals, context={"type": vals["type"], "date": obj.date})
        get_model("account.payment").post([pmt_id])
        pmt = get_model("account.payment").browse(pmt_id)
        acc_line = pmt.move_id.lines[0]
        acc_line.write({"statement_lines": [("set", [st_line.id])]})
        st_line_ids, acc_line_ids = get_model("account.statement.line").get_reconcile_lines([st_line.id])
        total_st = 0
        for st_line in get_model("account.statement.line").browse(st_line_ids):
            total_st += st_line.received - st_line.spent
        total_acc = 0
        for acc_line in get_model("account.move.line").browse(acc_line_ids):
            total_acc += acc_line.debit - acc_line.credit
        if total_st != total_acc:
            raise Exception("Reconciliation error")
        get_model("account.statement.line").write(st_line_ids, {"state": "reconciled"})
        get_model("account.move.line").write(acc_line_ids, {"state": "reconciled"})

ReconcileAdjust.register()
