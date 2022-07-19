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


class Reconcile(Model):
    _name = "account.reconcile"
    _string = "Account Reconciliation"
    _name_field = "number"
    _fields = {
        "lines": fields.One2Many("account.move.line", "reconcile_id", "Account Entries", condition=[["move_id.state", "=", "posted"]]),
        "debit": fields.Decimal("Total Debit", function="get_total", function_multi=True),
        "credit": fields.Decimal("Total Credit", function="get_total", function_multi=True),
        "balance": fields.Decimal("Balance", function="get_total", function_multi=True),
        "number": fields.Char("Number", function="get_total", function_multi=True),
    }

    def get_total(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            debit = 0
            credit = 0
            for line in obj.lines:
                debit += line.debit
                credit += line.credit
            balance = debit - credit
            number = "R%d" % obj.id
            if balance != 0:
                number += "*"
            vals[obj.id] = {
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "number": number,
            }
        return vals

Reconcile.register()
