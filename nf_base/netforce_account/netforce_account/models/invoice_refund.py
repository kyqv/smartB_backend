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


class InvoiceRefund(Model):
    _name = "invoice.refund"
    _transient = True
    _fields = {
        "amount": fields.Decimal("Amount", required=True),
        "date": fields.Date("Date", required=True),
        "account_id": fields.Many2One("account.account", "Account", required=True, condition=[["type", "in", ["bank","cash","cheque"]]], on_delete="cascade"),
        "ref": fields.Char("Ref"),
        "invoice_id": fields.Many2One("account.invoice", "Invoice", required=True, on_delete="cascade"),
    }

    def _get_invoice(self, context={}):
        return context["parent_id"]

    _defaults = {
        "invoice_id": _get_invoice,
    }

    def add_refund(self, ids, context={}):
        obj = self.browse(ids[0])
        inv = obj.invoice_id
        assert inv.inv_type in ("credit", "prepay", "overpay")
        if obj.amount > inv.amount_credit_remain:
            raise Exception("Amount refunded exceeds the remaining credit")
        vals = {
            "type": inv.type,
            "pay_type": "invoice",
            "contact_id": inv.contact_id.id,
            "date": obj.date,
            "ref": obj.ref,
            "account_id": obj.account_id.id,
            "currency_id": inv.currency_id.id,
            "lines": [("create", {
                "type": "invoice",
                "invoice_id": inv.id,
                "account_id": inv.account_id.id,
                "amount": obj.amount,
            })],
        }
        pmt_id = get_model("account.payment").create(vals, context={"type": vals["type"]})
        get_model("account.payment").post([pmt_id])
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv.id,
            }
        }

InvoiceRefund.register()
