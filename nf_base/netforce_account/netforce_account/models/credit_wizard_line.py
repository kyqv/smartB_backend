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


class CreditWizardLine(Model):
    _name = "account.credit.wizard.line"
    _transient = True
    _fields = {
        "wiz_id": fields.Many2One("account.credit.wizard", "Wizard", required=True, on_delete="cascade"),
        "move_line_id": fields.Many2One("account.move.line", "Account Entry", required=True, readonly=True, on_delete="cascade"),
        "move_id": fields.Many2One("account.move", "Journal Entry", required=True, readonly=True, on_delete="cascade"),
        "date": fields.Date("Date", readonly=True),
        "account_id": fields.Many2One("account.account", "Account", required=True, readonly=True, on_delete="cascade"),
        "amount_credit_remain": fields.Decimal("Outstanding Credit", readonly=True),
        "amount": fields.Decimal("Amount"),
    }

CreditWizardLine.register()
