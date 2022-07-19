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

from netforce.model import Model, fields


class ExpenseLine(Model):
    _name = "account.expense.line"
    _string = "Expense Line"
    _fields = {
        "expense_id": fields.Many2One("account.expense", "Expense", required=True, on_delete="cascade"),
        "description": fields.Char("Description", required=True),
        "qty": fields.Decimal("Qty", required=True),
        "unit_price": fields.Decimal("Unit Price", required=True),
        "amount": fields.Decimal("Amount", function="get_amount"),
        "account_id": fields.Many2One("account.account", "Account", condition=[["type", "!=", "view"]]),
        "tax_id": fields.Many2One("account.tax.rate", "Tax Rate"),
    }

    def get_amount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = obj.qty * obj.unit_price
        return vals

ExpenseLine.register()
