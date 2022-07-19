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


class ClaimPayment(Model):
    _name = "claim.payment"
    _transient = True
    _fields = {
        "amount": fields.Decimal("Amount", required=True),
        "date": fields.Date("Date", required=True),
        "account_id": fields.Many2One("account.account", "Account", required=True, condition=[["type", "=", "bank"]], on_delete="cascade"),
        "ref": fields.Char("Ref"),
        "claim_id": fields.Many2One("account.claim", "Claim", required=True, on_delete="cascade"),
    }

    def add_payment(self, ids, context={}):
        obj = self.browse(ids[0])
        claim = obj.claim_id
        if obj.amount > claim.amount_due:
            raise Exception("Amound paid exceeds the amount due.")
        settings = get_model("settings").browse(1)
        claim_account_id = settings.unpaid_claim_id.id
        assert claim_account_id, "Missing unpaid expense claims account"
        vals = {
            "type": "out",
            "pay_type": "claim",
            "date": obj.date,
            "ref": obj.ref,
            "account_id": obj.account_id.id,
            "currency_id": settings.currency_id.id,
            "lines": [("create", {
                "type": "claim",
                "claim_id": claim.id,
                "account_id": claim.account_id.id,
                "amount": obj.amount,
            })],
        }
        pmt_id = get_model("account.payment").create(vals, context={"type": "out"})
        get_model("account.payment").post([pmt_id])
        return {
            "next": {
                "name": "claim_edit",
                "active_id": claim.id,
            },
            "flash": "Payment recorded",
        }

ClaimPayment.register()
