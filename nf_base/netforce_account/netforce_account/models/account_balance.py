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
import time
from netforce.database import get_connection

class Balance(Model):
    _name = "account.balance"
    _string="Account Balance"
    _fields = {
        "account_id": fields.Many2One("account.account", "Account", required=True, on_delete="cascade"),
        "track_id": fields.Many2One("account.track.categ","Track-1"),
        "debit": fields.Decimal("Debit",required=True),
        "credit": fields.Decimal("Credit",required=True),
        "amount_cur": fields.Decimal("Currency Amt"),
    }


    def update_balances(self,context={}): # XXX: make faster
        db=get_connection()
        res=db.query("SELECT account_id,track_id,SUM(debit) AS total_debit,SUM(credit) AS total_credit,SUM(amount_cur*SIGN(debit-credit)) AS total_amount_cur FROM account_move_line GROUP BY account_id,track_id")
        bals={}
        for r in res:
            bals[(r.account_id,r.track_id)]=(r.total_debit,r.total_credit,r.total_amount_cur)
        db.execute("DELETE FROM account_balance")
        for (acc_id,track_id),(debit,credit,amount_cur) in bals.items():
            db.execute("INSERT INTO account_balance (account_id,track_id,debit,credit,amount_cur) VALUES (%s,%s,%s,%s,%s)",acc_id,track_id,debit,credit,amount_cur)

Balance.register()
