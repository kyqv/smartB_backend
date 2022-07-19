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
from netforce.database import get_connection

# XXX: deprecated, not used any more


class BankReconcile(Model):
    _name = "account.bank.reconcile"
    _string = "Bank Reconciliation"
    _name_field = "number"
    _fields = {
        "account_lines": fields.One2Many("account.move.line", "bank_reconcile_id", "Account Entries"),
        "statement_lines": fields.One2Many("account.statement.line", "bank_reconcile_id", "Statement Lines"),
        "total_account": fields.Decimal("Total Account", function="get_total", function_multi=True),
        "total_statement": fields.Decimal("Total Statement", function="get_total", function_multi=True),
        "number": fields.Char("Number", function="get_total", function_multi=True),
    }

    def get_total(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_account = 0
            total_statement = 0
            for line in obj.account_lines:
                total_account += line.debit - line.credit
            for line in obj.statement_lines:
                total_statement += line.received - line.spent
            number = "R%d" % obj.id
            if abs(total_account - total_statement) > 0:
                number += "*"
            vals[obj.id] = {
                "total_account": total_account,
                "total_statement": total_statement,
                "number": number,
            }
        return vals

    def delete(self, ids, **kw):
        st_line_ids = []
        move_line_ids = []
        for obj in self.browse(ids):
            for st_line in obj.statement_lines:
                st_line_ids.append(st_line.id)
            for move_line in obj.account_lines:
                move_line_ids.append(move_line.id)
        st_line_ids = list(set(st_line_ids))
        move_line_ids = list(set(move_line_ids))
        get_model("account.statement.line").write(st_line_ids, {"state": "not_reconciled"})
        get_model("account.move.line").write(move_line_ids, {"state": "not_reconciled"})
        super().delete(ids, **kw)

BankReconcile.register()
